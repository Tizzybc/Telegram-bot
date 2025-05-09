import os
import logging
import tempfile
from telegram import Update, InputMediaPhoto, InputMediaVideo
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp

# ===== CONFIGURATION =====
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Required
BOT_USERNAME = os.getenv("BOT_USERNAME")  # e.g., "@yourbot"
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g., "@yourchannel"
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]  # Comma-separated

# Media settings
STICKER_PATH = "sticker.png"
WATERMARK_TEXT = "@YourBrand"
FONT_PATH = "arial.ttf"
STICKER_SIZE = 0.15
TEXT_POSITION = "bottom-center"
TEXT_COLOR = (255, 255, 255)
TEXT_OUTLINE = (0, 0, 0)
TEXT_SIZE_RATIO = 0.05

# ===== LOGGING =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== MEDIA PROCESSING =====
async def process_image(input_path: str, output_path: str) -> bool:
    """Add watermark to image"""
    try:
        img = Image.open(input_path).convert("RGBA")
        draw = ImageDraw.Draw(img)
        
        # Load font
        try:
            font = ImageFont.truetype(FONT_PATH, int(img.width * TEXT_SIZE_RATIO))
        except:
            font = ImageFont.load_default()
        
        # Add text watermark
        text = WATERMARK_TEXT
        text_width = draw.textlength(text, font=font)
        
        if TEXT_POSITION == "bottom-center":
            position = (
                (img.width - text_width) // 2,
                img.height - int(img.height * 0.05)
            )
        
        # Text outline
        for x in [-1, 0, 1]:
            for y in [-1, 0, 1]:
                draw.text(
                    (position[0] + x, position[1] + y),
                    text,
                    font=font,
                    fill=TEXT_OUTLINE
                )
        
        # Main text
        draw.text(position, text, font=font, fill=TEXT_COLOR)
        
        # Add sticker
        if os.path.exists(STICKER_PATH):
            sticker = Image.open(STICKER_PATH).convert("RGBA")
            sticker_width = int(img.width * STICKER_SIZE)
            sticker = sticker.resize(
                (sticker_width, int(sticker_width * sticker.height / sticker.width)),
                Image.Resampling.LANCZOS
            )
            img.paste(
                sticker,
                (img.width - sticker.width - 10, img.height - sticker.height - 10),
                sticker
            )
        
        img.save(output_path, "PNG")
        return True
        
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return False

async def process_video(input_path: str, output_path: str) -> bool:
    """Add watermark to video"""
    try:
        video = mp.VideoFileClip(input_path)
        
        # Text watermark
        txt_clip = (mp.TextClip(
            WATERMARK_TEXT,
            fontsize=video.w * TEXT_SIZE_RATIO,
            color='white',
            stroke_color='black',
            stroke_width=2
        )
        .set_position(("center", "bottom"))
        .set_duration(video.duration))
        
        final = mp.CompositeVideoClip([video, txt_clip])
        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            threads=4,
            preset='ultrafast'
        )
        return True
        
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        return False
    finally:
        if 'video' in locals(): video.close()
        if 'final' in locals(): final.close()

# ===== TELEGRAM HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "🖼️ Media Processor Bot\n\n"
        "Send me photos/videos to add watermarks!\n"
        "I can auto-process channel posts when added as admin."
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming media"""
    message = update.message or update.channel_post
    if not message:
        return
    
    # Get media file
    if message.photo:
        file = await message.photo[-1].get_file()
        media_type = "photo"
    elif message.video:
        file = await message.video.get_file()
        media_type = "video"
    else:
        if update.message:  # Only reply to private chats
            await update.message.reply_text("Please send a photo or video.")
        return
    
    # Process media
    input_path = tempfile.mktemp()
    output_path = tempfile.mktemp(suffix=".png" if media_type == "photo" else ".mp4")
    
    try:
        await file.download_to_drive(input_path)
        
        success = await (
            process_image(input_path, output_path)
            if media_type == "photo"
            else process_video(input_path, output_path)
        )
        
        if not success:
            raise Exception("Processing failed")
        
        with open(output_path, "rb") as f:
            if update.channel_post:  # Edit channel post
                await context.bot.edit_message_media(
                    chat_id=message.chat_id,
                    message_id=message.message_id,
                    media=(
                        InputMediaPhoto(f)
                        if media_type == "photo"
                        else InputMediaVideo(f)
                    )
                )
            else:  # Send to private chat
                await context.bot.send_media(
                    chat_id=message.chat_id,
                    media=(
                        InputMediaPhoto(f, caption="Processed!")
                        if media_type == "photo"
                        else InputMediaVideo(f, caption="Processed!")
                    )
                )
                
    except Exception as e:
        logger.error(f"Failed to handle media: {e}")
        if update.message:
            await update.message.reply_text(f"❌ Error: {str(e)}")
    finally:
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                try: os.remove(path)
                except: pass

# ===== MAIN =====
def main():
    """Start the bot"""
    app = Application.builder().token(TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ChatType.CHANNEL,
        handle_media
    ))
    
    # Webhook configuration
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),
        url_path=TOKEN,
        webhook_url=f"{os.getenv('WEBHOOK_URL')}/{TOKEN}",
        secret_token=os.getenv("SECRET_TOKEN", "default_secret_123")
    )

if __name__ == "__main__":
    main()

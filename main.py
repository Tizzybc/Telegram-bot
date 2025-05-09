import os
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
import tempfile
import textwrap
import requests
from io import BytesIO

# Configuration
TOKEN = os.getenv("TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Your channel ID (e.g., @yourchannel)
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]  # Comma-separated user IDs

# Media Processing Settings
STICKER_PATH = "sticker.png"
WATERMARK_TEXT = "@YourChannel"
FONT_PATH = "arial.ttf"  # Provide a font file or use default
STICKER_SIZE = 0.15
TEXT_POSITION = "bottom-center"
TEXT_COLOR = (255, 255, 255)
TEXT_OUTLINE = (0, 0, 0)
TEXT_SIZE_RATIO = 0.05

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! I'm your media processing bot.\n\n"
        "Send me photos/videos to add watermark/sticker.\n"
        "I can also automatically process channel posts when added as admin."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    Available commands:
    /start - Start the bot
    /help - Show this help
    /settings - Configure bot settings
    /process - Manually process media
    
    Admin commands:
    /add_channel - Add a channel for auto-processing
    /stats - Get bot statistics
    """
    await update.message.reply_text(help_text)

async def process_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process media from private chat"""
    if update.message.chat.type != "private":
        return
    
    await handle_media(update, context, source="chat")

async def channel_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically process channel posts"""
    if not update.channel_post:
        return
    
    await handle_media(update, context, source="channel")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE, source="chat"):
    try:
        message = update.message or update.channel_post
        chat_id = message.chat_id
        
        # Check if media exists
        if message.photo:
            file = await message.photo[-1].get_file()
            media_type = "photo"
        elif message.video:
            file = await message.video.get_file()
            media_type = "video"
        else:
            if source == "chat":
                await message.reply_text("Please send a photo or video.")
            return

        # Download media
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            await file.download_to_drive(temp_file.name)
            input_path = temp_file.name

        # Process media
        output_ext = ".png" if media_type == "photo" else ".mp4"
        with tempfile.NamedTemporaryFile(suffix=output_ext, delete=False) as output_file:
            output_path = output_file.name

        if media_type == "photo":
            await process_image(input_path, output_path)
        else:
            await process_video(input_path, output_path)

        # Send processed media
        with open(output_path, "rb") as f:
            if source == "channel":
                # Edit original channel post
                if media_type == "photo":
                    await context.bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message.message_id,
                        media=InputMediaPhoto(f)
                    )
                else:
                    await context.bot.edit_message_media(
                        chat_id=chat_id,
                        message_id=message.message_id,
                        media=InputMediaVideo(f)
                    )
            else:
                # Send new message in private chat
                caption = f"Processed by @{BOT_USERNAME}"
                if media_type == "photo":
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=f,
                        caption=caption
                    )
                else:
                    await context.bot.send_video(
                        chat_id=chat_id,
                        video=f,
                        caption=caption
                    )

    except Exception as e:
        logger.error(f"Error processing media: {e}")
        if source == "chat":
            await message.reply_text(f"❌ Error: {str(e)}")
    finally:
        # Cleanup
        for path in [input_path, output_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass

async def process_image(input_path: str, output_path: str):
    """Process image with watermark and sticker"""
    try:
        img = Image.open(input_path).convert("RGBA")
        
        # Add text watermark
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(FONT_PATH, int(img.width * TEXT_SIZE_RATIO))
        except:
            font = ImageFont.load_default()
        
        text = WATERMARK_TEXT
        text_width, text_height = draw.textsize(text, font=font)
        
        if TEXT_POSITION == "bottom-center":
            position = (
                (img.width - text_width) // 2,
                img.height - text_height - 20
            )
        
        # Text outline
        for x_offset in [-1, 0, 1]:
            for y_offset in [-1, 0, 1]:
                if x_offset or y_offset:
                    draw.text(
                        (position[0] + x_offset, position[1] + y_offset),
                        text,
                        font=font,
                        fill=TEXT_OUTLINE
                    )
        
        # Main text
        draw.text(position, text, font=font, fill=TEXT_COLOR)
        
        # Add sticker if exists
        if os.path.exists(STICKER_PATH):
            sticker = Image.open(STICKER_PATH).convert("RGBA")
            sticker_width = int(img.width * STICKER_SIZE)
            sticker = sticker.resize(
                (sticker_width, int(sticker_width * sticker.size[1] / sticker.size[0])),
                Image.Resampling.LANCZOS
            )
            position = (img.width - sticker.width - 10, img.height - sticker.height - 10)
            img.paste(sticker, position, sticker)
        
        img.save(output_path, "PNG")
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        raise

async def process_video(input_path: str, output_path: str):
    """Process video with watermark and sticker"""
    try:
        video = mp.VideoFileClip(input_path)
        
        # Add text watermark
        txt_clip = mp.TextClip(
            WATERMARK_TEXT,
            fontsize=video.w * TEXT_SIZE_RATIO,
            color='white',
            stroke_color='black',
            stroke_width=2
        )
        txt_clip = txt_clip.set_position(("center", "bottom")).set_duration(video.duration)
        
        # Add sticker if exists
        if os.path.exists(STICKER_PATH):
            sticker = Image.open(STICKER_PATH).convert("RGBA")
            sticker_width = int(video.w * STICKER_SIZE)
            sticker = sticker.resize(
                (sticker_width, int(sticker_width * sticker.size[1] / sticker.size[0])),
                Image.Resampling.LANCZOS
            )
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_sticker:
                sticker.save(temp_sticker.name, "PNG")
                sticker_clip = mp.ImageClip(temp_sticker.name).set_duration(video.duration)
                sticker_clip = sticker_clip.set_position(("right", "bottom"))
                final_clip = mp.CompositeVideoClip([video, txt_clip, sticker_clip])
        else:
            final_clip = mp.CompositeVideoClip([video, txt_clip])
        
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
    except Exception as e:
        logger.error(f"Video processing error: {e}")
        raise
    finally:
        video.close()
        if 'final_clip' in locals():
            final_clip.close()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again.")

def main():
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("process", process_media))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, process_media))
    app.add_handler(MessageHandler(filters.ChatType.CHANNELS, channel_post_handler))
    app.add_error_handler(error_handler)
    
    # Webhook setup for Render
    port = int(os.getenv("PORT", 8443))
    webhook_url = os.getenv("WEBHOOK_URL")
    
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{webhook_url}/{TOKEN}",
        secret_token="YOUR_SECRET_TOKEN"
    )

if __name__ == "__main__":
    main()

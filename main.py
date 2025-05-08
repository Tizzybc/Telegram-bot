import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, Filters, ContextTypes
from PIL import Image
import moviepy.editor as mp
import tempfile
import logging

# Bot configuration
TOKEN = os.getenv("TOKEN")  # Get token from environment variable
CAPTION = "Your default caption here"  # Customize your caption
STICKER_PATH = "sticker.png"  # Path to your sticker image (PNG with transparency)
STICKER_POSITION = "bottom-right"  # Options: top-left, top-right, bottom-left, bottom-right
STICKER_SIZE = 0.2  # Sticker size as a fraction of media width (e.g., 0.2 = 20%)

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! Send me a photo or video, and I'll add a caption and a sticker to it."
    )

def process_image(image_path: str, output_path: str) -> None:
    img = Image.open(image_path).convert("RGBA")
    sticker = Image.open(STICKER_PATH).convert("RGBA")
    img_width, img_height = img.size
    sticker_width = int(img_width * STICKER_SIZE)
    sticker = sticker.resize((sticker_width, int(sticker_width * sticker.size[1] / sticker.size[0])), Image.Resampling.LANCZOS)
    sticker_x, sticker_y = 0, 0
    margin = 10
    if STICKER_POSITION == "top-left":
        sticker_x, sticker_y = margin, margin
    elif STICKER_POSITION == "top-right":
        sticker_x, sticker_y = img_width - sticker.width - margin, margin
    elif STICKER_POSITION == "bottom-left":
        sticker_x, sticker_y = margin, img_height - sticker.height - margin
    elif STICKER_POSITION == "bottom-right":
        sticker_x, sticker_y = img_width - sticker.width - margin, img_height - sticker.height - margin
    img.paste(sticker, (sticker_x, sticker_y), sticker)
    img.save(output_path, "PNG")

def process_video(video_path: str, output_path: str) -> None:
    video = mp.VideoFileClip(video_path)
    sticker = Image.open(STICKER_PATH).convert("RGBA")
    video_width, video_height = video.size
    sticker_width = int(video_width * STICKER_SIZE)
    sticker = sticker.resize((sticker_width, int(sticker_width * sticker.size[1] / sticker.size[0])), Image.Resampling.LANCZOS)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_sticker:
        sticker.save(temp_sticker.name, "PNG")
        sticker_clip = mp.ImageClip(temp_sticker.name, duration=video.duration)
    margin = 10
    if STICKER_POSITION == "top-left":
        sticker_clip = sticker_clip.set_position((margin, margin))
    elif STICKER_POSITION == "top-right":
        sticker_clip = sticker_clip.set_position((video_width - sticker_width - margin, margin))
    elif STICKER_POSITION == "bottom-left":
        sticker_clip = sticker_clip.set_position((margin, video_height - sticker.size[1] - margin))
    elif STICKER_POSITION == "bottom-right":
        sticker_clip = sticker_clip.set_position((video_width - sticker_width - margin, video_height - sticker.size[1] - margin))
    final_video = mp.CompositeVideoClip([video, sticker_clip])
    final_video.write(output_path, codec="libx264", audio_codec="aac")
    video.close()
    final_video.close()
    os.remove(temp_sticker.name)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    chat_id = message.chat_id
    if message.photo:
        file = await message.photo[-1].get_file()
        media_type = "photo"
    elif message.video:
        file = await message.video.get_file()
        media_type = "video"
    else:
        await message.reply_text("Please send a photo or video.")
        return
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        await file.download_to_drive(temp_file.name)
        input_path = temp_file.name
    output_ext = ".png" if media_type == "photo" else ".mp4"
    with tempfile.NamedTemporaryFile(suffix=output_ext, delete=False) as output_file:
        output_path = output_file.name
    try:
        if media_type == "photo":
            process_image(input_path, output_path)
        else:
            process_video(input_path, output_path)
        with open(output_path, "rb") as f:
            if media_type == "photo":
                await context.bot.send_photo(chat_id=chat_id, photo=f, caption=CAPTION)
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption=CAPTION)
    except Exception as e:
        await message.reply_text(f"Error processing media: {str(e)}")
    finally:
        os.remove(input_path)
        os.remove(output_path)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")

def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(Filters.photo | Filters.video, handle_media))
    app.add_error_handler(error_handler)
    port = int(os.getenv("PORT", 8443))
    webhook_url = os.getenv("WEBHOOK_URL")  # Set in Render environment
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=TOKEN,
        webhook_url=f"{webhook_url}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
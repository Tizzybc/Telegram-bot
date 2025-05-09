from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a photo or video!")

async def handle_photo(update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    await photo.get_file().download("temp.jpg")
    await update.message.reply_photo("temp.jpg", caption="Processed by MyMobileBot")

async def handle_video(update, context: ContextTypes.DEFAULT_TYPE):
    video = update.message.video
    await video.get_file().download("temp.mp4")
    await update.message.reply_video("temp.mp4", caption="Processed by MyMobileBot")

def main():
    application = Application.builder().token(os.getenv("TOKEN")).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO & ~filters.COMMAND, handle_video))
    webhook_url = f"{os.getenv('WEBHOOK_URL')}/{os.getenv('TOKEN')}"
    application.run_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", 8443)), url_path=os.getenv("TOKEN"), webhook_url=webhook_url)
    print("Bot is running...")

if __name__ == "__main__":
    main()

import os
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from datetime import datetime, timedelta
import pytz
import asyncio

# ===== CONFIGURATION =====
TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]
TIMEZONE = pytz.timezone(os.getenv("TIMEZONE", "UTC"))

# ===== LOGGING =====
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== DATABASE SETUP (Example using TinyDB) =====
from tinydb import TinyDB, Query
db = TinyDB('db.json')
channels_db = db.table('channels')
scheduled_posts_db = db.table('scheduled_posts')

# ===== KEYBOARDS =====
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Create Post", callback_data="create_post")],
        [InlineKeyboardButton("🗓 Scheduled Posts", callback_data="scheduled_posts")],
        [InlineKeyboardButton("👥 User Management", callback_data="user_mgmt")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
    ])

def post_options_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Button", callback_data="add_button")],
        [InlineKeyboardButton("⏱ Schedule", callback_data="schedule_post")],
        [InlineKeyboardButton("📤 Post Now", callback_data="post_now")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ])

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with main menu"""
    user = update.effective_user
    welcome_text = (
        f"👋 Welcome {user.first_name} to Channel Manager Pro!\n\n"
        "📢 Create and schedule posts across multiple channels\n"
        "👥 Manage subscribers and welcome messages\n"
        "⏱ Automate your content delivery\n\n"
        "What would you like to do today?"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=main_menu_keyboard())

async def handle_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage connected channels"""
    query = update.callback_query
    await query.answer()
    
    channels = channels_db.all()
    if not channels:
        text = "No channels connected yet!\n\nClick below to add your first channel:"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ])
    else:
        text = "📢 Your Connected Channels:\n\n"
        buttons = []
        for channel in channels:
            text += f"• {channel['title']} (ID: {channel['id']})\n"
            buttons.append([InlineKeyboardButton(
                f"⚙️ {channel['title']}", 
                callback_data=f"channel_{channel['id']}"
            )])
        
        buttons.append([InlineKeyboardButton("➕ Add Channel", callback_data="add_channel")])
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        keyboard = InlineKeyboardMarkup(buttons)
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post creation workflow"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['creating_post'] = True
    await query.edit_message_text(
        "✍️ Send me the content for your post (text, photo, video, or document):\n\n"
        "You can add formatting like:\n"
        "*bold* _italic_ `code` [links](https://example.com)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Cancel", callback_data="main_menu")]
        ])
    )

async def schedule_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule post for later"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⏰ When should I send this post?\n\n"
        "Send date/time in format: DD-MM-YYYY HH:MM\n"
        "Example: 15-05-2023 14:30",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="post_options")]
        ])
    )
    context.user_data['awaiting_schedule'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all incoming messages"""
    if update.message:
        if context.user_data.get('creating_post'):
            # Store post content
            context.user_data['post_content'] = {
                'text': update.message.text or update.message.caption,
                'type': 'text',
                'media': None
            }
            
            if update.message.photo:
                context.user_data['post_content']['type'] = 'photo'
                context.user_data['post_content']['media'] = update.message.photo[-1].file_id
            elif update.message.video:
                context.user_data['post_content']['type'] = 'video'
                context.user_data['post_content']['media'] = update.message.video.file_id
            
            await update.message.reply_text(
                "✅ Post content saved! Choose an option:",
                reply_markup=post_options_keyboard()
            )
            del context.user_data['creating_post']
            
        elif context.user_data.get('awaiting_schedule'):
            try:
                schedule_time = datetime.strptime(update.message.text, "%d-%m-%Y %H:%M")
                schedule_time = TIMEZONE.localize(schedule_time)
                
                if schedule_time < datetime.now(TIMEZONE):
                    await update.message.reply_text("⚠️ Please enter a future date/time")
                    return
                
                # Store scheduled post
                post_id = scheduled_posts_db.insert({
                    'content': context.user_data['post_content'],
                    'schedule_time': schedule_time.timestamp(),
                    'channels': context.user_data.get('selected_channels', []),
                    'user_id': update.message.from_user.id
                })
                
                await update.message.reply_text(
                    f"✅ Post scheduled for {schedule_time.strftime('%d %b %Y at %H:%M')}",
                    reply_markup=main_menu_keyboard()
                )
                del context.user_data['awaiting_schedule']
                
                # Schedule the task
                delay = (schedule_time - datetime.now(TIMEZONE)).total_seconds()
                asyncio.create_task(send_scheduled_post(context.application, post_id, delay))
                
            except ValueError:
                await update.message.reply_text("⚠️ Invalid format. Please use DD-MM-YYYY HH:MM")

async def send_scheduled_post(app, post_id, delay):
    """Send scheduled post after delay"""
    await asyncio.sleep(delay)
    post = scheduled_posts_db.get(doc_id=post_id)
    
    if post:
        content = post['content']
        for channel_id in post['channels']:
            try:
                if content['type'] == 'text':
                    await app.bot.send_message(
                        chat_id=channel_id,
                        text=content['text'],
                        parse_mode="Markdown"
                    )
                elif content['type'] == 'photo':
                    await app.bot.send_photo(
                        chat_id=channel_id,
                        photo=content['media'],
                        caption=content['text'],
                        parse_mode="Markdown"
                    )
                elif content['type'] == 'video':
                    await app.bot.send_video(
                        chat_id=channel_id,
                        video=content['media'],
                        caption=content['text'],
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Failed to send post to {channel_id}: {e}")
        
        scheduled_posts_db.remove(doc_ids=[post_id])

# ===== MAIN =====
def main():
    """Start the bot"""
    app = Application.builder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(handle_channels, pattern="^channel_mgmt$"))
    app.add_handler(CallbackQueryHandler(create_post, pattern="^create_post$"))
    app.add_handler(CallbackQueryHandler(schedule_post, pattern="^schedule_post$"))
    
    # Messages
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Scheduled tasks
    app.job_queue.run_repeating(check_scheduled_posts, interval=300, first=10)
    
    # Start
    app.run_polling()

if __name__ == "__main__":
    main()

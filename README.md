# Telegram Bot - Quick Setup

## 📦 Files Included

All the files you need to run the bot:

```
bot_files/
├── main.py                  # Main bot file
├── requirements.txt         # Dependencies
├── .env.example            # Configuration template
├── config/
│   └── settings.py         # Config loader
├── database/
│   ├── models.py           # Database models
│   └── manager.py          # Database operations
├── handlers/
│   ├── menu.py             # Main menu
│   ├── settings.py         # Settings
│   └── channel.py          # Channel handlers
└── utils/
    └── keyboards.py        # Keyboard layouts
```

## 🚀 Quick Start

### Step 1: Install Dependencies

```bash
pip install aiogram==3.7.0
pip install sqlalchemy==2.0.30
pip install aiosqlite==0.20.0
pip install python-dotenv==1.0.0
```

Or use requirements.txt:
```bash
pip install -r requirements.txt
```

### Step 2: Create .env File

Copy `.env.example` to `.env` and fill in your values:

```env
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_IDS=your_user_id
MY_CHANNEL_ID=-1001234567890
FIRST_COMMENT_ENABLED=True
FIRST_COMMENT_TEXT=👇 Share your thoughts below!
```

### Step 3: Get Your Credentials

**Bot Token:**
1. Open Telegram → Search @BotFather
2. Send `/newbot`
3. Copy the token

**Your User ID:**
1. Open Telegram → Search @userinfobot
2. Send `/start`
3. Copy your ID

**Channel ID:**
1. Forward a message from your channel to @userinfobot
2. Copy the channel ID (starts with -100)

### Step 4: Run the Bot

```bash
python main.py
```

You should see:
```
[INFO] Database initialized
[INFO] Aiogram bot initialized
[INFO] Bot is ready!
```

### Step 5: Test It

1. Open your bot in Telegram
2. Send `/start`
3. See the main menu appear! ✨

## ✅ Features

- ✅ 8-row main menu with 14 buttons
- ✅ First comment automation
- ✅ Settings management
- ✅ Database tracking
- ✅ Easy configuration

## 🐛 Troubleshooting

**"No module named 'aiogram'"**
→ Install dependencies: `pip install -r requirements.txt`

**"BOT_TOKEN is not set"**
→ Create .env file with your token

**Bot doesn't respond**
→ Make sure bot is admin in your channel

## 📱 Where to Run

- ✅ Computer (best)
- ✅ Pterodactyl panel (great)
- ✅ VPS/Cloud server (perfect)
- ⚠️ Mobile (unstable)

## 🎉 That's It!

Your bot is ready to use. Enjoy! 🚀

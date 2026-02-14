import asyncio

import logging

from aiogram import Bot, Dispatcher

from aiogram.client.default import DefaultBotProperties

from aiogram.enums import ParseMode

from config.settings import config

from database.manager import DatabaseManager

from handlers import menu, settings, channel

# Configure logging

logging.basicConfig(

    level=logging.INFO,

    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',

    handlers=[

        logging.FileHandler('bot.log'),

        logging.StreamHandler()

    ]

)

logger = logging.getLogger(__name__)

async def main():

    """

    Main function that runs the Aiogram bot.

    Simplified version without Pyrogram scraper.

    """

    

    # Validate configuration

    if not config.BOT_TOKEN:

        raise ValueError("BOT_TOKEN is not set in environment variables")

    

    logger.info("Starting Telegram Management Bot...")

    

    # Initialize database

    db = DatabaseManager(config.DATABASE_URL)

    await db.create_tables()

    logger.info("Database initialized")

    

    # Initialize the Aiogram bot

    bot = Bot(

        token=config.BOT_TOKEN,

        default=DefaultBotProperties(parse_mode=ParseMode.HTML)

    )

    dp = Dispatcher()

    

    # Register routers (order matters!)

    dp.include_router(menu.router)

    dp.include_router(settings.router)

    dp.include_router(channel.router)

    

    # Make database available to handlers

    dp["db"] = db

    

    logger.info("Aiogram bot initialized")

    logger.info("=" * 50)

    logger.info("Bot is ready!")

    logger.info("=" * 50)

    

    try:

        await dp.start_polling(bot)

    except Exception as e:

        logger.error(f"Error in bot polling: {e}", exc_info=True)

    finally:

        await bot.session.close()

        logger.info("Bot stopped")

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        logger.info("Bot stopped by user")

    except Exception as e:

        logger.error(f"Failed to start bot: {e}", exc_info=True)


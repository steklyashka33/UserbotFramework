import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

import aiogram
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ISOLATION: Get MVP root for imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Import from root
from bot_server import handlers
from shared.config import BOT_PORT
from shared.logging_utils import setup_logger

# Log configuration
logger = setup_logger("BOT")

# Load settings from the local .env in the MVP root
load_dotenv(BASE_DIR / ".env", override=True)
BOT_TOKEN = os.getenv("API_TOKEN", "")

# Aiogram setup
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(handlers.router)

# ----------------- WEBHOOK SERVER ----------------- #
async def webhook_handler(request: web.Request):
    data = await request.json()
    event = data.get("event")
    session_id = data.get("session_id")

    if event == "SESSION_DIED":
        logger.warning(f"Userbot session {session_id} died!")
        
    return web.json_response({"status": "ok"})

async def start_webhook_listener():
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', int(BOT_PORT))
    await site.start()
    logger.info(f"Webhook Listener started on port {BOT_PORT}")

async def main():
    """Start bot with an infinite connection loop on network failures."""
    # Disable "scary" aiohttp/aiogram logs on disconnects
    logging.getLogger('aiogram').setLevel(logging.CRITICAL)
    logging.getLogger('aiohttp').setLevel(logging.CRITICAL)

    # Start manager webhook listener ONLY ONCE
    try:
        await start_webhook_listener()
    except Exception as e:
        logger.error(f"Webhook listener is already running or port error: {type(e).__name__} - {e}")

    while True:
        try:
            # Check connection with Telegram
            bot_info = await bot.get_me()
            logger.info(f"Bot successfully authorized: @{bot_info.username}")
            
            logger.info("Bot Server started. Waiting for commands...")
            # Drop pending updates and start polling
            await bot.delete_webhook(drop_pending_updates=True)
            await dp.start_polling(bot)
            break 

        except (aiogram.exceptions.TelegramNetworkError, asyncio.TimeoutError):
            logger.warning("Telegram API connection error. Retrying in 10 sec...")
            await asyncio.sleep(10)
        except Exception as e:
            logger.critical(f"Unexpected bot error: {type(e).__name__} - {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")

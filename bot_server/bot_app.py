import os
import sys
import asyncio
import logging
from pathlib import Path

import aiogram
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ISOLATION: Get UserbotFramework root for imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Import from root
from bot_server import handlers
from shared.config import BOT_PORT, HIDE_API_LOGS, BOT_TOKEN
from shared.logging_utils import setup_logger

# Log configuration
logger = setup_logger("BOT")

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
        reason = data.get("reason")
        # logger.warning(f"Userbot session {session_id} died! Reason: {reason}")
        
        try:
            user_id = int(session_id)
            
            # Human-friendly messages instead of technical reasons
            if reason == "login_incomplete":
                friendly_msg = (
                    "⏳ **Authorization was not completed.**\n\n"
                    "It looks like you started logging in but didn't enter the code or cloud password (2FA) in time. "
                    "The session was automatically deleted for your security.\n\n"
                    "Try logging in again through the menu."
                )
            elif reason == "auth_revoked":
                friendly_msg = (
                    "ℹ️ **Session has been terminated!**\n\n"
                    "This happened because you selected 'Terminate other sessions' in Telegram settings "
                    "or the account was unlinked programmatically.\n\n"
                    "You can /login in again at any time through the menu."
                )
            elif reason == "banned":
                friendly_msg = (
                    "⚠️ **Account has been disabled by Telegram servers!**\n\n"
                    "It seems the session was forcibly terminated or the account was banned. "
                    "This usually happens due to suspicious activity.\n\n"
                    "We recommend using only clean, aged accounts."
                )
            else:
                friendly_msg = (
                    "❓ **Your userbot session has been stopped.**\n\n"
                    "An unexpected termination occurred.\n\n"
                    "Please try logging in again."
                )

            await bot.send_message(user_id, friendly_msg, parse_mode="Markdown")
            logger.info(f"User {user_id} notified about session status {reason}.")
        except Exception as e:
            logger.error(f"Could not notify user {session_id}: {type(e).__name__} - {e}")
        
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
    # Manage detail levels for network/API logs
    if HIDE_API_LOGS:
        logging.getLogger('aiogram').setLevel(logging.CRITICAL)
        logging.getLogger('aiohttp').setLevel(logging.CRITICAL)
    else:
        logging.getLogger('aiogram').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)

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
            # Process pending updates and start polling
            await bot.delete_webhook(drop_pending_updates=False)
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

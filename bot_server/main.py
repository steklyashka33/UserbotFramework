import sys
import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ISOLATION: Get MVP root for imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Import from root
from bot_server import handlers
from shared.config import BOT_PORT, BOT_TOKEN
from shared.logging_utils import setup_logger

# Log configuration
logger = setup_logger("BOT_CORE")

# Aiogram setup
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(handlers.router)

# ----------------- WEBHOOK SERVER ----------------- #
# Small built-in HTTP server for signals (webhooks) from Manager server
async def webhook_handler(request: web.Request):
    data = await request.json()
    event = data.get("event")
    phone = data.get("phone")

    if event == "SESSION_DIED":
        logger.warning(f"Session {phone} died (Webhook alert received).")
        
    return web.json_response({"status": "ok"})

async def start_webhook_server(runner: web.AppRunner):
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', int(BOT_PORT))
    await site.start()
    logger.info(f"Webhook Listener started on port {BOT_PORT}")

async def main():
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    
    runner = web.AppRunner(app)
    await start_webhook_server(runner)

    logger.info("Bot Server (Legacy Main) started. Waiting for commands...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot Service stopped.")

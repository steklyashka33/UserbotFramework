import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

# ISOLATION: Get MVP root for imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Import from root
from bot_server import handlers
from shared.config import BOT_PORT

# Load settings from the local .env in the MVP root
load_dotenv(BASE_DIR / ".env")
BOT_TOKEN = os.getenv("API_TOKEN", "")

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
        print(f"\n[WEBHOOK ALERT] Userbot session {phone} died!")
        # Here the bot could send notifications to admins
        
    return web.json_response({"status": "ok"})

async def start_webhook_server(runner: web.AppRunner):
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', int(BOT_PORT))
    await site.start()
    print(f"Bot Server: Webhook Listener started on port {BOT_PORT}")

async def main():
    if not BOT_TOKEN:
        print("Error: set API_TOKEN for bot in local .env file!")
        return
        
    app = web.Application()
    app.router.add_post('/webhook', webhook_handler)
    
    runner = web.AppRunner(app)
    await start_webhook_server(runner)

    print("Async Bot Server started and waiting for connection. Waiting for commands...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")

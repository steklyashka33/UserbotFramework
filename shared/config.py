import os
from pathlib import Path
from dotenv import load_dotenv

# Fundamental isolation: locate MVP root regardless of script execution path
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# Telethon settings, matching the original userbot
import random

# List of real devices for device masquerading
DEVICE_MODELS = [
    "SM-G981B", "SM-N986B", "Google Pixel 5", "Mi 10 Pro", "CPH2025", 
    "OnePlus 8 Pro", "Samsung S21 Ultra", "Redmi Note 10"
]
SYSTEM_VERSIONS = ["10.0", "11.0", "12.0", "13.0"]

# Generate a unique fingerprint for each session
DEVICE_CONFIG = {
    "device_model": random.choice(DEVICE_MODELS),
    "system_version": random.choice(SYSTEM_VERSIONS),
    "app_version": f"{random.randint(7, 9)}.{random.randint(0, 9)}.{random.randint(0, 5)}",
}

# API URL
# Support ports from ENV (for scalability) or use defaults
MANAGER_PORT = os.getenv("MANAGER_API_PORT", "8000")
BOT_PORT = os.getenv("BOT_WEBHOOK_PORT", "8001")

MANAGER_API_URL = f"http://127.0.0.1:{MANAGER_PORT}"
BOT_WEBHOOK_URL = f"http://127.0.0.1:{BOT_PORT}/webhook"

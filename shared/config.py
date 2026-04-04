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
    "Huawei NATCOM N8302",
    "Huawei VIETTEL V8404",
    "Huawei HUAWEI Y210-0251",
    "Huawei Pulse",
    "Huawei Grameenphone Crystal",
    "Xiaomi Redmi K30 Pro 5G",
    "Xiaomi MI 8 Explorer Edition",
    "Xiaomi MI 8 Pro",
    "Xiaomi MI 8 UD",
    "Samsung SM-A750FN", "Samsung SM-S908B", "Google Pixel 5",
    "OnePlus 8 Pro", "Samsung S21 Ultra", "Redmi Note 10"
]
SYSTEM_VERSIONS = [f"SDK {i}" for i in range(24, 36)]

# Generate a unique fingerprint for each session
# DEVICE_CONFIG = {
#     "device_model": random.choice(DEVICE_MODELS),
#     "system_version": random.choice(SYSTEM_VERSIONS),
#     "app_version": f"{random.randint(9, 12)}.{random.randint(0, 5)}.{random.randint(0, 4)}",
# }
DEVICE_CONFIG = {
    "device_model": "Samsung SM-A022G",
    "system_version": "SDK 31",
    "app_version": "12.6.2",
}

# Communication ports
# These define the ports for Manager API and Bot Webhook listener
MANAGER_PORT = "8000"
BOT_PORT = "8001"

# API URL
MANAGER_API_URL = f"http://127.0.0.1:{MANAGER_PORT}"
BOT_WEBHOOK_URL = f"http://127.0.0.1:{BOT_PORT}/webhook"

# Feature flags
# Set to True to display ALL active Telegram devices in /info, not just the current session
SHOW_ALL_SESSIONS_IN_INFO = False
# Clean up terminal: set to True to hide frequent API request logs (GET/POST ... 200 OK)
# Change to False if you need to debug API communication between Bot and Manager
HIDE_API_LOGS = True

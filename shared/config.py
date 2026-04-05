import os
import random
from pathlib import Path
from dotenv import load_dotenv

# --- CORE SETUP ---
# Fundamental isolation: locate project root regardless of script execution path
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# ──────────────────────────────────────────────────────────────────────────────
# PERSONAL CREDENTIALS (FROM .ENV)
# ──────────────────────────────────────────────────────────────────────────────
# These are unique to each user and should be kept private in your .env file.
# Telegram API credentials
API_ID    = int(os.getenv("API_ID", 0))
API_HASH  = os.getenv("API_HASH", "")
# Bot Token
BOT_TOKEN = os.getenv("API_TOKEN", "")

# ──────────────────────────────────────────────────────────────────────────────
# DEVICE MASQUERADE (Anti-Ban)
# ──────────────────────────────────────────────────────────────────────────────

# If True — a random device from the list below will be selected for each session.
# If False — a static device (Samsung SM-A022G) will be used for all sessions.
USE_RANDOM_DEVICE = False

DEVICE_MODELS = [
    "Huawei NATCOM N8302", "Huawei VIETTEL V8404", "Huawei HUAWEI Y210-0251", "Huawei Pulse",
    "Huawei Grameenphone Crystal", "Xiaomi Redmi K30 Pro 5G", "Xiaomi MI 8 Explorer Edition",
    "Xiaomi MI 8 Pro", "Xiaomi MI 8 UD", "Samsung SM-A750FN", "Samsung SM-S908B", 
    "Google Pixel 5", "OnePlus 8 Pro", "Samsung S21 Ultra", "Redmi Note 10"
]
SYSTEM_VERSIONS = [f"SDK {i}" for i in range(24, 36)]

if USE_RANDOM_DEVICE:
    # Dynamic configuration (refreshed on every restart)
    DEVICE_CONFIG = {
        "device_model": random.choice(DEVICE_MODELS),
        "system_version": random.choice(SYSTEM_VERSIONS),
        "app_version": f"{random.randint(9, 12)}.{random.randint(0, 5)}.{random.randint(0, 4)}",
    }
else:
    # Static configuration (keeps your device fingerprint consistent)
    DEVICE_CONFIG = {
        "device_model": "Samsung SM-A022G",
        "system_version": "SDK 31",
        "app_version": "12.6.2",
    }

# ──────────────────────────────────────────────────────────────────────────────
# NETWORK CONFIGURATION (Manager & Bot Communication)
# ──────────────────────────────────────────────────────────────────────────────

# Host addresses: "127.0.0.1" if both Manager and Bot run on the same machine.
MANAGER_HOST = "127.0.0.1"   # Where Bot sends API requests to Manager
BOT_HOST     = "127.0.0.1"   # Where Manager sends Webhook notifications to Bot

# Ports used for inter-service communication
MANAGER_PORT = "8000"
BOT_PORT     = "8001"

# Assembled URLs (do not change unless you use an HTTPS proxy or custom path)
MANAGER_API_URL  = f"http://{MANAGER_HOST}:{MANAGER_PORT}"
BOT_WEBHOOK_URL  = f"http://{BOT_HOST}:{BOT_PORT}/webhook"

# ──────────────────────────────────────────────────────────────────────────────
# FEATURE FLAGS & LOGGING
# ──────────────────────────────────────────────────────────────────────────────

# Set to True to display ALL active Telegram devices in /info, not just the current session.
SHOW_ALL_SESSIONS_IN_INFO = False

# Clean up console: Set to True to hide frequent API status logs (GET/POST ... 200 OK).
# Set to False if you need to debug communication between Bot and Manager.
HIDE_API_LOGS = True

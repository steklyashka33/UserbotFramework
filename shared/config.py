import os
import random
from pathlib import Path
from dotenv import load_dotenv

# --- SETUP ---
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

# If True — each session gets its own unique (but stable) device profile.
# If False — every session uses the STATIC_DEVICE_CONFIG defined below.
USE_UNIQUE_DEVICES = True

# Values used when USE_UNIQUE_DEVICES is False
STATIC_DEVICE_CONFIG = {
    "device_model": "Samsung SM-A022G",
    "system_version": "SDK 31",
    "app_version": "12.6.2",
}

DEVICE_MODELS = [
    "Samsung SM-S918B", "Samsung SM-G998B", "Samsung SM-A546B", "Google Pixel 8 Pro", 
    "Google Pixel 7a", "OnePlus 11 5G", "Xiaomi 13 Ultra", "Xiaomi Redmi Note 12 Pro", 
    "Huawei P60 Pro", "Realme GT3", "Nothing Phone (2)", "Sony Xperia 1 V",
    "Samsung SM-A750FN", "Google Pixel 5", "OnePlus 8 Pro"
]
SYSTEM_VERSIONS = [f"SDK {i}" for i in range(28, 36)] # Android 9–16

def get_device_info(session_id: str) -> dict:
    """
    Generate deterministic device metadata for a session.
    The same session_id will ALWAYS return the same device info.
    This ensures consistency while providing uniqueness between accounts.
    """
    if not USE_UNIQUE_DEVICES:
        return STATIC_DEVICE_CONFIG

    # Seeding the random generator locally to ensure deterministic output per session
    rng = random.Random(session_id)
    return {
        "device_model": rng.choice(DEVICE_MODELS),
        "system_version": rng.choice(SYSTEM_VERSIONS),
        "app_version": f"{rng.randint(10, 12)}.{rng.randint(1, 6)}.{rng.randint(0, 5)}",
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

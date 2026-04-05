import sys
import os
import subprocess
import time
from pathlib import Path
from shared.logging_utils import setup_logger

# Log configuration for the main entry point
logger = setup_logger("SYSTEM_ENGINE")

# ISOLATION: Locate CoreUserbot root for 'shared' imports
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from shared.config import MANAGER_PORT, BOT_PORT

def start_system():
    logger.info("="*30)
    logger.info("CoreUserbot: STARTING")
    logger.info(f"Manager Service: Port {MANAGER_PORT}")
    logger.info(f"Bot Service:     Port {BOT_PORT}")
    logger.info("="*30)

    # Path to Python interpreter
    python_exe = sys.executable

    # Start Bot Server
    logger.info("Starting Bot Server...")
    bot_env = os.environ.copy()
    bot_env["PYTHONPATH"] = str(BASE_DIR)

    bot_proc = subprocess.Popen(
        [python_exe, "-m", "bot_server.bot_app"],
        cwd=str(BASE_DIR),
        env=bot_env
    )

    time.sleep(5)  # Allow Bot (and its webhook listener) to warm up

    # Start Manager Server
    logger.info("Starting Manager Server...")
    manager_env = os.environ.copy()
    manager_env["PYTHONPATH"] = str(BASE_DIR)
    
    manager_proc = subprocess.Popen(
        [python_exe, "-m", "manager_server.server_app"],
        cwd=str(BASE_DIR),
        env=manager_env
    )

    try:
        # Keep the main process alive as long as children are alive
        while True:
            if bot_proc.poll() is not None:
                logger.error("Bot Server stopped unexpectedly.")
                break
            if manager_proc.poll() is not None:
                logger.error("Manager Server stopped unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bot_proc.terminate()
        manager_proc.terminate()
        logger.info("All processes stopped. 👋")

if __name__ == "__main__":
    start_system()

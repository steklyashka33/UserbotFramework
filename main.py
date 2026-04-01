import sys
import os
import subprocess
import time
from pathlib import Path
from shared.logging_utils import setup_logger

# Log configuration for the main entry point
logger = setup_logger("SYSTEM_ENGINE")

# 1. Locate the MVP root
MVP_ROOT = Path(__file__).resolve().parent

def start_system():
    logger.info("="*30)
    logger.info("USERBOT API MVP: STARTING")
    logger.info("="*30)

    # Path to Python interpreter
    python_exe = sys.executable

    # Start Manager Server
    logger.info("Starting Manager Server...")
    manager_env = os.environ.copy()
    manager_env["PYTHONPATH"] = str(MVP_ROOT)
    
    manager_proc = subprocess.Popen(
        [python_exe, "-m", "manager_server.server_app"],
        cwd=str(MVP_ROOT),
        env=manager_env
    )

    time.sleep(3) # Give API server time to warm up

    # Start Bot Server
    logger.info("Starting Bot Server...")
    bot_env = os.environ.copy()
    bot_env["PYTHONPATH"] = str(MVP_ROOT)

    bot_proc = subprocess.Popen(
        [python_exe, "-m", "bot_server.bot_app"],
        cwd=str(MVP_ROOT),
        env=bot_env
    )

    try:
        # Keep the main process alive as long as children are alive
        while True:
            if manager_proc.poll() is not None:
                logger.error("Manager Server stopped unexpectedly.")
                break
            if bot_proc.poll() is not None:
                logger.error("Bot Server stopped unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        manager_proc.terminate()
        bot_proc.terminate()
        logger.info("All processes stopped. 👋")

if __name__ == "__main__":
    start_system()

import asyncio
import logging
import aiohttp
from pathlib import Path
import sys
import os

# Add MVP root to sys.path to import 'shared'
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from .client import TelegramClientForBot
from shared.config import DEVICE_CONFIG, BOT_WEBHOOK_URL
from shared.logging_utils import setup_logger

# Log configuration for each session
logger = setup_logger("ACCOUNT")

CONNECTION_CHECK_DELAY = 10

class Account:
    """Client wrapper for continuous operation in memory."""
    GLOBAL_NETWORK_OK = True # Global flag for all sessions
    
    def __init__(self, session_id: str, api_id: int, api_hash: str):
        self.session_id = str(session_id)
        self.api_id = api_id
        self.api_hash = api_hash
        
        # Ensure that the sessions folder exists
        session_dir = BASE_DIR / "sessions"
        os.makedirs(session_dir, exist_ok=True)
        session_path = str(session_dir / self.session_id)

        # Telethon instance: strict limits to prevent server hang on Windows
        self.client = TelegramClientForBot(
            session_path, 
            api_id, 
            api_hash,
            connection_retries=0, # IMPORTANT: 0, so it crashes immediately on error
            auto_reconnect=False, # IMPORTANT: do not let it go into network wait on its own
            timeout=5,            # Timeout for network request
            **DEVICE_CONFIG,
            lang_code="en",
            system_lang_code="en-US"
        )
        self.is_running = False
        self._monitor_task = None
        self._network_warning_sent = False # Flag to avoid spamming logs

    async def start_monitoring(self):
        """Start Health Check for the session. Connection is inside the loop only!"""
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())

    async def _monitoring_loop(self):
        """Check health every 10 seconds. Filter out internet connection issues."""
        from telethon.errors import AuthKeyUnregisteredError, SessionRevokedError, UserDeactivatedError, UserDeactivatedBanError
        import asyncio

        while self.is_running:
            try:
                # If connection is lost - just try to reconnect without "killing" the session
                if not self.client.is_connected():
                    try:
                        # Limit the ENTIRE connection process (DNS + TCP + Handshake)
                        await asyncio.wait_for(self.client.connect(), timeout=7.0)
                        
                        if not Account.GLOBAL_NETWORK_OK:
                            logger.info("Connection to Telegram restored! Sessions are resuming work.")
                            Account.GLOBAL_NETWORK_OK = True
                    except (asyncio.TimeoutError, ConnectionError, OSError, asyncio.IncompleteReadError) as e:
                        # IMPORTANT: If the connection "hangs" or drops on the read phase
                        await self.client.disconnect()
                        raise # Throw to the main monitor except
                
                # Request state (fast request). Returns False if authorization is lost.
                if not await self.client.is_user_authorized():
                    await self._handle_death(reason="auth_revoked")
                    break

            except (ConnectionError, asyncio.TimeoutError, OSError, asyncio.IncompleteReadError) as e:
                # Internet issues (e.g. VPN turned off)
                if Account.GLOBAL_NETWORK_OK:
                    logger.warning(f"Connection to Telegram lost ({type(e).__name__}). All sessions go into wait mode...")
                    Account.GLOBAL_NETWORK_OK = False
                await asyncio.sleep(CONNECTION_CHECK_DELAY)
                continue
            except (AuthKeyUnregisteredError, SessionRevokedError, UserDeactivatedError, UserDeactivatedBanError) as e:
                # Telegram server forcibly terminated our session!
                logger.error(f"Telegram server kicked session {self.session_id}: {type(e).__name__} - {e}")
                await self._handle_death(reason="banned")
                break
            except Exception as e:
                # Crash due to an unexpected server error
                logger.error(f"Unexpected health check failure for session {self.session_id}: {type(e).__name__} - {e}")
                if "AuthKey" in str(e) or "Deactivated" in str(e) or "Revoked" in str(e):
                    await self._handle_death(reason="banned")
                    break
                
            await asyncio.sleep(CONNECTION_CHECK_DELAY)

    async def _handle_death(self, reason=None):
        """Session death. Notify the bot via Webhook and delete files."""
        self.is_running = False
        logger.warning(f"Session {self.session_id} died. Reason: {reason}. Sending Webhook to Bot.")
        
        # If the session died due to key revocation, delete the file so it wouldn't load again
        if reason in ["auth_revoked", "banned"]:
            try:
                await self.client.disconnect()
                session_file = BASE_DIR / "sessions" / f"{self.session_id}.session"
                if os.path.exists(session_file):
                    os.remove(session_file)
                    logger.info(f"Dead session file {self.session_id} permanently deleted.")
            except Exception as e:
                logger.error(f"Failed to delete session file {self.session_id}: {type(e).__name__} - {e}")

        try:
            async with aiohttp.ClientSession() as session:
                payload = {"event": "SESSION_DIED", "session_id": self.session_id, "reason": reason}
                async with session.post(BOT_WEBHOOK_URL, json=payload) as resp:
                    pass # Webhook sent successfully
        except Exception as e:
            logger.error(f"Failed to send Webhook for session {self.session_id}: {type(e).__name__} - {e}")

    async def stop(self):
        """Forcible session stop."""
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        await self.client.disconnect()
        logger.info(f"Account {self.session_id} stopped manually.")

    async def logout(self):
        """Complete session logout and deletion."""
        logger.warning(f"Session {self.session_id} is being logged out manually.")
        self.is_running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        
        try:
            if not self.client.is_connected():
                await self.client.connect()
            await self.client.log_out()
        except Exception as e:
            logger.error(f"Error logging out of account {self.session_id}: {type(e).__name__} - {e}")
        finally:
            await self.client.disconnect()
            
            # Delete file
            session_file = BASE_DIR / "sessions" / f"{self.session_id}.session"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    logger.info(f"Session file {session_file} deleted on logout.")
                except Exception as e:
                    logger.error(f"Failed to delete session file {self.session_id} on logout: {type(e).__name__} - {e}")

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
    
    def __init__(self, session_id: str, api_id: int, api_hash: str, on_death=None):
        self.session_id = str(session_id)
        self.api_id = api_id
        self.api_hash = api_hash
        self.on_death = on_death
        
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
        self._warm_up_task = None
        self._network_warning_sent = False # Flag to avoid spamming logs
        self._ready_event = asyncio.Event()

    def _shutdown(self):
        """
        Stop the session and cancel all background tasks.
        """
        self.is_running = False
        self._ready_event.clear()
        current = asyncio.current_task()
        for task in (self._monitor_task, self._warm_up_task):
            if task and not task.done() and task is not current:
                task.cancel()

    async def wait_until_ready(self, timeout=10.0):
        """Wait until the session is connected and authorized."""
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


    async def warm_up(self):
        """
        Imitate real Telegram client behavior right after login with gradual delays.
        Official apps execute this chain: GetConfig -> GetAppConfig -> GetPrivacy -> GetNotifySettings.
        """
        from telethon import functions, types
        import random

        # Initial wait to let the session stabilize
        await asyncio.sleep(random.uniform(3, 7))

        steps = [
            ("GetConfig", lambda: functions.help.GetConfigRequest()),
            ("GetAppConfig", lambda: functions.help.GetAppConfigRequest(hash=0)),
            ("GetPrivacy", lambda: functions.account.GetPrivacyRequest(
                key=types.InputPrivacyKeyStatusTimestamp()
            )),
            ("GetAuthorizations", lambda: functions.account.GetAuthorizationsRequest()),
            ("GetNotifySettings", lambda: functions.account.GetNotifySettingsRequest(
                peer=types.InputNotifyPeer(peer=types.InputPeerSelf())
            )),
        ]

        logger.info(f"Starting warm-up routine for {self.session_id}...")
        
        for name, build_req in steps:
            # Check if session was stopped during the process
            if not self.is_running: 
                break
                
            # Wait for connection if it drops during warm-up
            try:
                for _ in range(10): # Max 10 seconds wait
                    if self.client.is_connected(): break
                    await asyncio.sleep(1)
                
                await self.client(build_req())
                logger.debug(f"[warm_up] {self.session_id}: {name} OK")
            except Exception as e:
                logger.warning(f"[warm_up] {self.session_id}: {name} failed: {type(e).__name__} - {e}")
            
            # Gradual human-like delay between actions
            await asyncio.sleep(random.uniform(2, 5))
        
        logger.info(f"Warm-up routine for {self.session_id} completed.")


    async def start_monitoring(self):
        """Start Health Check and Warm-up for the session."""
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        self._warm_up_task = None

    async def _monitoring_loop(self):
        """Check health every 10 seconds. Filter out internet connection issues."""
        while self.is_running:
            try:
                # 1. Connection check (network layer)
                if not self.client.is_connected():
                    self._ready_event.clear()
                    try:
                        # Limit the ENTIRE connection process (DNS + TCP + Handshake)
                        await asyncio.wait_for(self.client.connect(), timeout=7.0)
                        
                        if not Account.GLOBAL_NETWORK_OK:
                            logger.info("Connection to Telegram restored! Sessions are resuming work.")
                            Account.GLOBAL_NETWORK_OK = True
                    except (asyncio.TimeoutError, ConnectionError, OSError, asyncio.IncompleteReadError) as e:
                        await self.client.disconnect()
                        raise # Catch in network block below

                # 2. Auth/Account health check (logic layer)
                if await self.ensure_alive():
                    # Account is dead (notified in ensure_alive), stop monitoring
                    break
                
                # We are alive and connected
                self._ready_event.set()

                if not self._warm_up_task:
                    # Start warm-up in parallel (it will proceed once connected)
                    self._warm_up_task = asyncio.create_task(self.warm_up())

            except (ConnectionError, asyncio.TimeoutError, OSError, asyncio.IncompleteReadError) as e:
                # Local or global network issues (VPN, API down, timeout)
                self._ready_event.clear()
                if Account.GLOBAL_NETWORK_OK:
                    logger.warning(f"Connection to Telegram lost ({type(e).__name__}). All sessions go into wait mode...")
                    Account.GLOBAL_NETWORK_OK = False
                await asyncio.sleep(CONNECTION_CHECK_DELAY)
                continue
            except Exception as e:
                # Critical bug or unexpected Telethon behavior
                logger.error(f"Critical error in monitoring loop for {self.session_id}: {type(e).__name__} - {e}")
                
            await asyncio.sleep(CONNECTION_CHECK_DELAY)

    async def _check_death_reason(self):
        """
        Internal check: returns False if alive, or reason string if dead.
        Handles both passive checks (get_me) and catching explicit Telethon death errors.
        """
        from telethon.errors import (
            AuthKeyUnregisteredError, SessionRevokedError, 
            UserDeactivatedError, UserDeactivatedBanError
        )
        try:
            me = await self.client.get_me()
            if me is None:
                # If key exists but user data is inaccessible - it's revoked
                if await self.client.is_user_authorized():
                    return "auth_revoked"
                else:
                    return "login_incomplete"
            return False # Session is alive
        except (UserDeactivatedError, UserDeactivatedBanError):
            return "banned"
        except (AuthKeyUnregisteredError, SessionRevokedError):
            return "auth_revoked"
        except Exception as e:
            # Check for death keywords in generic strings
            err_str = str(e).lower()
            if any(k in err_str for k in ["deactivated", "banned"]): return "banned"
            if any(k in err_str for k in ["auth", "revoked", "unregistered"]): return "auth_revoked"
            # It's some other non-critical error, let the loop continue
            return False

    async def ensure_alive(self) -> bool:
        """
        Active check: returns True if DIED and cleanup performed, False if still alive.
        Centralizes the logic for both checking and handling death.
        """
        death_reason = await self._check_death_reason()
        if death_reason:
            await self._handle_death(reason=death_reason)
            return True
        return False

    def _notify_on_death(self):
        """Invoke callback to remove account from Manager's memory."""
        if not self.on_death:
            return
            
        try:
            if asyncio.iscoroutinefunction(self.on_death):
                asyncio.create_task(self.on_death(self.session_id))
            else:
                self.on_death(self.session_id)
        except Exception:
            pass

    async def _handle_death(self, reason=None):
        """Session death. Notify the bot via Webhook and delete files."""
        if not self.is_running and reason != "login_incomplete": return # Avoid double death
        
        self._shutdown()
        self._notify_on_death()
            
        logger.warning(f"Session {self.session_id} died. Reason: {reason}. Cleaning up.")
        
        await self._logout()

        # Retry loop for Webhook (essential during cold start when Bot is warming up)
        for attempt in range(10):
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {"event": "SESSION_DIED", "session_id": self.session_id, "reason": reason}
                    async with session.post(BOT_WEBHOOK_URL, json=payload, timeout=2.0) as resp:
                        if resp.status == 200:
                            logger.info(f"Webhook delivered for session {self.session_id}")
                            return # Terminate on success
                break
            except Exception as e:
                if attempt < 9:
                    await asyncio.sleep(5) # Wait for Bot to wake up
                    continue
                logger.error(f"Failed to send Webhook for session {self.session_id} after 10 attempts: {type(e).__name__} - {e}")

    async def stop(self):
        """Forcible session stop."""
        self._shutdown()
        await self.client.disconnect()
        logger.info(f"Account {self.session_id} stopped manually.")

    async def logout(self):
        """Complete session logout and deletion."""
        logger.warning(f"Session {self.session_id} is being logged out manually.")
        self._shutdown()
        self._notify_on_death()
        await self._logout()
    
    async def _logout(self):
        try:
            if not self.client.is_connected():
                await asyncio.wait_for(self.client.connect(), timeout=7.0)
            await asyncio.wait_for(self.client.log_out(), timeout=7.0)
        except Exception as e:
            pass
        finally:
            await self.client.disconnect()
            
            # Delete file
            session_file = BASE_DIR / "sessions" / f"{self.session_id}.session"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    return True
                except Exception as e:
                    logger.error(f"Failed to delete session file {self.session_id} on logout: {type(e).__name__} - {e}")

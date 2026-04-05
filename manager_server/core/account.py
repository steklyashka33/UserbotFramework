import asyncio
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
from telethon.errors import (
    AuthKeyUnregisteredError, SessionRevokedError,
    UserDeactivatedError, UserDeactivatedBanError
)

# Log configuration for each session
logger = setup_logger("ACCOUNT")

CONNECTION_CHECK_DELAY = 10

# Network-level exceptions (not Telegram auth errors)
NETWORK_ERRORS = (asyncio.TimeoutError, ConnectionError, OSError, asyncio.IncompleteReadError)


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
            connection_retries=0,  # IMPORTANT: 0, so it crashes immediately on error
            auto_reconnect=False,  # IMPORTANT: do not let it go into network wait on its own
            timeout=5,             # Timeout for network request
            **DEVICE_CONFIG,
            lang_code="en",
            system_lang_code="en-US"
        )
        self.is_running = False
        self._monitor_task = None
        self._warm_up_task = None
        self._ready_event = asyncio.Event()

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────

    def _shutdown(self):
        """Stop the session and cancel all background tasks."""
        self.is_running = False
        self._ready_event.clear()
        current = asyncio.current_task()
        for task in (self._monitor_task, self._warm_up_task):
            if task and not task.done() and task is not current:
                task.cancel()

    async def wait_until_ready(self, timeout: float = 10.0) -> bool:
        """Wait until the session is connected and authorized."""
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def start_monitoring(self):
        """Start health check loop and warm-up for the session."""
        self.is_running = True
        self._ready_event.clear()
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        self._warm_up_task = None

    async def stop(self):
        """Forcible session stop (no Telegram logout, no file deletion)."""
        self._shutdown()
        await self.client.disconnect()
        logger.info(f"Account {self.session_id} stopped manually.")

    async def logout(self):
        """Complete session logout: stop tasks, notify Manager, logout from Telegram, delete file."""
        logger.warning(f"Session {self.session_id} is being logged out manually.")
        self._shutdown()
        self._notify_on_death()
        await self._logout()

    # ──────────────────────────────────────────────
    # Network layer (single source of truth)
    # ──────────────────────────────────────────────

    async def ensure_connected(self, timeout: float = 7.0):
        """
        Ensure the Telethon client is connected.

        - Does nothing if already connected.
        - Raises NETWORK_ERRORS on failure so callers can distinguish network vs auth errors.
        - Updates GLOBAL_NETWORK_OK flag on successful reconnect.
        - No side effects on _ready_event (managed only by _shutdown and _monitoring_loop).
        """
        if self.client.is_connected():
            return

        try:
            # Limit the ENTIRE connection process (DNS + TCP + Handshake)
            await asyncio.wait_for(self.client.connect(), timeout=timeout)

            if not Account.GLOBAL_NETWORK_OK:
                logger.info("Connection to Telegram restored! Sessions are resuming work.")
                Account.GLOBAL_NETWORK_OK = True
        except NETWORK_ERRORS:
            await self.client.disconnect()
            raise  # Let the caller handle the network error

    # ──────────────────────────────────────────────
    # Auth / health checks
    # ──────────────────────────────────────────────

    async def _check_death_reason(self):
        """
        Internal check: returns False if alive, or a reason string if the session is dead.
        Assumes the client is already connected — only checks the auth/logic layer.
        """
        try:
            me = await self.client.get_me()
            if me is None:
                # Key exists but user data is inaccessible
                authorized = await self.client.is_user_authorized()
                return "auth_revoked" if authorized else "login_incomplete"
            return False  # Session is alive
        except (UserDeactivatedError, UserDeactivatedBanError):
            return "banned"
        except (AuthKeyUnregisteredError, SessionRevokedError):
            return "auth_revoked"
        except Exception as e:
            # Check for death keywords in generic Telethon strings
            err_str = str(e).lower()
            if any(k in err_str for k in ["deactivated", "banned"]):
                return "banned"
            if any(k in err_str for k in ["auth", "revoked", "unregistered"]):
                return "auth_revoked"
            # Some other non-critical error — let the monitoring loop continue
            return False

    @property
    def session_file_exists(self) -> bool:
        """Check whether the .session file exists on disk."""
        return (BASE_DIR / "sessions" / f"{self.session_id}.session").exists()

    async def check_status(self) -> str:
        """
        Precisely diagnose the session state without side effects.
        Returns one of:
          - 'CONNECTED'       – running, connected and authorized
          - 'STOPPED'         – is_running=False but session file exists on disk
          - 'FILE_NOT_FOUND'  – is_running=False and no session file (was deleted/never logged in)
          - 'NO_NETWORK'      – client cannot connect to Telegram servers
          - 'NOT_AUTHORIZED'  – connected but login was never completed
          - 'DEAD'            – session revoked or account banned/deactivated
          - 'UNKNOWN_ERROR'   – some unexpected non-network, non-auth error

        Delegates connection to ensure_connected() and death detection to
        _check_death_reason() to avoid any logic duplication.
        """
        if not self.is_running:
            # Distinguish between "stopped but recoverable" and "file gone"
            return "STOPPED" if self.session_file_exists else "FILE_NOT_FOUND"

        try:
            await self.ensure_connected()
        except NETWORK_ERRORS:
            return "NO_NETWORK"

        death_reason = await self._check_death_reason()
        if death_reason == "login_incomplete":
            return "NOT_AUTHORIZED"
        if death_reason:
            return "DEAD"
        return "CONNECTED"

    async def probe_session(self) -> str:
        """
        Probe the real health of a stopped session by connecting and checking auth.
        Unlike check_status(), ignores is_running — always connects and verifies.

        Used before restarting a STOPPED session to avoid restarting a dead one.
        Returns: 'CONNECTED', 'NO_NETWORK', 'NOT_AUTHORIZED', 'DEAD'.
        """
        try:
            await self.ensure_connected()
        except NETWORK_ERRORS:
            return "NO_NETWORK"

        death_reason = await self._check_death_reason()
        if death_reason == "login_incomplete":
            return "NOT_AUTHORIZED"
        if death_reason:
            return "DEAD"
        return "CONNECTED"

    async def ensure_alive(self) -> bool:
        """
        Active check: returns True if the session DIED and cleanup was performed,
        False if the session is still alive.

        Assumes the client is already connected (called from _monitoring_loop).
        """
        death_reason = await self._check_death_reason()
        if death_reason:
            await self._handle_death(reason=death_reason)
            return True
        return False

    # ──────────────────────────────────────────────
    # Monitoring loop
    # ──────────────────────────────────────────────

    async def _monitoring_loop(self):
        """Check health every 10 seconds. Separate network errors from auth/logic errors."""
        while self.is_running:
            try:
                # 1. Network layer — ensure_connected raises on failure
                await self.ensure_connected()

                # 2. Auth/logic layer — check if account was revoked/banned
                if await self.ensure_alive():
                    break  # Account is dead, monitoring stopped inside ensure_alive

                # We are alive and connected
                self._ready_event.set()

                if not self._warm_up_task:
                    self._warm_up_task = asyncio.create_task(self.warm_up())

            except NETWORK_ERRORS as e:
                # Local or global network issues (VPN, API down, timeout)
                self._ready_event.clear()
                if Account.GLOBAL_NETWORK_OK:
                    logger.warning(
                        f"Connection to Telegram lost ({type(e).__name__}). "
                        "All sessions go into wait mode..."
                    )
                    Account.GLOBAL_NETWORK_OK = False
                await asyncio.sleep(CONNECTION_CHECK_DELAY)
                continue
            except Exception as e:
                # Critical bug or unexpected Telethon behavior — log, lower flag, keep looping
                logger.error(
                    f"Critical error in monitoring loop for {self.session_id}: "
                    f"{type(e).__name__} - {e}"
                )

            await asyncio.sleep(CONNECTION_CHECK_DELAY)

    # ──────────────────────────────────────────────
    # Warm-up
    # ──────────────────────────────────────────────

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
                for _ in range(10):
                    if await self.client.get_me():
                        break
                    await asyncio.sleep(3)

                await self.client(build_req())
                logger.debug(f"[warm_up] {self.session_id}: {name} OK")
            except Exception as e:
                logger.warning(f"[warm_up] {self.session_id}: {name} failed: {type(e).__name__} - {e}")

            # Gradual human-like delay between actions
            await asyncio.sleep(random.uniform(2, 5))

        logger.info(f"Warm-up routine for {self.session_id} completed.")

    # ──────────────────────────────────────────────
    # Request wrappers (keep server_app from touching client directly)
    # ──────────────────────────────────────────────

    async def request_phone_code(self, phone: str):
        """
        Connect and send a Telegram SMS code request for the given phone number.
        Returns the SendCodeRequest result (contains phone_code_hash).
        Raises on any network or Telegram error.
        """
        await self.ensure_connected()
        return await self.client.send_code_request(phone)

    # ──────────────────────────────────────────────
    # Death handling
    # ──────────────────────────────────────────────

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
        """Session death: shut down, notify Manager, delete files, notify Bot via Webhook."""
        if not self.is_running and reason != "login_incomplete":
            return  # Avoid double death

        self._shutdown()
        self._notify_on_death()

        logger.warning(f"Session {self.session_id} died. Reason: {reason}. Cleaning up.")

        await self._logout()

        # Retry loop for Webhook (essential during cold start when Bot is warming up)
        number_of_repetitions = 10
        for attempt in range(number_of_repetitions):
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {"event": "SESSION_DIED", "session_id": self.session_id, "reason": reason}
                    async with session.post(BOT_WEBHOOK_URL, json=payload, timeout=2.0) as resp:
                        if resp.status == 200:
                            logger.info(f"Webhook delivered for session {self.session_id}")
                            return # Terminate on success
                break
            except Exception as e:
                if attempt < (number_of_repetitions-1):
                    await asyncio.sleep(5) # Wait for Bot to wake up
                    continue
                logger.error(
                    f"Failed to send Webhook for session {self.session_id} "
                    f"after 10 attempts: {type(e).__name__} - {e}"
                )

    async def _logout(self):
        """Low-level cleanup: log out from Telegram, disconnect, delete session file."""
        try:
            await self.ensure_connected()
            await asyncio.wait_for(self.client.log_out(), timeout=7.0)
        except Exception:
            pass  # Best-effort: even if Telegram is unreachable, we still clean up locally
        finally:
            await self.client.disconnect()

            # Delete file
            session_file = BASE_DIR / "sessions" / f"{self.session_id}.session"
            if session_file.exists():
                try:
                    session_file.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete session file {self.session_id} on logout: {type(e).__name__} - {e}")

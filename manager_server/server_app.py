import os
import sys
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from telethon import functions
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError,
    PasswordHashInvalidError
)
from contextlib import asynccontextmanager

# ISOLATION: Locate MVP root for 'shared' imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Import from root
from manager_server.core.account import Account, NETWORK_ERRORS
from shared.config import HIDE_API_LOGS, API_ID, API_HASH
from shared.logging_utils import setup_logger

# Log configuration
logger = setup_logger("MANAGER")

def global_exception_handler(loop, context):
    """Hide scary internal asyncio/Telethon errors (IncompleteReadError) from the console."""
    msg = context.get("message", "")
    exc = context.get("exception", None)
    if exc and isinstance(exc, (asyncio.IncompleteReadError, ConnectionError, OSError)):
        return
    if "IncompleteReadError" in msg or "was never retrieved" in msg:
        return
    loop.default_exception_handler(context)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Silence API request logs if requested in config
    if HIDE_API_LOGS:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
        # Also handle potential direct logging from uvicorn's configuration
        logging.getLogger("uvicorn").setLevel(logging.WARNING)

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(global_exception_handler)
    asyncio.create_task(_load_accounts_bg())
    yield

app = FastAPI(lifespan=lifespan)

accounts = {}
sessions_hashes = {} 

async def _load_accounts_bg():
    """Background task for loading sessions."""
    try:
        session_dir = BASE_DIR / "sessions"
        os.makedirs(session_dir, exist_ok=True)
        loaded_count = 0
        logger.info("Extracting previous sessions (Zero-Wait)...")
        for file in os.listdir(session_dir):
            if file.endswith(".session"):
                session_id = file.replace(".session", "")
                try:
                    acc = Account(session_id, API_ID, API_HASH, on_death=lambda sid: accounts.pop(sid, None))
                    accounts[session_id] = acc
                    await acc.start_monitoring()
                    logger.info(f"Account {session_id} is connected.")
                    loaded_count += 1
                except Exception as e:
                    logger.error(f"Initialization error for {session_id}: {type(e).__name__} - {e}")
        logger.info(f"Session indexing completed ({loaded_count} accounts).")
    except Exception as fatal_e:
        logger.critical(f"Background session loading task failed completely: {type(fatal_e).__name__} - {fatal_e}")

class PhoneRequest(BaseModel):
    phone: str
    session_id: str

class LoginRequest(BaseModel):
    phone: str
    session_id: str
    code: str
    password: str = None

class SendMessageRequest(BaseModel):
    target: str
    text: str

async def _do_request_code(acc: Account, phone: str, session_id: str) -> dict:
    """
    Helper: send a Telegram code request and store the hash.
    Raises HTTPException on network or Telegram errors.
    Exists to avoid duplicating the try/except block in send_code.
    """
    try:
        res = await acc.request_phone_code(phone)
        sessions_hashes[session_id] = res.phone_code_hash
        return {"status": "success", "phone_code_hash": res.phone_code_hash}
    except NETWORK_ERRORS as e:
        logger.error(f"Network error sending code to {phone} ({session_id}): {type(e).__name__} - {e}")
        raise HTTPException(status_code=503, detail="FAILED_TO_CONNECT")
    except Exception as e:
        logger.error(f"Failed to send code to {phone} ({session_id}): {type(e).__name__} - {e}")
        raise HTTPException(status_code=400, detail="FAILED_TO_SEND_CODE")

@app.post("/api/auth/send_code")
async def send_code(req: PhoneRequest):
    # Precise check: what is the current state of this session?
    if req.session_id in accounts:
        acc_existing = accounts[req.session_id]
        status = await acc_existing.check_status()

        if status == "CONNECTED":
            raise HTTPException(status_code=400, detail="ALREADY_CONNECTED")

        elif status == "STOPPED":
            # File exists but session is not running — probe real health before restarting
            probe = await acc_existing.probe_session()
            if probe == "CONNECTED":
                # Session is healthy — just restart monitoring and resend code
                logger.info(f"Resuming stopped session {req.session_id}.")
                await acc_existing.start_monitoring()
                return await _do_request_code(acc_existing, req.phone, req.session_id)
            elif probe == "NO_NETWORK":
                raise HTTPException(status_code=503, detail="SESSION_NO_NETWORK")
            elif probe == "DEAD":
                # DEAD or NOT_AUTHORIZED — clean up and fall through to a fresh login
                logger.warning(f"Stopped session {req.session_id} is dead (probe={probe}). Cleaning up.")
                await acc_existing.logout()

        elif status == "NO_NETWORK":
            # Session is running but can't reach Telegram right now
            raise HTTPException(status_code=503, detail="SESSION_NO_NETWORK")

        elif status == "FILE_NOT_FOUND":
            # Object is in memory but file was deleted — purge the ghost
            logger.warning(f"Ghost session {req.session_id} (no file). Removing from memory.")
            accounts.pop(req.session_id, None)
            sessions_hashes.pop(req.session_id, None)
            # Fall through to create a fresh session below

        elif status in ("DEAD", "NOT_AUTHORIZED"):
            logger.warning(f"Session {req.session_id} status={status}. Cleaning up.")
            await acc_existing.logout()
            # Fall through to create a new session below

        else:  # UNKNOWN_ERROR
            logger.error(f"Unexpected status '{status}' for session {req.session_id}. Cleaning up.")
            await acc_existing.logout()

    def _on_death(sid):
        accounts.pop(sid, None)
        sessions_hashes.pop(sid, None)

    acc = Account(req.session_id, API_ID, API_HASH, on_death=_on_death)
    accounts[req.session_id] = acc
    return await _do_request_code(acc, req.phone, req.session_id)

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    acc = accounts.get(req.session_id)
    phone_hash = sessions_hashes.get(req.session_id)
    if not acc or not phone_hash:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    try:
        await acc.client.start(phone=req.phone, code=req.code, password=req.password, phone_code_hash=phone_hash)
        sessions_hashes.pop(req.session_id, None)  # Hash consumed — no longer needed
        await acc.start_monitoring()
        logger.info(f"Account {req.session_id} is connected.")
        return {"status": "success", "id": req.session_id}
    except SessionPasswordNeededError:
        raise HTTPException(status_code=401, detail="PASSWORD_NEEDED")
    except PasswordHashInvalidError:
        raise HTTPException(status_code=400, detail="PASSWORD_INVALID")
    except PhoneCodeInvalidError:
        raise HTTPException(status_code=400, detail="PHONE_CODE_INVALID")
    except PhoneCodeExpiredError:
        # Code expired — complete failure of this session
        await acc.logout()  # Handles stopping, removing from accounts and file deletion
        raise HTTPException(status_code=400, detail="PHONE_CODE_EXPIRED")
    except PasswordHashInvalidError:
        raise HTTPException(status_code=400, detail="PASSWORD_INVALID")
    except Exception as e:
        logger.error(f"LOGIN FAILED for {req.session_id}: {type(e).__name__} - {e}")
        # Fatal/unexpected error — cleanup to avoid "ghost" sessions
        await acc.logout()
        raise HTTPException(status_code=400, detail=f"AUTH_ERROR_{type(e).__name__}")

@app.get("/api/sessions/{session_id}/status")
async def get_status(session_id: str):
    """Check the status of an already running userbot."""
    acc = accounts.get(session_id)
    if not acc:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    if not acc.is_running:
        return {"status": "stopped"}
    if not acc.client.is_connected():
        return {"status": "offline_network_error"}
    return {"status": "online"}

@app.get("/api/sessions")
async def list_sessions():
    """List all accounts and clean up those that died."""
    # Build a list of truly dead sessions to remove them from memory
    dead_ids = []
    for sid, acc in accounts.items():
        if not acc.is_running:
            dead_ids.append(sid)
            
    for sid in dead_ids:
        accounts.pop(sid, None)
        
    return {
        "sessions": [
            {
                "session_id": sid, 
                "is_running": a.is_running, 
                "is_connected": a.client.is_connected()
            } for sid, a in accounts.items()
        ]
    }

@app.post("/api/sessions/{session_id}/action/send_message")
async def send_message_task(session_id: str, req: SendMessageRequest):
    from telethon import errors
    acc = accounts.get(session_id)
    
    # 1. Check existence
    if not acc:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    
    # 2. Check network (VPN/Internet)
    if not acc.client.is_connected():
        raise HTTPException(status_code=503, detail="NETWORK_ERROR")

    # 3. Check authorization (is account alive)
    try:
        if not await acc.client.is_user_authorized():
            raise HTTPException(status_code=401, detail="AUTH_REVOKED")
    except:
        raise HTTPException(status_code=503, detail="NETWORK_ERROR")

    try:
        await acc.client.send_message(req.target, req.text)
        return {"status": "success"}
    except errors.FloodWaitError as e:
        raise HTTPException(status_code=429, detail=f"FloodWait: {e.seconds}")
    except Exception as e:
        logger.error(f"Failed to send message: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/info")
async def session_info(session_id: str):
    """Request detailed account data for a specific userbot."""
    acc = accounts.get(session_id)
    
    # 1. Check existence
    if not acc:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    
    # 2. Check network
    if not acc.client.is_connected():
        raise HTTPException(status_code=503, detail="NETWORK_ERROR")

    # 3. Check authorization
    try:
        if not await acc.client.is_user_authorized():
            raise HTTPException(status_code=401, detail="AUTH_REVOKED")
        
        me = await acc.client.get_me()
        if not me:
            # If get_me returns None, authorization is lost. 
            # We don't trigger death cleanup here anymore, let the monitoring loop handle it.
            raise HTTPException(status_code=401, detail="AUTH_REVOKED")

        authorizations = await acc.client(functions.account.GetAuthorizationsRequest())
        auth_list = []
        for auth in authorizations.authorizations:
            auth_list.append({
                "device_model": auth.device_model,
                "platform": auth.platform,
                "system_version": auth.system_version,
                "app_name": auth.app_name,
                "app_version": auth.app_version,
                "date_active": auth.date_active.strftime("%Y-%m-%d %H:%M:%S") if auth.date_active else "unknown",
                "ip": auth.ip,
                "country": auth.country,
                "official_app": auth.official_app, 
                "current": auth.current
            })

        return {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "phone": me.phone,
            "sessions": auth_list,
        }
    except Exception as e:
        logger.error(f"Failed to get info for session {session_id}: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """Stop the userbot via API."""
    acc = accounts.get(session_id)
    if not acc:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    await acc.stop()
    del accounts[session_id]
    return {"status": "success"}

@app.post("/api/sessions/{session_id}/logout")
async def logout_session(session_id: str):
    """Logout from account and delete the session."""
    acc = accounts.get(session_id)
    if not acc:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")
    await acc.logout()
    del accounts[session_id]
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    os.makedirs(BASE_DIR / "sessions", exist_ok=True)
    from shared.config import MANAGER_PORT, HIDE_API_LOGS
    
    # Apply log level directly to uvicorn to catch startup logs
    log_level = "warning" if HIDE_API_LOGS else "info"
    uvicorn.run(app, host="127.0.0.1", port=int(MANAGER_PORT), log_level=log_level)

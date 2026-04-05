import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ISOLATION: Locate the MVP root for 'shared' imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Import from the root
from manager_server.core.account import Account
from shared.config import API_ID, API_HASH

app = FastAPI()

# In-memory session database (dictionary of Accounts)
accounts = {}

class PhoneRequest(BaseModel):
    phone: str

class LoginRequest(BaseModel):
    phone: str
    code: str
    phone_code_hash: str
    password: str = None

@app.post("/api/auth/send_code")
async def send_code(req: PhoneRequest):
    """Step 1. Request login code."""
    acc = Account(req.phone, API_ID, API_HASH)
    accounts[req.phone] = acc
    try:
        phone_code_hash = await acc.client.api_send_code(req.phone)
        return {"status": "success", "phone_code_hash": phone_code_hash}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """Step 2. Login code entry."""
    acc = accounts.get(req.phone)
    if not acc:
        raise HTTPException(status_code=404, detail="Session not initialized.")
    try:
        me = await acc.client.api_login(req.phone, req.code, req.phone_code_hash, req.password)
        # If authorization is successful, start background monitoring
        await acc.start_monitoring()
        return {"status": "success", "id": me.id, "username": me.username}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/sessions/{phone}/status")
async def get_status(phone: str):
    """Check the status of an already running userbot."""
    acc = accounts.get(phone)
    if not acc or not acc.is_running:
        return {"status": "offline"}
    return {"status": "online"}

@app.post("/api/sessions/{phone}/stop")
async def stop_session(phone: str):
    """Stop the userbot via API."""
    acc = accounts.get(phone)
    if acc:
        await acc.stop()
        del accounts[phone]
        return {"status": "success"}
    return {"status": "not_found"}

if __name__ == "__main__":
    import uvicorn
    # Create a folder for Telethon sessions in the MVP root
    os.makedirs(BASE_DIR / "sessions", exist_ok=True)
    from shared.config import MANAGER_PORT
    uvicorn.run(app, host="127.0.0.1", port=int(MANAGER_PORT))

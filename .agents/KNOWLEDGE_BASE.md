# 🧠 Knowledge Base: UserbotFramework Distributed Architecture

This project is a high-performance, resilient framework for managing Telegram userbots via a centralized API (Manager) and a Telegram interface (Bot).

---

## 🏗 System Architecture
The system is divided into two independent services for process isolation and scalability:

1. **Manager Server (FastAPI)**:
   - **Role**: Core session owner. Manages Telethon instances, health monitoring, and REST API.
   - **Port**: Default 8000.
   - **Persistence**: Sessions are stored as `.session` (SQLite) files in the `sessions/` directory.

2. **Bot Server (Aiogram)**:
   - **Role**: Management UI. Receives user commands and proxies them to the Manager.
   - **Port**: Default 8001 (for internal webhooks from Manager).
   - **Features**: Includes a Unicode-based obfuscation engine for message protection.

3. **Orchestrator (`main.py`)**:
   - Uses the `subprocess` API to launch both services.
   - Essential for Windows compatibility to avoid socket inheritance issues between processes.

---

## 🔑 Core Logic & Systems

### 1. Advanced Session Lifecycle (OOP)
Implemented via the `Account` class in `manager_server/core/account.py`:
- **Encapsulation**: All Telethon client interactions (connect, auth check, logout) are hidden inside the class.
- **Proactive Monitoring**: A background loop (`_monitoring_loop`) checks session health every 10 seconds.
- **Health Check Loop**: Each session makes a fast `is_user_authorized()` request every 10 seconds. If the network drops, the system goes into wait mode (warning) but does not delete data.
- **Fail-Safe Warm-up**: The warm-up task is protected against network failures. If the connection is lost during imitation requests, the task aborts gracefully to prevent infinite loops.
- **Session Existence Check**: New endpoint `GET /api/auth/{session_id}/exists` allows checking if a session exists in memory or on disk without starting it.
- **Auto-Cleanup**: If a session is banned or revoked, the system automatically calls `logout()`, deleting local files and notifying the Bot via Webhook.
- **Probe Logic**: Uses `probe_session()` to verify health of stopped sessions before allowing a restart.

### 2. Smart Initialization (Warm-up)
New sessions undergo a "warm-up" routine to ensure stable connection and health:
- Triggers standard requests like `GetConfig`, `GetAppConfig`, and `GetPrivacy`.
- Prevents instant session flagging by following standard MTProto initialization patterns.

### 3. Centralized Configuration (`shared/config.py`)
Single source of truth for the entire system:
- **Networking**: Support for separate hosts (`MANAGER_HOST`, `BOT_HOST`) allows deploying services on different servers.
- **Session Identification**: 
    - `USE_UNIQUE_DEVICES`: If True, each session gets a unique (but stable) device profile (mimicry mode).
    - `STATIC_DEVICE_CONFIG`: If False, all sessions identify as "Userbot Framework" for transparency.
- **Credential Isolation**: Only secrets (`API_ID`, `API_HASH`, `BOT_TOKEN`) stay in `.env`.
- **Log Control**: `HIDE_API_LOGS` flag to suppress frequent HTTP success logs for cleaner console output.

### 4. Anti-Ban Foundation
The `bot_server/obfuscator.py` module implements Unicode-based text transformation:
- Replaces standard Latin/Cyrillic characters with visual homoglyphs.
- Prevents automated scanners from reading message content while remaining legible to humans.

---

## 📜 Logging & Observability
Standardized via `shared/logging_utils.py`:
- **Module Tags**: `[MANAGER]`, `[BOT]`, `[ACCOUNT]`, `[SYSTEM_ENGINE]`.
- **Error Transparency**: All exceptions are logged with class names and detailed traces.

---

## 🛡️ Security & UX
- **ID-Based Storage**: Sessions are named by Telegram ID, not phone numbers, ensuring consistency across login attempts.
- **2FA Support**: Full flow for sessions protected by Two-Factor Authentication.
- **Precise Error Feedback**: Standardized error codes (e.g., `PHONE_CODE_EXPIRED`, `SESSION_REVOKED`) ensure the Bot can provide helpful instructions to the user.

---

## 🚀 Potential Paths for Scaling
1. **User Ownership & Isolation**: Upon further development on top of this framework, clarify if commands should be strictly restricted to the session owner's ID (e.g., preventing users from manipulating other users' sessions).
2. **Session Wait-Time Management**: Implement a 10-minute timer for /login in the Bot server. 
    - If the code is not entered within 10 minutes, notify the user that the wait time has expired and the code must be requested again. 
    - Clear the Bot's FSM state and notify the Manager to purge the session (calling `_on_death`). 
    - Cancel the timer if the code is successfully entered.
3. **Database Integration**: Replace the in-memory `accounts` dictionary with Redis/PostgreSQL for persistent metadata storage.
4. **Proxy Management**: Extend `Account` to support individual proxies per session for large-scale operations.
5. **Advanced Obfuscation**: Implement dynamic grammar-based or AI-driven text rewriting.

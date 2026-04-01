# 🧠 Knowledge Base: Distributed Userbot API MVP

This project represents a fault-tolerant architecture for managing Telegram userbots via a centralized API manager and a Telegram bot (interface).

---

## 🏗 System Architecture
The system is divided into two independent processes to provide network resource isolation (especially critical on Windows):

1. **Manager Server (Port 8000)**: Core of the system. Stores Telethon sessions, manages their lifecycle, and provides a REST API.
2. **Bot Server (Port 8001)**: Management interface. Communicates with the manager via HTTP and accepts webhooks about session deaths.
3. **Main Launcher (`main.py`)**: Orchestrator, launched via `subprocess`. **Important: do not use multiprocessing on Windows** due to socket conflicts.

---

## 🔑 Key Features and Logic

### 1. ID-Oriented Management
All sessions and files are named by **Telegram User ID** (`id.session`). The phone number is only used once during login. This ensures reliability when changing numbers or logging in repeatedly.

### 2. Zero-Wait Startup (Instant Launch)
The Manager and Bot bind ports instantly. Connecting sessions to Telegram happens in the background via `lifespan` and `asyncio.create_task`. The server is always "online", even if Telegram is unavailable.

### 3. Network Resilience (Windows Hardened)
Due to Windows socket and VPN specifics:
* **Timeouts**: The entire `client.connect()` process is wrapped in `asyncio.wait_for`.
* **Error Isolation**: Specific `IncompleteReadError` (0 bytes), `TimeoutError`, and `ConnectionError` are intercepted.
* **Silencer (Exception Handler)**: The Manager has a global asyncio exception interceptor so that system logs `Future exception was never retrieved` from Telethon don't spam the console.
* **Health Check Loop**: Each session makes a fast `is_user_authorized()` request every 10 seconds. If the network drops, the system goes into wait mode (warning) but does not delete data.

### 4. Security
* **Contact Validation**: The bot only accepts the phone number via the "Share Contact" button. The server verifies: `contact.user_id == from_user.id`. Connecting someone else's account is impossible.
* **Logout**: The `/logout` command calls `client.log_out()`, completely deleting the authorization keys on the Telegram servers and the file on disk.

---

## 📜 Logging Standards
Uses `shared.logging_utils`. Each message has a module tag:
* `[MANAGER]` — General API events.
* `[ACCOUNT]` — Detailed logs of a specific userbot session.
* `[BOT]` — Interface logs.
* All errors are logged with the class name: `{type(e).__name__} - {e}`.

---

## 🛠 Technical Stack
* **Python 3.12+**
* **FastAPI** (Manager API)
* **Aiogram 3.x** (Bot GUI)
* **Telethon** (Userbot Engine)
* **Windows Subprocess API** (Process Isolation)

---

## 🐋 Deployment & Infrastructure
The system is officially containerized for production reliability:
*   **Docker (python-slim)**: Uses a minimal Debian-based image to reduce attack surface and build time.
*   **Layer Caching**: `requirements.txt` is installed BEFORE copying the source code to optimize rebuilds.
*   **Volume Persistence**: The `/app/sessions` directory is mapped to the host's `./sessions` folder to ensure Telegram sessions survive container restarts.
*   **Process Management**: `main.py` acts as the PID 1 equivalent inside the container, orchestrating the Manager and Bot via `subprocess`.

---

## 📦 Dependency Management
*   **Pinned Versions**: All core libraries (`Telethon`, `FastAPI`, `Aiogram`) are pinned to exact versions in `requirements.txt` to prevent breaking changes from upstream updates.
*   **Compatibility**: Optimized for Python 3.11+ (latest tested stable environment).

---

## 📜 Documentation Standards
*   **Dual README**: Maintenance of `README.md` (English, Primary) and `README.ru.md` (Russian, Secondary) with cross-links.
*   **Security Disclaimer**: Mandatory notice about 2FA necessity (setup BEFORE login) and developer non-liability.

---

## 🚀 Future Work
1. **Proxies**: To scale, you need to add a `proxy` field to the `Account` class and pass it during `connect()`.
2. **Database**: Everything is currently in RAM in the `accounts` dictionary. For production, it's worth adding SQLite/PostgreSQL to store metadata (but leave the sockets themselves in memory).

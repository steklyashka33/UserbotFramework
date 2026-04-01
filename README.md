# 🚀 CoreUserbot: Distributed Telegram Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](https://www.docker.com/)

[🇷🇺 Russian Version](README.ru.md)

**Scalable & Distributed Telegram Userbot Core with Bot-driven management.**

---

**CoreUserbot** is a high-performance, modular framework for building distributed Telegram userbots. This project is built for developers who need a robust foundation for multi-account management with process isolation and high resilience.

### ✨ Key Features
*   ⚙️ **Distributed Architecture:** Independent Manager (FastAPI) and Bot (Aiogram) servers.
*   🛡️ **Process Isolation:** Uses `subprocess` API to avoid socket conflicts, specifically optimized for Windows.
*   🌐 **Resilience:** Automatic health checks and re-connection logic for unstable networks.
*   🚀 **Zero-Wait Startup:** Instant server binding with background session initialization.
*   🐋 **Dockerized:** Ready for production with one command.

---

### 📦 Installation

#### Option 1: Docker (Recommended)
1. **Clone & Enter:**
   ```bash
   git clone https://github.com/your-username/CoreUserbot.git
   cd CoreUserbot
   ```
2. **Setup Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your Telegram API ID, Hash, and Bot Token
   ```
3. **Run:**
   ```bash
   docker-compose up -d --build
   ```

#### Option 2: Local Setup (Quick Start)
1. **Setup Environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Configuration:**
   Copy `.env.example` to `.env` and fill it in.
3. **Launch:**
   ```bash
   python main.py
   ```

---

### 📂 Project Structure
```text
.
├── bot_server/          # Aiogram-based management interface
├── manager_server/      # FastAPI-based session & API core
├── shared/              # Common utilities, config, and logging
├── sessions/            # Storage for .session files (Telethon)
├── main.py              # Orchestration entry point
└── docker-compose.yaml  # Deployment configuration
```

---

### ⚙️ Configuration (.env)
| Variable | Purpose |
| :--- | :--- |
| `API_ID` | Telegram API ID from my.telegram.org |
| `API_HASH` | Telegram API Hash from my.telegram.org |
| `API_TOKEN` | Bot API Token from @BotFather |
| `MANAGER_API_PORT` | Optional: Port for Manager (default: 8000) |
| `BOT_WEBHOOK_PORT`| Optional: Port for Webhooks (default: 8001) |

---

### ⚠️ Disclaimer & Security
**Important Notice:**
1.  **Responsibility:** The author is not responsible for any misuse, account bans, or data loss. Use this software at your own risk.
2.  **Account Safety:** Telegram security systems may terminate all account sessions if suspicious activity is detected.
3.  **2FA Recommendation:** It is highly recommended to enable **Two-Factor Authentication (2FA)** **BEFORE** linking your account to any userbot system to ensure maximum security.

---

## 📄 License
Distributed under the **Apache License 2.0**. See `LICENSE` for more information.

---
*Created with ❤️ for the Telegram developer community.*

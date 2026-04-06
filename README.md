# 🚀 CoreUserbot: Distributed Telegram Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](https://www.docker.com/)

[🇷🇺 Russian Version](README.ru.md)

**Scalable & Distributed Telegram Userbot Framework with Smart Session Management.**

---

**CoreUserbot** is a production-ready, modular framework for building distributed Telegram userbots. It provides a robust foundation for multi-account management with process isolation, high resilience, and anti-ban protection.

### ✨ Key Features
*   ⚙️ **Distributed Architecture:** Independent Manager (FastAPI) and Bot (Aiogram) servers.
*   🛡️ **Smart Lifecycle Management:** OOP-based `Account` class with proactive health checks.
*   🧠 **Human-like Behavior:** Built-in "warm-up" routine to mimic real app interaction patterns.
*   🎭 **Anti-Ban Engine:** Unicode-based message obfuscator to bypass automated detection.
*   🌐 **Multi-Host Ready:** Centralized networking supporting separate servers for Bot and Manager.
*   🚀 **Zero-Wait Startup:** Instant server binding with background session indexing.
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
   Copy `.env.example` to `.env` and fill it in. Adjust networking in `shared/config.py` if needed.
3. **Launch:**
   ```bash
   python main.py
   ```

---

### 📂 Project Structure
```text
.
├── bot_server/          # AIogram-based management interface
│   ├── obfuscator.py    # Unicode-based text protection engine
│   └── handlers.py      # Unified API communication & UI logic
├── manager_server/      # FastAPI-based session & API core
│   └── core/            # Encapsulated Account (Telethon) & Client logic
├── shared/              # Centralized Config, Logging, and Utilities
├── sessions/            # Storage for .session files (Telethon)
├── main.py              # Orchestration entry point
└── docker-compose.yaml  # Deployment configuration
```

---

### ⚙️ Configuration
The project uses a hybrid configuration system for maximum flexibility:

1.  **.env**: Store secret credentials (`API_ID`, `API_HASH`, `API_TOKEN`).
2.  **shared/config.py**: Centralized source of truth for all other settings:
    *   `MANAGER_HOST` / `BOT_HOST`: IP addresses for multi-server deployment.
    *   `MANAGER_PORT` / `BOT_PORT`: Communication ports.
    *   `USE_STABLE_RANDOM_DEVICE`: Toggle unique-per-session vs. static device fingerprint.
    *   `STATIC_DEVICE_CONFIG`: Fixed device profile used when randomization is disabled.
    *   `HIDE_API_LOGS`: Clean terminal output toggle.

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

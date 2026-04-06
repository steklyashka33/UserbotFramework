# 🚀 CoreUserbot

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](https://www.docker.com/)

[🇷🇺 Russian Version](README.ru.md)

---

**CoreUserbot** is a scalable framework for launching distributed Telegram userbots based on **Telethon**. The project provides a reliable foundation for smart session management, process isolation, high resilience, and anti-ban protection.

### ✨ Key Features
*   ⚙️ **Telethon Userbot Cluster:** Simultaneous support and launch of multiple Telethon-based userbots in real-time.
*   🛰️ **Distributed Orchestration:** Manager (FastAPI) handles the API and session lifecycle, while the Bot (Aiogram) provides a friendly management UI.
*   🛡️ **Smart Lifecycle:** OOP-based `Account` class with proactive session health monitoring.
*   🧠 **Human-like Behavior:** Built-in "warm-up" routine to mimic real Telegram app activity.
*   🎭 **Anti-Ban Protection:** Unicode-based message obfuscator engine to bypass automated detection systems.
*   🌐 **Multi-Host Ready:** Centralized networking allowing Bot and Manager to run on different servers.
*   🚀 **Instant Start:** API ports bind instantly without waiting for session authorization (background Zero-Wait Indexing).
*   🐋 **Docker-ready:** Ready for production deployment with a single command.

---

### 🔗 Component Interaction
To understand how the system works, imagine the following chain:
1.  **You** send a command to the control bot (**Bot Server / Aiogram interface**).
2.  **The Bot** forwards your command via internal REST API to the **Manager Server**.
3.  **Manager Server** (FastAPI) finds the active session and commands the specific **Telethon Userbot**.
4.  **The Userbot** performs the action directly via the MTProto protocol (acting as a real Telegram client).

---

### 📦 Installation

#### Option 1: Docker (Recommended)
1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/CoreUserbot.git
   cd CoreUserbot
   ```
2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env and provide your API_ID, API_HASH, and Bot Token
   ```
3. **Launch:**
   ```bash
   docker-compose up -d --build
   ```

#### Option 2: Local Setup
1. **Prepare Environment:**
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
├── .agents/             # AI instructions, knowledge base and skills
├── bot_server/          # Aiogram-based management interface
│   ├── obfuscator.py    # Unicode text protection engine
│   └── handlers.py      # Unified API communication logic
├── manager_server/      # FastAPI-based session management core
│   └── core/            # Encapsulated Account (Telethon) logic
├── shared/              # Global config, logger, and utilities
├── sessions/            # Storage for .session files
├── main.py              # Entry point and process orchestrator
└── docker-compose.yaml  # Deployment configuration
```

---

### ⚙️ Configuration
The project uses a hybrid configuration system for maximum flexibility:

1.  **.env**: Storage for secret keys (`API_ID`, `API_HASH`, `API_TOKEN`).
2.  **shared/config.py**: Single source of truth for all other parameters:
    *   `MANAGER_HOST` / `BOT_HOST`: IP addresses for multi-server deployment.
    *   `MANAGER_PORT` / `BOT_PORT`: Communication ports.
    *   `USE_UNIQUE_DEVICES`: Toggle between unique (but stable) and static device fingerprints.
    *   `STATIC_DEVICE_CONFIG`: Fixed device profile used when randomization is disabled.
    *   `HIDE_API_LOGS`: Clean terminal mode (hides frequent HTTP logs).

---

### ⚠️ Disclaimer & Security
**Important Notice:**
1.  **Responsibility:** The author is not responsible for any misuse, account bans, or data loss. Use at your own risk.
2.  **Account Safety:** Telegram security systems may terminate sessions if suspicious activity is detected.
3.  **2FA Recommendation:** It is highly recommended to enable **Two-Factor Authentication (2FA)** **BEFORE** connecting an account to any userbot system.

---

## 📄 License
Distributed under the **Apache License 2.0**. See the `LICENSE` file for details.

---
*Created with ❤️ for the Telegram developer community.*

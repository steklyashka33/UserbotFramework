# 🚀 CoreUserbot: Distributed Telegram Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-green.svg)](https://www.docker.com/)

[🇺🇸 English Version](README.md)

**Scalable & Distributed Telegram Userbot Core with Bot-driven management.**

---

**CoreUserbot** — это высокопроизводительный, модульный каркас для создания распределенных Telegram-юзерботов. Проект создан для разработчиков, которым нужна надежная база для управления множеством аккаунтов с изоляцией процессов и высокой устойчивостью к сбоям.

### ✨ Ключевые возможности
*   ⚙️ **Распределенная архитектура:** Независимые сервера Менеджера (FastAPI) и Бота (Aiogram).
*   🛡️ **Изоляция процессов:** Использование `subprocess` для исключения конфликтов сокетов, оптимизировано для работы под Windows.
*   🌐 **Отказоустойчивость:** Автоматические проверки здоровья (health checks) и логика переподключения.
*   🚀 **Мгновенный запуск:** Быстрый запуск API с фоновой инициализацией сессий Telegram.
*   🐋 **Docker-ready:** Разворачивание всей инфраструктуры одной командой.

---

### 📦 Установка

#### Вариант 1: Docker (Рекомендуется)
1. **Клонируйте и перейдите в папку:**
   ```bash
   git clone https://github.com/ваш-юзернейм/CoreUserbot.git
   cd CoreUserbot
   ```
2. **Настройка окружения:**
   ```bash
   cp .env.example .env
   # Отредактируйте .env, указав API_ID, API_HASH и токен бота
   ```
3. **Запуск:**
   ```bash
   docker-compose up -d --build
   ```

#### Вариант 2: Локальный запуск (Быстрый старт)
1. **Подготовка окружения:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # На Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Конфигурация:**
   Скопируйте `.env.example` в `.env` и заполните данные.
3. **Запуск:**
   ```bash
   python main.py
   ```

---

### 📂 Структура проекта
```text
.
├── bot_server/          # Интерфейс управления на Aiogram
├── manager_server/      # Ядро (сессии и API) на FastAPI
├── shared/              # Утилиты, конфиг и логирование
├── sessions/            # Хранилище .session файлов (Telethon)
├── main.py              # Точка входа (Оркестратор)
└── docker-compose.yaml  # Конфигурация деплоя
```

---

### ⚙️ Конфигурация (.env)
| Переменная | Описание |
| :--- | :--- |
| `API_ID` | Ваш Telegram API ID с my.telegram.org |
| `API_HASH` | Ваш Telegram API Hash с my.telegram.org |
| `API_TOKEN` | Токен бота от @BotFather |
| `MANAGER_API_PORT` | Опционально: Порт Менеджера (дефолт: 8000) |
| `BOT_WEBHOOK_PORT`| Опционально: Порт для вебхуков (дефолт: 8001) |

---

### ⚠️ Ответственность и Безопасность
**Важное примечание:**
1.  **Отказ от ответственности:** Автор не несет ответственности за любое использование проекта, бан аккаунтов или потерю данных. Вы используете ПО на свой страх и риск.
2.  **Безопасность аккаунта:** Системы безопасности Telegram могут принудительно завершить все сессии аккаунта при обнаружении подозрительной активности.
3.  **Рекомендация по 2FA:** Настоятельно рекомендуется включить **двухфакторную аутентификацию (2FA)** **ПЕРЕД** подключением вашего аккаунта к любой системе юзерботов для обеспечения максимальной безопасности.

---

## 📄 Лицензия
Распространяется под лицензией **Apache License 2.0**. См. `LICENSE` для подробностей.

---
*Создано с ❤️ для сообщества разработчиков Telegram.*

# ApexNotification — Telegram LeadForm Hub

Production-ready Telegram CRM-бот для управления клиентами, офферами, лидформами, источниками трафика, лидами, ролями и пикселями.

## Возможности

- **Мультитенант CRM** — Клиенты → Офферы → Лидформы
- **Динамические лидформы** — текст, телефон, число, дата, выбор
- **Отслеживание источников** — уникальные deep-link на каждую форму+источник
- **Роли пользователей** — super_admin / client_admin / client_viewer / manager
- **Мастер создания оффера** — 7-шаговый пошаговый wizard
- **Пиксели/события** — Meta, Google, TikTok, Telegram tracking
- **Экспорт** — CSV (UTF-8-BOM) и XLSX
- **Дублирование** — автоматическая защита от повторных заявок
- **Статистика** — сегодня, за период, по источникам, конверсии

## Стек

| Компонент | Версия |
|-----------|--------|
| Python | 3.10+ |
| aiogram | 3.7.0 |
| SQLAlchemy (async) | 2.0.30 |
| aiosqlite | 0.20.0 |
| Alembic | 1.13.1 |
| openpyxl | 3.1.2 |
| pydantic-settings | 2.3.3 |

---

## Быстрый старт (Windows)

### Вариант 1 — установка на новый сервер одной командой

```powershell
# 1. Создать папку
mkdir D:\bots\ApexNotification
cd D:\bots\ApexNotification

# 2. Скачать и запустить скрипт установки
powershell -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/averysultan3-creator/ApexNotification/main/setup_server.ps1' -OutFile setup_server.ps1; .\setup_server.ps1"
```

Скрипт сам: клонирует репозиторий, создаст `.venv`, установит зависимости, создаст `.env`.

### Вариант 2 — если уже склонировали вручную

```bat
install_windows.bat
```

---

## Настройка .env

После установки открой `.env` и заполни:

```env
BOT_TOKEN=8656058191:AAXXX...       # токен от @BotFather
ADMIN_IDS=123456789                  # твой числовой Telegram ID (от @userinfobot)
BOT_USERNAME=your_bot_username       # @username бота без @
DATABASE_URL=sqlite+aiosqlite:///./leadform_hub.db
LOG_LEVEL=INFO
PAGE_SIZE=10
```

---

## Запуск

```bat
run_windows.bat
```

---

## Обновление с GitHub

```bat
update_windows.bat
```

Скрипт: `git pull` → обновит зависимости → применит миграции → запустит тесты → сообщит о статусе.

---

## Ручные команды

### Создать виртуальное окружение и установить зависимости

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Применить миграции базы данных

```bat
.venv\Scripts\activate
python -m alembic upgrade head
```

Если `alembic` не найден как команда — используй:

```bat
python -m alembic upgrade head
```

### Запустить тесты

```bat
.venv\Scripts\activate
python -m pytest tests/ -v
```

### Проверить синтаксис всех файлов

```powershell
Get-ChildItem -Recurse -Filter "*.py" | Where-Object { $_.FullName -notmatch "__pycache__" } | ForEach-Object { python -m py_compile $_.FullName }
```

### Проверить импорт БД

```bat
python -c "from database import init_db; print('DB import OK')"
```

---

## Структура проекта

```
ApexNotification/
├── alembic/               # Миграции БД
│   └── versions/          # Файлы миграций (001–004)
├── handlers/
│   ├── admin/             # Хендлеры для super_admin
│   ├── client/            # Кабинет клиента
│   ├── manager/           # Кабинет менеджера
│   ├── shared/            # /start — маршрутизация по ролям
│   └── user/              # Пользовательский flow (лидформа)
├── keyboards/             # Клавиатуры aiogram
├── middlewares/           # DB, RoleMiddleware, Auth
├── models/                # SQLAlchemy ORM модели
├── services/              # Бизнес-логика
├── states/                # FSM состояния (wizard и др.)
├── tests/                 # pytest тесты
├── utils/                 # Утилиты (пагинация, валидация)
├── main.py                # Точка входа
├── config.py              # Настройки из .env
├── database.py            # Инициализация БД
├── requirements.txt
├── .env.example           # Шаблон настроек
├── install_windows.bat    # Первичная установка
├── run_windows.bat        # Запуск бота
├── update_windows.bat     # Обновление с GitHub
└── setup_server.ps1       # Установка на новый сервер
```

---

## Deployment на новый сервер — пошагово

**Шаг 1.** Убедись, что установлены [Python 3.10+](https://python.org) и [Git](https://git-scm.com/download/win).

**Шаг 2.** Создай папку и запусти скрипт:

```powershell
mkdir D:\bots
cd D:\bots\ApexNotification
powershell -ExecutionPolicy Bypass -File setup_server.ps1
```

Или скачай и запусти за одну команду:

```powershell
mkdir D:\bots\ApexNotification; cd D:\bots\ApexNotification; powershell -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/averysultan3-creator/ApexNotification/main/setup_server.ps1' -OutFile setup_server.ps1; .\setup_server.ps1"
```

**Шаг 3.** Открой `.env` и заполни BOT_TOKEN, ADMIN_IDS, BOT_USERNAME.

**Шаг 4.** Запусти бот:

```bat
run_windows.bat
```

**Шаг 5.** Для обновлений в будущем:

```bat
update_windows.bat
```

---

## Безопасность

- `.env` исключён из git (`.gitignore`)
- База данных `.db` исключена из git
- Все реальные токены — только в `.env` на сервере
- Не коммить `.env` в репозиторий


Edit `.env`:

```dotenv
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
DATABASE_URL=sqlite+aiosqlite:///./leadform_hub.db
BOT_USERNAME=your_bot_username   # without @
PAGE_SIZE=8
LOG_LEVEL=INFO
```

- `BOT_TOKEN` — get from [@BotFather](https://t.me/BotFather)
- `ADMIN_IDS` — comma-separated Telegram user IDs with admin access
- `BOT_USERNAME` — your bot's username (used to build referral deep links)

### 3. Run the bot

```bash
python main.py
```

The database is created automatically on first run via `init_db()`.

> **Note:** `init_db()` in `database.py` calls SQLAlchemy's `create_all` for local dev convenience. In production, manage schema via Alembic only.

### 4. (Optional) Use Alembic for migrations

> Alembic CLI may not be on PATH. Use it as:
> - **Linux/macOS:** `alembic upgrade head` (if installed via pip in venv)
> - **Windows:** `python -m alembic upgrade head` may fail due to packaging. Use the full path: `C:\Python310\Scripts\alembic.exe upgrade head` or install in a venv and activate it first.

```bash
# If alembic is on PATH:
alembic upgrade head

# If not (common on Windows without venv):
python -c "from alembic.config import main; main(argv=['upgrade', 'head'])"
```

For subsequent schema changes:

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Project Structure

```
ApexNotification/
├── main.py                    # Entry point
├── config.py                  # Settings from .env
├── database.py                # SQLAlchemy engine + session + init
├── requirements.txt
├── .env.example
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py
│
├── models/
│   ├── __init__.py
│   ├── client.py
│   ├── offer.py
│   ├── lead_form.py
│   ├── lead_form_question.py
│   ├── referral_source.py
│   └── lead.py
│
├── services/
│   ├── client_service.py
│   ├── offer_service.py
│   ├── form_service.py
│   ├── question_service.py
│   ├── referral_service.py
│   ├── lead_service.py
│   ├── stats_service.py
│   └── export_service.py
│
├── handlers/
│   ├── admin/
│   │   ├── menu.py
│   │   ├── clients.py
│   │   ├── offers.py
│   │   ├── leadforms.py
│   │   ├── questions.py
│   │   ├── referrals.py
│   │   ├── leads.py
│   │   ├── stats.py
│   │   └── exports.py
│   └── user/
│       └── flow.py            # User-facing form FSM
│
├── keyboards/
│   ├── admin_kb.py
│   └── user_kb.py
│
├── middlewares/
│   ├── auth.py                # AdminMiddleware
│   └── db.py                  # DatabaseMiddleware
│
├── states/
│   ├── admin_states.py
│   └── user_states.py
│
├── utils/
│   ├── pagination.py
│   ├── validators.py
│   ├── formatters.py
│   └── notifications.py
│
└── tests/
    ├── conftest.py
    ├── test_services.py
    └── test_utils.py
```

## Deep Link Format

Referral links follow this format:

```
https://t.me/{BOT_USERNAME}?start=lf_{form_id}_ref_{ref_code}
```

Example: `https://t.me/mybot?start=lf_3_ref_a1b2c3d4`

The bot automatically generates these links when you create a referral source. Copy them from the admin panel and distribute to traffic sources.

## Admin Panel Flow

```
/start (admin)
└── 📋 Clients
    └── [Create] → wizard: name → username → notes
    └── [View] → edit fields / toggle status / delete
        └── 📦 Offers
            └── [Create] → wizard: client → name → description → geo → language
            └── [View] → edit / toggle / delete
                └── 📝 Lead Forms
                    └── [Create] → client → offer → name → language → welcome → success
                    └── [View] → edit / toggle / delete
                        ├── ❓ Questions
                        │   └── [Add] → text → type → [options] → required?
                        │   └── [View] → edit text / move up-down / delete
                        └── 🔗 Ref Links
                            └── [Add] → name → source type → notes
                            └── [View] → toggle / delete / copy deep link

└── 📨 Leads
    └── Filter by client / offer / form / status / date
    └── [View] → change status / add note

└── 📊 Stats
    └── Global / per-client / per-offer / per-form / per-ref

└── 📤 Export
    └── CSV or XLSX, optional filters
```

## User Flow

1. User clicks a referral deep link
2. Bot shows welcome message
3. Bot asks questions one by one (with type validation)
4. On completion — success message + admin notification
5. Duplicate submissions are blocked silently

## Running Tests

```bash
pytest tests/ -v
```

Dependencies (`pytest`, `pytest-asyncio`) are included in `requirements.txt`.

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | ✅ | — | Telegram Bot API token |
| `ADMIN_IDS` | ✅ | — | Comma-separated Telegram user IDs |
| `DATABASE_URL` | ❌ | `sqlite+aiosqlite:///./leadform_hub.db` | SQLAlchemy async DB URL |
| `BOT_USERNAME` | ✅ | — | Bot username (no @) for deep links |
| `PAGE_SIZE` | ❌ | `8` | Items per page in list views |
| `LOG_LEVEL` | ❌ | `INFO` | Python logging level |

## Switching to PostgreSQL

Change `DATABASE_URL` in `.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/leadform_hub
```

Add `asyncpg` to requirements:

```
asyncpg==0.29.0
```

No code changes needed — SQLAlchemy abstracts the driver.

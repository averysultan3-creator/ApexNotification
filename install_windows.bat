@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   ApexNotification — Install / Setup (Windows)
echo ============================================================
echo.

:: ── Check Python ────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.10+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] Found %%i

:: ── Create virtual environment ───────────────────────────────────────────────
if exist .venv (
    echo [OK] Virtual environment already exists — skipping creation.
) else (
    echo [..] Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

:: ── Activate venv ────────────────────────────────────────────────────────────
echo [..] Activating virtual environment ...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Could not activate virtual environment.
    pause
    exit /b 1
)

:: ── Upgrade pip ──────────────────────────────────────────────────────────────
echo [..] Upgrading pip ...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded.

:: ── Install requirements ─────────────────────────────────────────────────────
echo [..] Installing requirements ...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed. Check requirements.txt and your internet connection.
    pause
    exit /b 1
)
echo [OK] Dependencies installed.

:: ── Create .env if missing ────────────────────────────────────────────────────
if not exist .env (
    copy .env.example .env >nul
    echo.
    echo [ВАЖНО] Файл .env создан из шаблона.
    echo         Открой .env и заполни:
    echo           BOT_TOKEN   — токен от @BotFather
    echo           ADMIN_IDS   — твой Telegram ID (число)
    echo           BOT_USERNAME — username бота без @
    echo.
    echo         После этого запусти run_windows.bat
) else (
    echo [OK] .env already exists.
)

:: ── Apply migrations ──────────────────────────────────────────────────────────
echo [..] Applying database migrations ...
python -m alembic upgrade head
if errorlevel 1 (
    echo [WARN] Alembic migration failed — check .env DATABASE_URL setting.
) else (
    echo [OK] Database up to date.
)

echo.
echo ============================================================
echo   Installation complete!
echo ============================================================
echo.
echo   Next steps:
echo     1. Open .env and fill in BOT_TOKEN, ADMIN_IDS, BOT_USERNAME
echo     2. Run: run_windows.bat
echo.
pause

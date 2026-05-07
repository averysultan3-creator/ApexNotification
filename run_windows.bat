@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ── Check .env ────────────────────────────────────────────────────────────────
if not exist .env (
    echo [ERROR] .env file not found!
    echo Run install_windows.bat first, then fill in BOT_TOKEN in .env
    pause
    exit /b 1
)

:: ── Check BOT_TOKEN is set ────────────────────────────────────────────────────
findstr /C:"BOT_TOKEN=your_bot_token_here" .env >nul 2>&1
if not errorlevel 1 (
    echo [ERROR] BOT_TOKEN не заполнен в .env
    echo Открой .env и замени "your_bot_token_here" на реальный токен.
    pause
    exit /b 1
)
findstr /R "^BOT_TOKEN=8656" .env >nul 2>&1
if not errorlevel 1 goto token_ok
findstr /C:"BOT_TOKEN=" .env >nul 2>&1
if errorlevel 1 (
    echo [ERROR] BOT_TOKEN отсутствует в .env
    pause
    exit /b 1
)
:token_ok

:: ── Check venv ────────────────────────────────────────────────────────────────
if not exist .venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment not found. Run install_windows.bat first.
    pause
    exit /b 1
)

:: ── Activate and run ─────────────────────────────────────────────────────────
call .venv\Scripts\activate.bat
echo [OK] Starting ApexNotification bot ...
echo      Press Ctrl+C to stop.
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Bot exited with an error. Check the output above.
    pause
)

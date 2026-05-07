@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo   ApexNotification — Update from GitHub
echo ============================================================
echo.

:: ── Check venv ────────────────────────────────────────────────────────────────
if not exist .venv\Scripts\activate.bat (
    echo [ERROR] Virtual environment not found. Run install_windows.bat first.
    pause
    exit /b 1
)

:: ── Git pull ──────────────────────────────────────────────────────────────────
echo [..] Pulling latest changes from GitHub ...
git pull
if errorlevel 1 (
    echo [ERROR] git pull failed. Check your internet connection or resolve merge conflicts.
    pause
    exit /b 1
)
echo [OK] Repository updated.

:: ── Activate venv ────────────────────────────────────────────────────────────
call .venv\Scripts\activate.bat

:: ── Update dependencies ───────────────────────────────────────────────────────
echo [..] Updating dependencies ...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)
echo [OK] Dependencies updated.

:: ── Apply migrations ──────────────────────────────────────────────────────────
echo [..] Applying database migrations ...
python -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] Alembic migration failed!
    echo         DO NOT start the bot until this is resolved.
    pause
    exit /b 1
)
echo [OK] Database migrations applied.

:: ── Syntax check ──────────────────────────────────────────────────────────────
echo [..] Running syntax check ...
set ERRORS=0
for /r %%f in (*.py) do (
    echo %%f | findstr /C:"__pycache__" >nul 2>&1
    if errorlevel 1 (
        python -m py_compile "%%f" 2>nul
        if errorlevel 1 (
            echo [SYNTAX ERROR] %%f
            set ERRORS=1
        )
    )
)
if !ERRORS! == 1 (
    echo [ERROR] Syntax errors found. Fix them before running the bot.
    pause
    exit /b 1
)
echo [OK] Syntax check passed.

:: ── Run tests ─────────────────────────────────────────────────────────────────
echo [..] Running tests ...
python -m pytest tests/ -v --tb=short -q
if errorlevel 1 (
    echo [ERROR] Tests failed! Check the output above before starting the bot.
    pause
    exit /b 1
)
echo [OK] All tests passed.

echo.
echo ============================================================
echo   Update completed successfully!
echo ============================================================
echo.
echo   Run the bot with: run_windows.bat
echo.
pause

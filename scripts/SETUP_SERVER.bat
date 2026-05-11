@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Apex Lead Router - Setup

for %%I in ("%~dp0..") do set "DIR=%%~fI"
if "!DIR:~-1!"=="\" set "DIR=!DIR:~0,-1!"
set "PY=!DIR!\.venv\Scripts\python.exe"
set "PYTHON_CMD="

cd /d "!DIR!"

:: -- Python detection (python / python3 / py launcher) ----
echo [SETUP] Checking Python...
python --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=python"

if "!PYTHON_CMD!"=="" (
    python3 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=python3"
)
if "!PYTHON_CMD!"=="" (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if "!PYTHON_CMD!"=="" (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.10+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during install.
    pause & exit /b 1
)

!PYTHON_CMD! -c "import sys; exit(0 if sys.version_info>=(3,10) else 1)" 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.10+ required. Current version is too old.
    echo         Download from https://python.org/downloads/
    pause & exit /b 1
)
echo [OK] Python OK (!PYTHON_CMD!)

:: -- Virtual env -------------------------------------------
if not exist "!DIR!\.venv\Scripts\python.exe" (
    echo [SETUP] Creating virtual environment...
    !PYTHON_CMD! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv creation failed. Try running as Administrator.
        pause & exit /b 1
    )
    echo [OK] venv created.
) else (
    echo [OK] venv exists.
)

echo [SETUP] Installing/updating dependencies (may take 1-2 min first time)...
"!PY!" -m pip install --upgrade pip -q 2>nul
"!PY!" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [WARN] First install attempt failed, retrying with verbose output...
    "!PY!" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency installation failed. Check internet connection.
        pause & exit /b 1
    )
)
echo [OK] Dependencies installed.

:: -- ngrok -------------------------------------------------
echo [SETUP] Checking ngrok...
set "NGROK_EXE="
for /f "tokens=*" %%i in ('where ngrok 2^>nul') do set "NGROK_EXE=%%i"
if "!NGROK_EXE!"=="" if exist "!DIR!\ngrok.exe" set "NGROK_EXE=!DIR!\ngrok.exe"
if "!NGROK_EXE!"=="" (
    echo [SETUP] ngrok not found. Downloading ngrok v3...
    :: Try primary CDN
    powershell -NoProfile -Command ^
        "try { Invoke-WebRequest 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile '%TEMP%\ngrok.zip' -UseBasicParsing -TimeoutSec 60; exit 0 } catch { exit 1 }"
    if errorlevel 1 (
        echo [WARN] Primary CDN failed, trying alternative...
        powershell -NoProfile -Command ^
            "try { Invoke-WebRequest 'https://github.com/nicowillis/ngrok-static/releases/download/v3/ngrok-v3-stable-windows-amd64.zip' -OutFile '%TEMP%\ngrok.zip' -UseBasicParsing -TimeoutSec 60; exit 0 } catch { exit 1 }"
    )
    if exist "%TEMP%\ngrok.zip" (
        powershell -NoProfile -Command "Expand-Archive -Path '%TEMP%\ngrok.zip' -DestinationPath '!DIR!' -Force"
        if exist "!DIR!\ngrok.exe" (
            set "NGROK_EXE=!DIR!\ngrok.exe"
            echo [OK] ngrok downloaded to !DIR!\ngrok.exe
        ) else (
            echo [WARN] ngrok download seems incomplete. You can install manually from https://ngrok.com/download
        )
    ) else (
        echo [WARN] Could not download ngrok. Install manually from https://ngrok.com/download
        echo        Then add ngrok.exe to this folder or to PATH.
    )
) else (
    echo [OK] ngrok found: !NGROK_EXE!
)

:: -- .env --------------------------------------------------
if not exist "!DIR!\.env" (
    if exist "!DIR!\.env.example" (
        echo [SETUP] Creating .env from .env.example...
        powershell -NoProfile -Command "$text=[IO.File]::ReadAllText('.env.example'); [IO.File]::WriteAllText('.env',$text,[Text.UTF8Encoding]::new($false))"
    ) else (
        echo [SETUP] Creating default .env...
        (
            echo BOT_TOKEN=
            echo ADMIN_IDS=
            echo ADMIN_SETUP_CODE=1234
            echo.
            echo DATABASE_URL=sqlite+aiosqlite:///./apex_lead_router.db
            echo LOG_LEVEL=INFO
            echo.
            echo PUBLIC_BASE_URL=http://localhost:8000
            echo WEB_HOST=0.0.0.0
            echo WEB_PORT=8000
            echo.
            echo FACEBOOK_VERIFY_TOKEN=apex_verify_changeme
            echo FACEBOOK_APP_SECRET=
            echo FACEBOOK_PAGE_ACCESS_TOKEN=
            echo FACEBOOK_GRAPH_VERSION=v19.0
            echo GOOGLE_SERVICE_ACCOUNT_JSON=
        ) > "!DIR!\.env"
    )
    echo.
    echo [WARN] .env created! You MUST fill BOT_TOKEN before running.
    echo        Opening .env now - add your BOT_TOKEN and ADMIN_IDS, then save and close.
    echo.
    start /wait notepad "!DIR!\.env"
    echo [SETUP] Checking BOT_TOKEN...
    powershell -NoProfile -Command ^
        "$env=(Get-Content '!DIR!\.env' -Raw); if($env -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[WARN] BOT_TOKEN is still empty! Bot will not work.'; exit 1} else {Write-Host '[OK] BOT_TOKEN is set.'; exit 0}"
    if errorlevel 1 (
        echo.
        echo [!] BOT_TOKEN is empty. Edit .env and fill it before starting.
        echo     You can do this later - run APEX.bat ^> Setup again to retry.
    )
) else (
    echo [OK] .env exists.
    :: Warn if BOT_TOKEN is empty
    powershell -NoProfile -Command ^
        "$env=(Get-Content '!DIR!\.env' -Raw); if($env -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[WARN] BOT_TOKEN is empty in .env - bot will not work!'}"
)

:: -- Folders -----------------------------------------------
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"
if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
if not exist "!DIR!\backups" mkdir "!DIR!\backups"
if not exist "!DIR!\exports" mkdir "!DIR!\exports"

:: -- DB migrations -----------------------------------------
echo [SETUP] Running database migrations...
"!PY!" -m alembic upgrade head 2>&1
if errorlevel 1 (
    echo [ERROR] Alembic migration failed.
    echo         Check that alembic.ini and alembic/ folder are present.
    pause & exit /b 1
)
echo [OK] Database up to date.

:: -- ngrok authtoken ---------------------------------------
if defined NGROK_EXE (
    :: Check if authtoken is already configured
    "!NGROK_EXE!" config check >nul 2>&1
    echo.
    set /p "NGROK_TOKEN=Enter ngrok authtoken (press Enter to skip if already configured): "
    if not "!NGROK_TOKEN!"=="" (
        "!NGROK_EXE!" config add-authtoken "!NGROK_TOKEN!"
        echo [OK] ngrok authtoken saved.
    ) else (
        echo [OK] Skipped ngrok authtoken.
    )
)

echo.
echo ============================================================
echo  [OK] Setup completed successfully!
echo.
echo  Next steps:
echo    1. Make sure BOT_TOKEN is set in .env
echo    2. Run APEX.bat ^> Start to launch the server
echo    3. Run APEX.bat ^> Watchdog for auto-restart on crash
echo ============================================================
echo.
endlocal

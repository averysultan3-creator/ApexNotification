@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Apex Lead Router

set "DIR=%~dp0"
if "!DIR:~-1!"=="\" set "DIR=!DIR:~0,-1!"
set "PY=!DIR!\.venv\Scripts\python.exe"
set "PID_FILE=!DIR!\runtime\server.pid"

cd /d "!DIR!"

:menu
cls
echo ============================================================
echo    Apex Lead Router  -  Control Panel
echo ============================================================
echo.
echo   1. Setup       (install deps, create .env, run migrations)
echo   2. Start       (start server + ngrok)
echo   3. Stop        (stop server + ngrok)
echo   4. Restart     (stop + start)
echo   5. Status      (show PID and /health)
echo   6. Logs        (tail logs/server.log)
echo   7. Watchdog    (monitor + auto-restart)
echo   8. Autostart   (register/remove Windows auto-start)
echo   0. Exit
echo.
set /p CHOICE=Choose [0-8]: 
if "!CHOICE!"=="1" goto do_setup
if "!CHOICE!"=="2" goto do_start
if "!CHOICE!"=="3" goto do_stop
if "!CHOICE!"=="4" goto do_restart
if "!CHOICE!"=="5" goto do_status
if "!CHOICE!"=="6" goto do_logs
if "!CHOICE!"=="7" goto do_watchdog
if "!CHOICE!"=="8" goto do_autostart
if "!CHOICE!"=="0" exit /b 0
goto menu

:: ============================================================
:: 1. SETUP
:: ============================================================
:do_setup
echo.

:: Python detection
echo [SETUP] Checking Python...
set "PYTHON_CMD="
python --version >nul 2>&1 && set "PYTHON_CMD=python"
if "!PYTHON_CMD!"=="" python3 --version >nul 2>&1 && set "PYTHON_CMD=python3"
if "!PYTHON_CMD!"=="" py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
if "!PYTHON_CMD!"=="" (
    echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during install.
    pause & goto menu
)
!PYTHON_CMD! -c "import sys; exit(0 if sys.version_info>=(3,10) else 1)" 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.10+ required. Download from https://python.org/downloads/
    pause & goto menu
)
echo [OK] Python found (!PYTHON_CMD!)

:: Virtual env
if not exist "!PY!" (
    echo [SETUP] Creating virtual environment...
    !PYTHON_CMD! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv creation failed. Try running as Administrator.
        pause & goto menu
    )
    echo [OK] venv created.
) else (
    echo [OK] venv exists.
)

:: Dependencies
echo [SETUP] Installing dependencies (first time ~1-2 min)...
"!PY!" -m pip install --upgrade pip -q 2>nul
"!PY!" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [WARN] First attempt failed, retrying with verbose output...
    "!PY!" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Dependency install failed. Check internet connection.
        pause & goto menu
    )
)
echo [OK] Dependencies installed.

:: ngrok
echo [SETUP] Checking ngrok...
set "NGROK_EXE="
for /f "tokens=*" %%i in ('where ngrok 2^>nul') do set "NGROK_EXE=%%i"
if "!NGROK_EXE!"=="" if exist "!DIR!\ngrok.exe" set "NGROK_EXE=!DIR!\ngrok.exe"
if "!NGROK_EXE!"=="" (
    echo [SETUP] Downloading ngrok v3...
    powershell -NoProfile -Command "try { Invoke-WebRequest 'https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip' -OutFile '$env:TEMP\ngrok.zip' -UseBasicParsing -TimeoutSec 60; exit 0 } catch { exit 1 }" >nul 2>&1
    if errorlevel 1 (
        echo [WARN] Primary CDN failed, trying alternative...
        powershell -NoProfile -Command "try { Invoke-WebRequest 'https://github.com/nicowillis/ngrok-static/releases/download/v3/ngrok-v3-stable-windows-amd64.zip' -OutFile '$env:TEMP\ngrok.zip' -UseBasicParsing -TimeoutSec 60; exit 0 } catch { exit 1 }" >nul 2>&1
    )
    if exist "%TEMP%\ngrok.zip" (
        powershell -NoProfile -Command "Expand-Archive -Path '$env:TEMP\ngrok.zip' -DestinationPath '!DIR!' -Force" >nul 2>&1
        if exist "!DIR!\ngrok.exe" (
            set "NGROK_EXE=!DIR!\ngrok.exe"
            echo [OK] ngrok downloaded.
        ) else (
            echo [WARN] ngrok download incomplete. Install manually from https://ngrok.com/download
        )
    ) else (
        echo [WARN] Could not download ngrok. Install manually from https://ngrok.com/download
    )
) else (
    echo [OK] ngrok found: !NGROK_EXE!
)

:: .env
if not exist "!DIR!\.env" (
    if exist "!DIR!\.env.example" (
        powershell -NoProfile -Command "$t=[IO.File]::ReadAllText('.env.example'); [IO.File]::WriteAllText('.env',$t,[Text.UTF8Encoding]::new($false))"
        echo [SETUP] .env created from .env.example
    ) else (
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
        echo [SETUP] Default .env created.
    )
    echo.
    echo [!] Fill BOT_TOKEN and ADMIN_IDS in .env, then save and close Notepad.
    start /wait notepad "!DIR!\.env"
    powershell -NoProfile -Command "$e=(Get-Content '!DIR!\.env' -Raw); if($e -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[WARN] BOT_TOKEN is still empty! Bot will not work.'} else {Write-Host '[OK] BOT_TOKEN is set.'}"
) else (
    echo [OK] .env exists.
    powershell -NoProfile -Command "$e=(Get-Content '!DIR!\.env' -Raw); if($e -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[WARN] BOT_TOKEN is empty in .env!'}"
)

:: Folders
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"
if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
if not exist "!DIR!\backups" mkdir "!DIR!\backups"
if not exist "!DIR!\exports" mkdir "!DIR!\exports"

:: Migrations
echo [SETUP] Running database migrations...
"!PY!" -m alembic upgrade head 2>&1
if errorlevel 1 (
    echo [ERROR] Alembic migration failed. Check alembic.ini and alembic/ folder.
    pause & goto menu
)
echo [OK] Database up to date.

:: ngrok authtoken
if defined NGROK_EXE (
    echo.
    set /p "NGROK_TOKEN=Enter ngrok authtoken (Enter to skip): "
    if not "!NGROK_TOKEN!"=="" (
        "!NGROK_EXE!" config add-authtoken "!NGROK_TOKEN!"
        echo [OK] ngrok authtoken saved.
    )
)

echo.
echo ============================================================
echo  [OK] Setup done! Next: choose 2 to Start server.
echo ============================================================
echo.
pause & goto menu

:: ============================================================
:: 2. START
:: ============================================================
:do_start
echo.
if not exist "!PY!" (
    echo [ERROR] .venv missing. Run Setup ^(1^) first.
    pause & goto menu
)
if not exist "!DIR!\.env" (
    echo [ERROR] .env missing. Run Setup ^(1^) first.
    pause & goto menu
)
powershell -NoProfile -Command "$e=(Get-Content '!DIR!\.env' -Raw); if($e -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[ERROR] BOT_TOKEN is empty!'; exit 1} else {exit 0}"
if errorlevel 1 pause & goto menu

if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"

:: Kill by PID file
if exist "!PID_FILE!" (
    set /p OLD_PID=<"!PID_FILE!"
    if not "!OLD_PID!"=="" (
        tasklist /fi "pid eq !OLD_PID!" /fo csv /nh 2>nul | findstr /i "python" >nul 2>&1
        if not errorlevel 1 (
            echo [START] Killing previous instance (PID !OLD_PID!)...
            taskkill /pid !OLD_PID! /f >nul 2>&1
            timeout /t 2 /nobreak >nul
        )
    )
    del "!PID_FILE!" >nul 2>&1
)

:: Kill any python main.py to avoid Telegram conflict
echo [START] Clearing conflicting processes...
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >nul

echo [START] Launching server...
start "Apex Lead Router Server" /min cmd /c ""!PY!" -u main.py all 2> "!DIR!\logs\stderr.log""

:: Start ngrok if available
set "NGROK_EXE="
for /f "tokens=*" %%i in ('where ngrok 2^>nul') do set "NGROK_EXE=%%i"
if "!NGROK_EXE!"=="" if exist "!DIR!\ngrok.exe" set "NGROK_EXE=!DIR!\ngrok.exe"
if defined NGROK_EXE (
    set "WEB_PORT=8000"
    for /f "tokens=2 delims==" %%v in ('findstr /i "^WEB_PORT" "!DIR!\.env" 2^>nul') do set "WEB_PORT=%%v"
    set "WEB_PORT=!WEB_PORT: =!"
    taskkill /im ngrok.exe /f >nul 2>&1
    timeout /t 1 /nobreak >nul
    start "ngrok" /min "!NGROK_EXE!" http !WEB_PORT!
    echo [START] ngrok started on port !WEB_PORT! - check URL at http://127.0.0.1:4040
) else (
    echo [INFO] ngrok not found, skipping. Add ngrok.exe to this folder or run Setup.
)

echo [START] Waiting up to 15 sec for health check...
set "READY=0"
for /l %%i in (1,1,15) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul
        powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0} else {exit 1} } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 set "READY=1"
    )
)

if "!READY!"=="1" (
    echo [OK] Server is up and healthy.
    powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 3; Write-Host $r.Content } catch {}"
) else (
    echo [WARN] Server did not respond in 15 sec. Check logs below.
    echo.
    echo --- Last 15 lines of logs\server.log ---
    if exist "!DIR!\logs\server.log" powershell -NoProfile -Command "Get-Content '!DIR!\logs\server.log' -Tail 15"
)
echo.
pause & goto menu

:: ============================================================
:: 3. STOP
:: ============================================================
:do_stop
echo.
set "STOPPED=0"

if exist "!PID_FILE!" (
    set /p PID=<"!PID_FILE!"
    if not "!PID!"=="" (
        tasklist /fi "pid eq !PID!" /fo csv /nh 2>nul | findstr /i "python" >nul 2>&1
        if not errorlevel 1 (
            echo [STOP] Killing PID !PID!...
            taskkill /pid !PID! /t /f >nul 2>&1
            set "STOPPED=1"
        )
    )
    del "!PID_FILE!" >nul 2>&1
)

powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main.py*'} | ForEach-Object { Write-Host ('[STOP] Killing stray PID '+$_.Id); $_ | Stop-Process -Force -ErrorAction SilentlyContinue }"

:: Stop ngrok
taskkill /im ngrok.exe /f >nul 2>&1 && echo [STOP] ngrok stopped.

if "!STOPPED!"=="1" (
    echo [OK] Server stopped.
) else (
    echo [OK] No running server found.
)
echo.
pause & goto menu

:: ============================================================
:: 4. RESTART
:: ============================================================
:do_restart
goto do_stop_for_restart

:do_stop_for_restart
set "STOPPED=0"
if exist "!PID_FILE!" (
    set /p PID=<"!PID_FILE!"
    if not "!PID!"=="" (
        tasklist /fi "pid eq !PID!" /fo csv /nh 2>nul | findstr /i "python" >nul 2>&1
        if not errorlevel 1 taskkill /pid !PID! /t /f >nul 2>&1
    )
    del "!PID_FILE!" >nul 2>&1
)
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >nul
goto do_start

:: ============================================================
:: 5. STATUS
:: ============================================================
:do_status
echo.
if exist "!PID_FILE!" (
    set /p P=<"!PID_FILE!"
    echo PID file: !P!
    tasklist /FI "PID eq !P!" 2>nul | findstr /I python.exe >nul && echo Process: RUNNING || echo Process: NOT RUNNING (stale PID)
) else (
    echo PID file: not found
)
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 3; Write-Host ('Health: '+$r.StatusCode+' '+$r.Content) } catch { Write-Host 'Health: DOWN' }"
echo.
pause & goto menu

:: ============================================================
:: 6. LOGS
:: ============================================================
:do_logs
if not exist "!DIR!\logs\server.log" (
    echo No logs\server.log yet.
    pause & goto menu
)
echo --- Last 40 lines of logs\server.log ---
powershell -NoProfile -Command "Get-Content '!DIR!\logs\server.log' -Tail 40"
echo.
pause & goto menu

:: ============================================================
:: 7. WATCHDOG
:: ============================================================
:do_watchdog
echo.
echo [WATCHDOG] Monitoring server (Ctrl+C to exit)...
echo [WATCHDOG] Logs: logs\watchdog.log
echo.
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"
if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
echo [%date% %time%] Watchdog started. >> "!DIR!\logs\watchdog.log"

:watchdog_loop
set "SERVER_OK=0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 8; if($r.StatusCode -eq 200){exit 0} else {exit 1} } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 set "SERVER_OK=1"

if "!SERVER_OK!"=="1" (
    timeout /t 30 /nobreak >nul
    goto watchdog_loop
)

echo [%date% %time%] Health check failed - restarting... >> "!DIR!\logs\watchdog.log"
echo [WATCHDOG] Server is DOWN - restarting...

:: Inline start (no external script call)
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >nul
start "Apex Lead Router Server" /min cmd /c ""!PY!" -u main.py all 2> "!DIR!\logs\stderr.log""
echo [%date% %time%] Server restarted. >> "!DIR!\logs\watchdog.log"

timeout /t 60 /nobreak >nul
goto watchdog_loop

:: ============================================================
:: 8. AUTOSTART
:: ============================================================
:do_autostart
echo.
echo   1. Register autostart (run on Windows login)
echo   2. Remove autostart
echo   0. Back
echo.
set /p ACHOICE=Choose [0-2]: 
if "!ACHOICE!"=="1" goto autostart_register
if "!ACHOICE!"=="2" goto autostart_remove
goto menu

:autostart_register
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$a=New-ScheduledTaskAction -Execute '!DIR!\APEX.bat' -Argument '2'; ^
     $t=New-ScheduledTaskTrigger -AtLogOn; ^
     $s=New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 2) -ExecutionTimeLimit ([TimeSpan]::Zero); ^
     Register-ScheduledTask -TaskName 'ApexLeadRouter' -Action $a -Trigger $t -Settings $s -RunLevel Highest -Force | Out-Null; ^
     Write-Host '[OK] Autostart registered. Server will start automatically on login.'"
echo.
pause & goto menu

:autostart_remove
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Unregister-ScheduledTask -TaskName 'ApexLeadRouter' -Confirm:$false -ErrorAction SilentlyContinue; ^
     Write-Host '[OK] Autostart removed.'"
echo.
pause & goto menu
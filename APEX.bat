@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Apex Lead Router

set "DIR=%~dp0"
if "!DIR:~-1!"=="\" set "DIR=!DIR:~0,-1!"
set "PY=!DIR!\.venv\Scripts\python.exe"
set "PID_FILE=!DIR!\runtime\server.pid"
set "REPO_URL=https://github.com/averysultan3-creator/ApexNotification.git"
set "INSTALL_DIR=D:\ApexNotification"
if not exist "D:\" set "INSTALL_DIR=%SystemDrive%\ApexNotification"

:: Optional one-file bootstrap secrets.
:: Leave empty for safe mode: Setup opens .env and asks ngrok token.
:: Fill only in your private server copy if you want fully unattended setup.
set "BOOTSTRAP_BOT_TOKEN="
set "BOOTSTRAP_ADMIN_IDS="
set "BOOTSTRAP_NGROK_TOKEN="

cd /d "!DIR!"

:: If this single BAT was copied to an empty server folder, bootstrap the project.
if exist "!DIR!\main.py" goto after_bootstrap

echo ============================================================
echo  Apex Lead Router bootstrap
echo ============================================================
echo This folder does not contain the project. Installing to:
echo   !INSTALL_DIR!
echo.
call :ensure_git
if errorlevel 1 goto bootstrap_git_error
if not exist "!INSTALL_DIR!" mkdir "!INSTALL_DIR!" >nul 2>&1
if exist "!INSTALL_DIR!\main.py" goto bootstrap_update_existing

echo [BOOT] Cloning repository...
git clone "!REPO_URL!" "!INSTALL_DIR!"
if errorlevel 1 goto bootstrap_clone_error
goto bootstrap_continue

:bootstrap_update_existing
echo [BOOT] Project already exists. Updating...
cd /d "!INSTALL_DIR!"
git pull --ff-only

:bootstrap_continue
copy /y "%~f0" "!INSTALL_DIR!\APEX.bat" >nul 2>&1
:: If APEX_SECRETS.txt sits next to the bat file, use it as .env (fully unattended deploy)
if exist "%~dp0APEX_SECRETS.txt" (
    echo [BOOT] Found APEX_SECRETS.txt - copying as .env...
    copy /y "%~dp0APEX_SECRETS.txt" "!INSTALL_DIR!\.env" >nul 2>&1
    echo [OK] .env installed from APEX_SECRETS.txt
)
cd /d "!INSTALL_DIR!"
set "DIR=!INSTALL_DIR!"
set "PY=!INSTALL_DIR!\.venv\Scripts\python.exe"
set "PID_FILE=!INSTALL_DIR!\runtime\server.pid"
set "APEX_AUTORUN=1"
echo.
echo [BOOT] Step 1/3: Running setup...
call "!INSTALL_DIR!\APEX.bat" 1
echo.
echo [BOOT] Step 2/3: Starting server + ngrok...
call "!INSTALL_DIR!\APEX.bat" 2
echo.
echo [BOOT] Step 3/3: Registering watchdog autostart...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$a=New-ScheduledTaskAction -Execute '!INSTALL_DIR!\APEX.bat' -Argument '7'; $t=New-ScheduledTaskTrigger -AtLogOn; $s=New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 2); Register-ScheduledTask -TaskName 'ApexLeadRouter' -Action $a -Trigger $t -Settings $s -RunLevel Highest -Force | Out-Null; Write-Host '[OK] Watchdog autostart registered.'"
echo.
echo ============================================================
echo  Apex Lead Router is LIVE
echo ============================================================
echo  Folder  : !INSTALL_DIR!
echo  Health  : http://127.0.0.1:8000/health
echo  Manage  : run APEX.bat from !INSTALL_DIR!
echo  Watchdog: APEX.bat menu item 7
echo ============================================================
echo.
pause
exit /b 0

:bootstrap_git_error
echo [ERROR] Git is required and could not be installed automatically.
echo Install Git manually: https://git-scm.com/download/win
pause
exit /b 1

:bootstrap_clone_error
echo [ERROR] git clone failed. Check internet/GitHub access.
pause
exit /b 1

:after_bootstrap

:: Set CLI flag when called with argument (no pause/menu after action)
if not "%~1"=="" set "APEX_CLI=1"

if "%~1"=="1" goto do_setup
if "%~1"=="2" goto do_start
if "%~1"=="3" goto do_stop
if "%~1"=="4" goto do_restart
if "%~1"=="5" goto do_status
if "%~1"=="6" goto do_logs
if "%~1"=="7" goto do_watchdog
if "%~1"=="8" goto do_autostart
if "%~1"=="9" goto do_update

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
echo   7. Watchdog    (monitor + auto-restart + Telegram alerts)
echo   8. Autostart   (register/remove Windows auto-start)
echo   9. Update      (git pull + migrate + restart)
echo   0. Exit
echo.
set "CHOICE="
set /p CHOICE=Choose [0-9]: 
if not defined CHOICE exit /b 0
if "!CHOICE!"=="1" goto do_setup
if "!CHOICE!"=="2" goto do_start
if "!CHOICE!"=="3" goto do_stop
if "!CHOICE!"=="4" goto do_restart
if "!CHOICE!"=="5" goto do_status
if "!CHOICE!"=="6" goto do_logs
if "!CHOICE!"=="7" goto do_watchdog
if "!CHOICE!"=="8" goto do_autostart
if "!CHOICE!"=="9" goto do_update
if "!CHOICE!"=="0" exit /b 0
goto menu

:: ============================================================
:: 1. SETUP
:: ============================================================
:do_setup
echo.

call :ensure_git
if exist "!DIR!\.git" (
    echo [SETUP] Updating project from GitHub...
    git fetch --all
    git pull --ff-only
    if errorlevel 1 (
        echo [WARN] git pull failed. Continuing with local files.
    ) else (
        echo [OK] Project updated.
    )
)

:: Python detection
echo [SETUP] Checking Python...
set "PYTHON_CMD="
python --version >nul 2>&1 && set "PYTHON_CMD=python"
if "!PYTHON_CMD!"=="" python3 --version >nul 2>&1 && set "PYTHON_CMD=python3"
if "!PYTHON_CMD!"=="" py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
if "!PYTHON_CMD!"=="" (
    echo [SETUP] Python not found. Trying winget install...
    winget install --id Python.Python.3.11 -e --source winget --silent --accept-package-agreements --accept-source-agreements
    set "PATH=%PATH%;%LocalAppData%\Programs\Python\Python311;%LocalAppData%\Programs\Python\Python311\Scripts"
    python --version >nul 2>&1 && set "PYTHON_CMD=python"
    if "!PYTHON_CMD!"=="" (
        echo [ERROR] Python not found. Install Python 3.10+ from https://python.org
        echo         Make sure to check "Add Python to PATH" during install.
        if defined APEX_CLI (exit /b 0)
pause ^& goto menu
    )
)
!PYTHON_CMD! -c "import sys; exit(0 if sys.version_info>=(3,10) else 1)" 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.10+ required. Download from https://python.org/downloads/
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
echo [OK] Python found (!PYTHON_CMD!)

:: Virtual env
if not exist "!PY!" (
    echo [SETUP] Creating virtual environment...
    !PYTHON_CMD! -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv creation failed. Try running as Administrator.
        if defined APEX_CLI (exit /b 0)
pause ^& goto menu
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
        if defined APEX_CLI (exit /b 0)
pause ^& goto menu
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
    if not "!BOOTSTRAP_BOT_TOKEN!"=="" powershell -NoProfile -Command "$p='!DIR!\.env'; $e=Get-Content $p -Raw; $e=[regex]::Replace($e,'(?m)^BOT_TOKEN=.*','BOT_TOKEN=!BOOTSTRAP_BOT_TOKEN!'); [IO.File]::WriteAllText($p,$e,[Text.UTF8Encoding]::new($false))"
    if not "!BOOTSTRAP_ADMIN_IDS!"=="" powershell -NoProfile -Command "$p='!DIR!\.env'; $e=Get-Content $p -Raw; $e=[regex]::Replace($e,'(?m)^ADMIN_IDS=.*','ADMIN_IDS=!BOOTSTRAP_ADMIN_IDS!'); [IO.File]::WriteAllText($p,$e,[Text.UTF8Encoding]::new($false))"
    powershell -NoProfile -Command "$e=(Get-Content '!DIR!\.env' -Raw); if($e -match 'BOT_TOKEN=\s*\r?\n'){exit 1} else {exit 0}"
    if errorlevel 1 (
        echo [!] Fill BOT_TOKEN and ADMIN_IDS in .env, then save and close Notepad.
        start /wait notepad "!DIR!\.env"
    )
    powershell -NoProfile -Command "$e=(Get-Content '!DIR!\.env' -Raw); if($e -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[WARN] BOT_TOKEN is still empty! Bot will not work.'} else {Write-Host '[OK] BOT_TOKEN is set.'}"
) else (
    echo [OK] .env exists.
    powershell -NoProfile -Command "$e=(Get-Content '!DIR!\.env' -Raw); if($e -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[WARN] BOT_TOKEN is empty in .env!'}"
)

if exist "!DIR!\.env.example" (
    echo [SETUP] Syncing missing .env keys from .env.example...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$envPath='!DIR!\.env'; $exPath='!DIR!\.env.example'; $envText=Get-Content $envPath -Raw; $add=@(); foreach($line in Get-Content $exPath){ if($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)='){ $k=$Matches[1]; if($envText -notmatch ('(?m)^'+[regex]::Escape($k)+'=')){ $add += $line } } }; if($add.Count -gt 0){ Add-Content -Path $envPath -Value ''; Add-Content -Path $envPath -Value '# Added by APEX.bat after update'; Add-Content -Path $envPath -Value $add; Write-Host ('[OK] Added missing keys: '+($add -join ', ')) } else { Write-Host '[OK] .env has all known keys.' }"
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='!DIR!\.env'; $e=Get-Content $p -Raw; if($e -match '(?m)^BOT_TOKEN=(.+)$'){ $tok=$Matches[1].Trim() } else { $tok='' }; if($tok -and ($e -notmatch '(?m)^BOT_USERNAME=\S+')){ try { $r=Invoke-RestMethod ('https://api.telegram.org/bot'+$tok+'/getMe') -TimeoutSec 10; if($r.ok -and $r.result.username){ if($e -match '(?m)^BOT_USERNAME='){ $e=$e -replace '(?m)^BOT_USERNAME=.*','BOT_USERNAME='+$r.result.username } else { $e += \"`r`nBOT_USERNAME=\"+$r.result.username+\"`r`n\" }; [IO.File]::WriteAllText($p,$e,[Text.UTF8Encoding]::new($false)); Write-Host ('[OK] BOT_USERNAME='+$r.result.username) } } catch { Write-Host '[WARN] Could not auto-detect BOT_USERNAME.' } }"

:: Folders
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"
if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
if not exist "!DIR!\backups" mkdir "!DIR!\backups"
if not exist "!DIR!\exports" mkdir "!DIR!\exports"

:: Migrations
if exist "!DIR!\apex_lead_router.db" (
    echo [SETUP] Creating database backup...
    for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%t"
    set "BACKUP_FILE=!DIR!\backups\apex_lead_router_!TS!.db"
    copy /y "!DIR!\apex_lead_router.db" "!BACKUP_FILE!" >nul
    if exist "!BACKUP_FILE!" echo [OK] Backup: !BACKUP_FILE!
    powershell -NoProfile -Command "Get-ChildItem '!DIR!\backups\apex_lead_router_*.db' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 20 | Remove-Item -Force -ErrorAction SilentlyContinue"
)
echo [SETUP] Running database migrations...
"!PY!" -m alembic upgrade head 2>&1
if errorlevel 1 (
    echo [ERROR] Alembic migration failed. Check alembic.ini and alembic/ folder.
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
echo [OK] Database up to date.

:: ngrok authtoken
if defined NGROK_EXE (
    echo.
    set "NGROK_TOKEN=!BOOTSTRAP_NGROK_TOKEN!"
    :: Read from .env if not set via bootstrap
    if "!NGROK_TOKEN!"=="" (
        for /f "tokens=1,* delims==" %%a in ('findstr /b /i "NGROK_AUTHTOKEN=" "!DIR!\.env" 2^>nul') do set "NGROK_TOKEN=%%b"
        set "NGROK_TOKEN=!NGROK_TOKEN: =!"
    )
    if "!NGROK_TOKEN!"=="" set /p "NGROK_TOKEN=Enter ngrok authtoken (Enter to skip): "
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
if defined APEX_AUTORUN exit /b 0
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:: ============================================================
:: 2. START
:: ============================================================
:do_start
echo.
if not exist "!PY!" (
    echo [ERROR] .venv missing. Run Setup ^(1^) first.
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
if not exist "!DIR!\.env" (
    echo [ERROR] .env missing. Run Setup ^(1^) first.
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
powershell -NoProfile -Command "$e=(Get-Content '!DIR!\.env' -Raw); if($e -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[ERROR] BOT_TOKEN is empty!'; exit 1} else {exit 0}"
if errorlevel 1 (
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)

if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"

:: Kill by PID file
if exist "!PID_FILE!" (
    set "OLD_PID="
    for /f "usebackq" %%p in ("!PID_FILE!") do set "OLD_PID=%%p"
    if not "!OLD_PID!"=="" (
        tasklist /fi "pid eq !OLD_PID!" /fo csv /nh 2>nul | findstr /i "python" >nul 2>&1
        if not errorlevel 1 (
            echo [START] Killing previous instance ^(PID !OLD_PID!^)...
            taskkill /pid !OLD_PID! /f >nul 2>&1
            timeout /t 3 /nobreak >nul
        )
    )
    del "!PID_FILE!" >nul 2>&1
)

:: Kill any python main.py to avoid Telegram conflict
echo [START] Clearing conflicting processes...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 /nobreak >nul

echo [START] Launching server...
powershell -NoProfile -Command "Start-Process -FilePath '!PY!' -ArgumentList '-u','main.py','all' -WorkingDirectory '!DIR!' -WindowStyle Hidden -RedirectStandardError '!DIR!\logs\stderr.log'"

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
    echo [START] ngrok started on port !WEB_PORT! - detecting public URL...
    powershell -NoProfile -Command "$url=$null; for($i=0;$i -lt 15;$i++){ try{$t=(Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 2).tunnels | Select-Object -First 1; if($t.public_url){$url=$t.public_url; break}}catch{}; Start-Sleep -Seconds 1 }; if($url){ $p='!DIR!\.env'; $e=Get-Content $p -Raw; if($e -match '(?m)^PUBLIC_BASE_URL='){ $e=[regex]::Replace($e,'(?m)^PUBLIC_BASE_URL=.*','PUBLIC_BASE_URL='+$url) } else { $e += ([char]13+[char]10+'PUBLIC_BASE_URL='+$url+[char]13+[char]10) }; [IO.File]::WriteAllText($p,$e,[Text.UTF8Encoding]::new($false)); Write-Host ('[OK] PUBLIC_BASE_URL='+$url) } else { Write-Host '[WARN] Could not detect ngrok URL. Open http://127.0.0.1:4040' }"
    :: Restart Python so it picks up the new PUBLIC_BASE_URL from .env
    echo [START] Restarting server with new public URL...
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    timeout /t 2 /nobreak >nul
    powershell -NoProfile -Command "Start-Process -FilePath '!PY!' -ArgumentList '-u','main.py','all' -WorkingDirectory '!DIR!' -WindowStyle Hidden -RedirectStandardError '!DIR!\logs\stderr.log'"
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
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Server failed to start or /health is DOWN after Start." >nul 2>&1
    echo.
    echo --- Last 15 lines of logs\server.log ---
    if exist "!DIR!\logs\server.log" powershell -NoProfile -Command "Get-Content '!DIR!\logs\server.log' -Tail 15"
)
echo.
if defined APEX_AUTORUN exit /b 0
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:: ============================================================
:: 3. STOP
:: ============================================================
:do_stop
echo.
set "STOPPED=0"

if exist "!PID_FILE!" (
    set "PID="
    for /f "usebackq" %%p in ("!PID_FILE!") do set "PID=%%p"
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

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Write-Host ('[STOP] Killing stray PID '+$_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

:: Stop ngrok
taskkill /im ngrok.exe /f >nul 2>&1 && echo [STOP] ngrok stopped.

if "!STOPPED!"=="1" (
    echo [OK] Server stopped.
) else (
    echo [OK] No running server found.
)
echo.
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:: ============================================================
:: 4. RESTART
:: ============================================================
:do_restart
goto do_stop_for_restart

:do_stop_for_restart
set "STOPPED=0"
if exist "!PID_FILE!" (
    set "PID="
    for /f "usebackq" %%p in ("!PID_FILE!") do set "PID=%%p"
    if not "!PID!"=="" (
        tasklist /fi "pid eq !PID!" /fo csv /nh 2>nul | findstr /i "python" >nul 2>&1
        if not errorlevel 1 taskkill /pid !PID! /t /f >nul 2>&1
    )
    del "!PID_FILE!" >nul 2>&1
)
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 /nobreak >nul
goto do_start

:: ============================================================
:: 5. STATUS
:: ============================================================
:do_status
echo.
if exist "!PID_FILE!" (
    set "P="
    for /f "usebackq" %%p in ("!PID_FILE!") do set "P=%%p"
    echo PID file: !P!
    tasklist /FI "PID eq !P!" 2>nul | findstr /I python.exe >nul && echo Process: RUNNING || echo Process: NOT RUNNING (stale PID)
) else (
    echo PID file: not found
)
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 3; Write-Host ('Health: '+$r.StatusCode+' '+$r.Content) } catch { Write-Host 'Health: DOWN'; if(Test-Path '!DIR!\logs\stderr.log'){ Write-Host '--- Last error (stderr.log) ---'; Get-Content '!DIR!\logs\stderr.log' -Tail 5 } }"
echo.
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:: ============================================================
:: 6. LOGS
:: ============================================================
:do_logs
echo.
if exist "!DIR!\logs\server.log" (
    echo --- Last 40 lines of logs\server.log ---
    powershell -NoProfile -Command "Get-Content '!DIR!\logs\server.log' -Tail 40"
) else (
    echo [INFO] logs\server.log not found yet ^(server never started?^)
)
if exist "!DIR!\logs\stderr.log" (
    echo.
    echo --- Last 20 lines of logs\stderr.log ---
    powershell -NoProfile -Command "Get-Content '!DIR!\logs\stderr.log' -Tail 20"
)
echo.
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:: ============================================================
:: 7. WATCHDOG
:: ============================================================
:do_watchdog
echo.
echo [WATCHDOG] Monitoring server every 30 sec (Ctrl+C to exit)
echo [WATCHDOG] Telegram alerts to ADMIN_IDS on crash
echo [WATCHDOG] Auto-update from GitHub every 10 min
echo [WATCHDOG] Log: logs\watchdog.log
echo.
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"
if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
echo [%date% %time%] Watchdog started. >> "!DIR!\logs\watchdog.log"

set "WD_FAIL_COUNT=0"
set "WD_LOOP=0"

:watchdog_loop
set /a WD_LOOP+=1

:: ---- Health check ----
set "SERVER_OK=0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 8; if($r.StatusCode -eq 200){exit 0} else {exit 1} } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 set "SERVER_OK=1"

if "!SERVER_OK!"=="1" (
    set "WD_FAIL_COUNT=0"
    call :wd_public_check
    if !WD_LOOP! GEQ 20 (
        set "WD_LOOP=0"
        call :wd_check_update
    )
    timeout /t 30 /nobreak >nul
    goto watchdog_loop
)

:: ---- Server is DOWN ----
set /a WD_FAIL_COUNT+=1
echo [%date% %time%] Health fail #!WD_FAIL_COUNT! - restarting... >> "!DIR!\logs\watchdog.log"
echo [WATCHDOG] Server is DOWN (attempt !WD_FAIL_COUNT!) - restarting...

if "!WD_FAIL_COUNT!"=="1" (
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Server DOWN - restarting by watchdog." >nul 2>&1
)
if "!WD_FAIL_COUNT!"=="3" (
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Server crashed 3 times in a row. Check logs immediately." >nul 2>&1
)

powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 /nobreak >nul
powershell -NoProfile -Command "Start-Process -FilePath '!PY!' -ArgumentList '-u','main.py','all' -WorkingDirectory '!DIR!' -WindowStyle Hidden -RedirectStandardError '!DIR!\logs\stderr.log'"
echo [%date% %time%] Server restarted (attempt !WD_FAIL_COUNT!). >> "!DIR!\logs\watchdog.log"

timeout /t 60 /nobreak >nul
goto watchdog_loop

:: Subroutine: check public URL / ngrok tunnel.
:wd_public_check
set "PUBLIC_BASE="
for /f "tokens=1,* delims==" %%a in ('findstr /b /i "PUBLIC_BASE_URL=" "!DIR!\.env" 2^>nul') do set "PUBLIC_BASE=%%b"
if "!PUBLIC_BASE!"=="" exit /b 0
echo !PUBLIC_BASE! | findstr /i "localhost 127.0.0.1" >nul && exit /b 0

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $r=Invoke-WebRequest -Uri '!PUBLIC_BASE!/health' -Headers @{'ngrok-skip-browser-warning'='1'} -UseBasicParsing -TimeoutSec 8; if($r.StatusCode -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 exit /b 0

echo [%date% %time%] Public health fail: !PUBLIC_BASE! - restarting ngrok... >> "!DIR!\logs\watchdog.log"
if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Public URL is DOWN. Restarting ngrok and updating PUBLIC_BASE_URL." >nul 2>&1
taskkill /im ngrok.exe /f >nul 2>&1

set "NGROK_EXE="
for /f "tokens=*" %%i in ('where ngrok 2^>nul') do set "NGROK_EXE=%%i"
if "!NGROK_EXE!"=="" if exist "!DIR!\ngrok.exe" set "NGROK_EXE=!DIR!\ngrok.exe"
if "!NGROK_EXE!"=="" exit /b 0

for /f "tokens=2 delims==" %%v in ('findstr /i "^WEB_PORT" "!DIR!\.env" 2^>nul') do set "WEB_PORT=%%v"
if "!WEB_PORT!"=="" set "WEB_PORT=8000"
start "ngrok" /min "!NGROK_EXE!" http !WEB_PORT!

powershell -NoProfile -ExecutionPolicy Bypass -Command "$url=$null; for($i=0;$i -lt 20;$i++){ try{$t=(Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 2).tunnels | Select-Object -First 1; if($t.public_url){$url=$t.public_url; break}}catch{}; Start-Sleep -Seconds 1 }; if($url){ $p='!DIR!\.env'; $e=Get-Content $p -Raw; $e=[regex]::Replace($e,'(?m)^PUBLIC_BASE_URL=.*','PUBLIC_BASE_URL='+$url); [IO.File]::WriteAllText($p,$e,[Text.UTF8Encoding]::new($false)); exit 0 } else { exit 1 }" >nul 2>&1
if not errorlevel 1 (
    echo [%date% %time%] Public URL recovered and .env updated. >> "!DIR!\logs\watchdog.log"
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Public URL recovered. PUBLIC_BASE_URL was updated. Server restarting." >nul 2>&1
    :: Restart Python server so it picks up the new PUBLIC_BASE_URL from .env
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    timeout /t 3 /nobreak >nul
    powershell -NoProfile -Command "Start-Process -FilePath '!PY!' -ArgumentList '-u','main.py','all' -WorkingDirectory '!DIR!' -WindowStyle Hidden -RedirectStandardError '!DIR!\logs\stderr.log'"
    echo [%date% %time%] Server restarted with new PUBLIC_BASE_URL. >> "!DIR!\logs\watchdog.log"
) else (
    echo [%date% %time%] Failed to recover public URL. >> "!DIR!\logs\watchdog.log"
)
exit /b 0

:: Subroutine: auto-update from GitHub
:wd_check_update
git fetch origin main >nul 2>&1
set "GIT_BEHIND=0"
for /f %%c in ('git rev-list HEAD...origin/main --count 2^>nul') do set "GIT_BEHIND=%%c"
if "!GIT_BEHIND!"=="" set "GIT_BEHIND=0"
if !GIT_BEHIND! GTR 0 (
    echo [%date% %time%] Auto-update: !GIT_BEHIND! new commit(s). >> "!DIR!\logs\watchdog.log"
    echo [WATCHDOG] Update available - applying !GIT_BEHIND! commit(s)...
    if not exist "!DIR!\backups" mkdir "!DIR!\backups"
    if exist "!DIR!\apex_lead_router.db" (
        for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "BKP_TS=%%t"
        copy /Y "!DIR!\apex_lead_router.db" "!DIR!\backups\apex_lead_router_!BKP_TS!.db" >nul
    )
    git pull origin main >nul 2>&1
    "!PY!" -m pip install -r requirements.txt -q >nul 2>&1
    "!PY!" -m alembic upgrade head >nul 2>&1
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Auto-update applied (!GIT_BEHIND! commits). Server restarting." >nul 2>&1
    powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    timeout /t 3 /nobreak >nul
    powershell -NoProfile -Command "Start-Process -FilePath '!PY!' -ArgumentList '-u','main.py','all' -WorkingDirectory '!DIR!' -WindowStyle Hidden -RedirectStandardError '!DIR!\logs\stderr.log'"
    echo [%date% %time%] Updated and restarted. >> "!DIR!\logs\watchdog.log"
    echo [WATCHDOG] Update applied, server restarted.
    timeout /t 30 /nobreak >nul
)
exit /b 0

:: ============================================================
:: 8. AUTOSTART
:: ============================================================
:do_autostart
echo.
echo   1. Register autostart (run on Windows login)
echo   2. Remove autostart
echo   0. Back
echo.
set "ACHOICE="
set /p ACHOICE=Choose [0-2]: 
if not defined ACHOICE goto menu
if "!ACHOICE!"=="1" goto autostart_register
if "!ACHOICE!"=="2" goto autostart_remove
goto menu

:autostart_register
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$a=New-ScheduledTaskAction -Execute '!DIR!\APEX.bat' -Argument '7'; ^
     $t=New-ScheduledTaskTrigger -AtLogOn; ^
     $s=New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 2); ^
     Register-ScheduledTask -TaskName 'ApexLeadRouter' -Action $a -Trigger $t -Settings $s -RunLevel Highest -Force | Out-Null; ^
     Write-Host '[OK] Watchdog autostart registered. It starts server and keeps it alive.'"
echo.
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:autostart_remove
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Unregister-ScheduledTask -TaskName 'ApexLeadRouter' -Confirm:$false -ErrorAction SilentlyContinue; ^
     Write-Host '[OK] Autostart removed.'"
echo.
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:: ============================================================
:: 9. UPDATE
:: ============================================================
:do_update
echo.
echo [UPDATE] Fetching latest changes from GitHub...
call :ensure_git
if errorlevel 1 (
    echo [ERROR] Git is not available and automatic install failed.
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
git fetch origin main 2>&1
set "GIT_BEHIND=0"
for /f %%c in ('git rev-list HEAD...origin/main --count 2^>nul') do set "GIT_BEHIND=%%c"
if "!GIT_BEHIND!"=="" set "GIT_BEHIND=0"
if !GIT_BEHIND! EQU 0 (
    echo [OK] Already up to date.
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
echo [UPDATE] !GIT_BEHIND! new commit(s) available. Pulling...
if not exist "!DIR!\backups" mkdir "!DIR!\backups"
if exist "!DIR!\apex_lead_router.db" (
    for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "BKP_TS=%%t"
    echo [UPDATE] Backup database: backups\apex_lead_router_!BKP_TS!.db
    copy /Y "!DIR!\apex_lead_router.db" "!DIR!\backups\apex_lead_router_!BKP_TS!.db" >nul
    powershell -NoProfile -Command "Get-ChildItem '!DIR!\backups\apex_lead_router_*.db' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 20 | Remove-Item -Force -ErrorAction SilentlyContinue"
)
git pull origin main
if errorlevel 1 (
    echo [ERROR] git pull failed. Check connectivity or local conflicts.
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Manual update failed during git pull. Check server console." >nul 2>&1
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
echo [UPDATE] Installing any new dependencies...
"!PY!" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [ERROR] pip install failed.
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Manual update failed during pip install. Check logs." >nul 2>&1
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
echo [UPDATE] Running migrations...
"!PY!" -m alembic upgrade head
if errorlevel 1 (
    echo [ERROR] alembic migration failed. Backup was kept in backups.
    if exist "!PY!" if exist "!DIR!\notify_admins.py" "!PY!" "!DIR!\notify_admins.py" "Manual update failed during database migration. Backup was kept." >nul 2>&1
    if defined APEX_CLI (exit /b 0)
pause ^& goto menu
)
echo [UPDATE] Restarting server...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'name=''python.exe''' | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 /nobreak >nul
if not exist "!DIR!\logs"    mkdir "!DIR!\logs"
powershell -NoProfile -Command "Start-Process -FilePath '!PY!' -ArgumentList '-u','main.py','all' -WorkingDirectory '!DIR!' -WindowStyle Hidden -RedirectStandardError '!DIR!\logs\stderr.log'"
timeout /t 8 /nobreak >nul
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 3; Write-Host '[OK] Server up: '+$r.Content } catch { Write-Host '[WARN] Server not responding yet - check Logs' }"
echo.
echo [UPDATE] Done! Applied !GIT_BEHIND! commit(s).
if defined APEX_CLI (exit /b 0)
pause ^& goto menu

:: ============================================================
:: Helpers
:: ============================================================
:ensure_git
git --version >nul 2>&1
if not errorlevel 1 exit /b 0
echo [SETUP] Git not found. Trying winget install...
winget install --id Git.Git -e --source winget --silent --accept-package-agreements --accept-source-agreements
set "PATH=%PATH%;%ProgramFiles%\Git\cmd"
git --version >nul 2>&1
if errorlevel 1 exit /b 1
exit /b 0

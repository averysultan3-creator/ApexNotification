@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Apex Lead Router - Start

for %%I in ("%~dp0..") do set "DIR=%%~fI"
if "!DIR:~-1!"=="\" set "DIR=!DIR:~0,-1!"
set "PY=!DIR!\.venv\Scripts\python.exe"
set "PID_FILE=!DIR!\runtime\server.pid"

cd /d "!DIR!"

if not exist "!PY!" (
    echo [ERROR] .venv is missing. Run APEX.bat ^> Setup first.
    pause & exit /b 1
)

if not exist "!DIR!\.env" (
    echo [ERROR] .env is missing. Run APEX.bat ^> Setup first.
    pause & exit /b 1
)

:: Check BOT_TOKEN
powershell -NoProfile -Command ^
    "$env=(Get-Content '!DIR!\.env' -Raw); if($env -match 'BOT_TOKEN=\s*\r?\n'){Write-Host '[ERROR] BOT_TOKEN is empty - fill it in .env first!'; exit 1} else {exit 0}"
if errorlevel 1 pause & exit /b 1

if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"
if not exist "!DIR!\logs" mkdir "!DIR!\logs"

:: Kill stale/conflicting processes
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

:: Kill any python processes running main.py to avoid Telegram getUpdates conflict
echo [START] Clearing any conflicting python processes...
powershell -NoProfile -Command ^
    "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue"
timeout /t 2 /nobreak >nul

echo [START] Launching server (mode: all)...
start "Apex Lead Router Server" /min cmd /c ""!PY!" -u main.py all > "!DIR!\logs\server.log" 2>&1"

echo [START] Waiting for server to start (up to 15 sec)...
set "READY=0"
for /l %%i in (1,1,15) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul
        powershell -NoProfile -Command ^
            "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0} else {exit 1} } catch { exit 1 }" >nul 2>&1
        if not errorlevel 1 set "READY=1"
    )
)

if "!READY!"=="1" (
    echo [OK] Server is running and healthy.
    powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 3; Write-Host $r.Content } catch {}"
) else (
    echo [WARN] Server did not respond in 15 seconds.
    echo        Check logs\server.log for errors.
    echo.
    echo --- Last 15 lines of log ---
    if exist "!DIR!\logs\server.log" (
        powershell -NoProfile -Command "Get-Content '!DIR!\logs\server.log' -Tail 15"
    )
)

endlocal

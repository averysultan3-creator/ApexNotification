@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Apex Lead Router - Stop

for %%I in ("%~dp0..") do set "DIR=%%~fI"
if "!DIR:~-1!"=="\" set "DIR=!DIR:~0,-1!"
set "PID_FILE=!DIR!\runtime\server.pid"

cd /d "!DIR!"

set "STOPPED=0"

:: Kill by PID file
if exist "!PID_FILE!" (
    set /p PID=<"!PID_FILE!"
    if not "!PID!"=="" (
        tasklist /fi "pid eq !PID!" /fo csv /nh 2>nul | findstr /i "python" >nul 2>&1
        if not errorlevel 1 (
            echo [STOP] Stopping PID !PID!...
            taskkill /pid !PID! /t /f >nul 2>&1
            set "STOPPED=1"
        )
    )
    del "!PID_FILE!" >nul 2>&1
)

:: Also kill any remaining python main.py processes (cleanup after crash/conflict)
powershell -NoProfile -Command ^
    "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main.py*'} | ForEach-Object { Write-Host ('[STOP] Killing stray PID '+$_.Id); $_ | Stop-Process -Force -ErrorAction SilentlyContinue; $global:stopped=1 }" 2>nul
if not "!STOPPED!"=="1" (
    echo [OK] Server was already stopped or no running instance found.
) else (
    echo [OK] Server stopped.
)

endlocal
endlocal

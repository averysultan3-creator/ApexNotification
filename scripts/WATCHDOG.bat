@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0.."

set "HEALTH_URL=http://127.0.0.1:8000/health"
set "PID_FILE=runtime\server.pid"
set "LOG_DIR=logs"
set "RUNTIME_DIR=runtime"
set "WATCHDOG_LOG=%LOG_DIR%\watchdog.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"

echo [%date% %time%] Watchdog started. >> "%WATCHDOG_LOG%"

:loop
set "SERVER_OK=0"

if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    if defined PID (
        tasklist /FI "PID eq !PID!" /FI "IMAGENAME eq python.exe" 2>nul | findstr /R /C:"python.exe" >nul
        if errorlevel 1 (
            echo [%date% %time%] Stale PID !PID!, removing pid file. >> "%WATCHDOG_LOG%"
            del "%PID_FILE%" >nul 2>nul
        )
    )
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $r = Invoke-WebRequest -Uri '%HEALTH_URL%' -UseBasicParsing -TimeoutSec 8; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"

if not errorlevel 1 set "SERVER_OK=1"

if "%SERVER_OK%"=="1" (
    timeout /t 30 /nobreak >nul
    goto loop
)

echo [%date% %time%] Health check failed, starting server. >> "%WATCHDOG_LOG%"
call "%~dp0START_SERVER.bat" >> "%WATCHDOG_LOG%" 2>&1

timeout /t 60 /nobreak >nul
goto loop

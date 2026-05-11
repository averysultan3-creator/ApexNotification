@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

:: ============================================================
::  APEX_AUTOSTART.bat
::  Тихий запуск при загрузке Windows (через Task Scheduler).
::  НЕ требует взаимодействия — просто стартует сервер и ngrok.
:: ============================================================

set "DIR=%~dp0"
if "!DIR:~-1!"=="\" set "DIR=!DIR:~0,-1!"
set "PY=!DIR!\.venv\Scripts\python.exe"
set "LOG=!DIR!\logs\autostart.log"

cd /d "!DIR!"

if not exist "!DIR!\logs" mkdir "!DIR!\logs"
if not exist "!DIR!\runtime" mkdir "!DIR!\runtime"

echo [%date% %time%] Autostart triggered. >> "!LOG!"

:: Проверяем что сервер вообще настроен
if not exist "!PY!" (
    echo [%date% %time%] ERROR: .venv missing, run APEX.bat Setup first! >> "!LOG!"
    exit /b 1
)
if not exist "!DIR!\.env" (
    echo [%date% %time%] ERROR: .env missing, run APEX.bat Setup first! >> "!LOG!"
    exit /b 1
)

:: Убиваем старые процессы
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*main.py*'} | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1
timeout /t 2 /nobreak >nul

:: Запускаем сервер
start "Apex Lead Router" /min cmd /c ""!PY!" -u main.py all 2> "!DIR!\logs\stderr.log""
echo [%date% %time%] Server started. >> "!LOG!"

:: Ждём старта (до 20 сек)
set "READY=0"
for /l %%i in (1,1,20) do (
    if "!READY!"=="0" (
        timeout /t 1 /nobreak >nul
        powershell -NoProfile -Command "try{$r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2; if($r.StatusCode -eq 200){exit 0}else{exit 1}}catch{exit 1}" >nul 2>&1
        if not errorlevel 1 set "READY=1"
    )
)

if "!READY!"=="1" (
    echo [%date% %time%] Health check OK. >> "!LOG!"
) else (
    echo [%date% %time%] WARNING: Health check failed after 20 sec! Check logs\server.log >> "!LOG!"
)

:: Запускаем ngrok если есть
set "NGROK_EXE="
for /f "tokens=*" %%i in ('where ngrok 2^>nul') do set "NGROK_EXE=%%i"
if "!NGROK_EXE!"=="" if exist "!DIR!\ngrok.exe" set "NGROK_EXE=!DIR!\ngrok.exe"

if defined NGROK_EXE (
    :: Читаем порт из .env
    set "WEB_PORT=8000"
    for /f "tokens=2 delims==" %%v in ('findstr /i "WEB_PORT" "!DIR!\.env" 2^>nul') do set "WEB_PORT=%%v"
    set "WEB_PORT=!WEB_PORT: =!"

    :: Убиваем старый ngrok
    taskkill /im ngrok.exe /f >nul 2>&1
    timeout /t 1 /nobreak >nul

    start "ngrok" /min "!NGROK_EXE!" http !WEB_PORT!
    echo [%date% %time%] ngrok started on port !WEB_PORT!. >> "!LOG!"
    echo [%date% %time%] Check ngrok URL at http://127.0.0.1:4040 >> "!LOG!"
) else (
    echo [%date% %time%] ngrok not found, skipping. >> "!LOG!"
)

echo [%date% %time%] Autostart complete. >> "!LOG!"
endlocal

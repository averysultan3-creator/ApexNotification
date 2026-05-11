@echo off
chcp 65001 >nul 2>&1
setlocal
cd /d "%~dp0.."

call "%~dp0STOP_SERVER.bat"
if errorlevel 1 exit /b %errorlevel%

timeout /t 2 /nobreak >nul

call "%~dp0START_SERVER.bat"
endlocal

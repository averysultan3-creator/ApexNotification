@echo off
chcp 1251 >nul
setlocal enabledelayedexpansion

echo.
echo =====================================================
echo   Apex Lead Router
echo =====================================================

:: Батник лежит ВНУТРИ папки проекта
set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

:: =====================================================
:: ОБНОВЛЕНИЕ: если уже установлен -- только git pull
:: =====================================================
if exist ".venv\Scripts\python.exe" if exist ".env" (
    echo [UPDATE] Уже установлен. Обновляю код...
    git pull
    echo.
    echo [OK] Запускаю...
    echo      Остановить: Ctrl+C
    echo.
    call .venv\Scripts\activate.bat
    python main.py all
    echo.
    echo [!] Сервер остановился.
    pause
    exit /b 0
)

:: =====================================================
:: ПЕРВЫЙ ЗАПУСК -- полная установка
:: =====================================================
echo [SETUP] Первый запуск -- устанавливаю...
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Установи Python 3.10+ c python.org
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git не найден! Установи c git-scm.com
    pause & exit /b 1
)
echo [OK] Git найден.

git pull

echo [..] Создаю .venv...
python -m venv .venv
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Не удалось создать .venv
    pause & exit /b 1
)
echo [OK] .venv готово.

echo [..] Устанавливаю зависимости...
.venv\Scripts\python.exe -m pip install --upgrade pip -q
.venv\Scripts\pip.exe install -r requirements.txt -q
if not exist ".venv\Lib\site-packages\aiogram" (
    echo [ERROR] Зависимости не установились. Проверь интернет.
    pause & exit /b 1
)
echo [OK] Зависимости установлены.

:: =====================================================
:: .env создается ОДИН РАЗ.
:: При следующих обновлениях НЕ трогается.
:: Все настройки остаются как есть.
:: =====================================================
if not exist ".env" (
    echo [..] Определяю внешний IP сервера...
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Invoke-WebRequest -Uri https://api.ipify.org -UseBasicParsing).Content.Trim() 2>$null"') do set "SERVER_IP=%%i"
    if "!SERVER_IP!"=="" set "SERVER_IP=YOUR_SERVER_IP"
    echo [INFO] IP: !SERVER_IP!

    (
        echo # ================================================
        echo # Apex Lead Router -- настройки сервера
        echo # Файл создается один раз и не трогается при
        echo # обновлениях. Все настройки остаются.
        echo # ================================================
        echo.
        echo # --- Telegram ---
        echo BOT_TOKEN=8656058191:AAE0ervW58sqNV9tAqfhNjrixM_BIBfG788
        echo # Твой Telegram ID (узнать у @userinfobot):
        echo ADMIN_IDS=
        echo BOT_USERNAME=apexnotification_bot
        echo.
        echo # --- Сервер ---
        echo # http://IP:8000 или https://домен если есть SSL
        echo PUBLIC_BASE_URL=http://!SERVER_IP!:8000
        echo WEB_HOST=0.0.0.0
        echo WEB_PORT=8000
        echo.
        echo # --- База данных ---
        echo DATABASE_URL=sqlite+aiosqlite:///./apex_lead_router.db
        echo.
        echo # --- Facebook / Meta Pixel ---
        echo # Токен верификации вебхука (придумай любое слово):
        echo FACEBOOK_VERIFY_TOKEN=my_secret_token
        echo # App Secret из Meta Developer Console:
        echo FACEBOOK_APP_SECRET=
        echo # Page Access Token:
        echo FACEBOOK_PAGE_ACCESS_TOKEN=
        echo FACEBOOK_GRAPH_VERSION=v19.0
        echo.
        echo # --- Логирование ---
        echo LOG_LEVEL=INFO
    ) > .env

    echo.
    echo  .env создан. ЗАПОЛНИ ПЕРЕД ЗАПУСКОМ:
    echo  1. ADMIN_IDS= -- вставь свой Telegram ID
    echo  2. PUBLIC_BASE_URL уже стоит: !SERVER_IP!
    echo  3. FACEBOOK_VERIFY_TOKEN= -- придумай слово-секрет
    echo.
    echo  Нажми любую клавишу -- откроется блокнот...
    pause >nul
    notepad .env
    echo [OK] .env сохранен.
) else (
    echo [OK] .env уже есть -- настройки сохранены.
)

echo [..] Миграции БД...
.venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (
    echo [WARN] Помечаю ревизию 005...
    .venv\Scripts\python.exe -m alembic stamp 005 >nul 2>&1
)
echo [OK] База готова.

netsh advfirewall firewall show rule name="ApexLeadRouter-8000" >nul 2>&1
if errorlevel 1 (
    echo [..] Открываю порт 8000...
    netsh advfirewall firewall add rule name="ApexLeadRouter-8000" dir=in action=allow protocol=TCP localport=8000 >nul
    echo [OK] Порт 8000 открыт.
) else (
    echo [OK] Порт 8000 уже открыт.
)

echo.
echo =====================================================
echo   УСТАНОВКА ЗАВЕРШЕНА
echo.
echo   Что сделать в боте СРАЗУ после запуска:
echo   1. Напиши /start -- станешь super_admin
echo   2. Прелендинги -- Добавить -- slug: skyx-pl-1
echo   3. В SkyX_preleand/index.html вставь:
echo      var APEX_SERVER = "http://!SERVER_IP!:8000";
echo      затем git push для GitHub Pages
echo.
echo   Следующие запуски: батник видит .env и .venv
echo   и делает ТОЛЬКО git pull + перезапуск
echo =====================================================
echo.
echo   Запускаю бот + веб-сервер (Ctrl+C для остановки)
echo.

call .venv\Scripts\activate.bat
python main.py all

echo.
echo [!] Сервер остановился.
pause

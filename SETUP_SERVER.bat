@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   ApexNotification — SETUP SERVER (одна кнопка)
echo ============================================================
echo.

:: ════════════════════════════════════════════════════════════════════════════
:: 1. ПРОВЕРКИ
:: ════════════════════════════════════════════════════════════════════════════

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден!
    echo Установи Python 3.10+ c https://python.org
    echo При установке поставь галку "Add Python to PATH"
    pause & exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git не найден!
    echo Установи Git c https://git-scm.com/download/win
    pause & exit /b 1
)
echo [OK] Git найден.

:: ════════════════════════════════════════════════════════════════════════════
:: 2. СКАЧАТЬ ПРОЕКТ
:: ════════════════════════════════════════════════════════════════════════════

set "DEPLOY_DIR=%~dp0"
if "%DEPLOY_DIR:~-1%"=="\" set "DEPLOY_DIR=%DEPLOY_DIR:~0,-1%"
set "PROJECT_DIR=%DEPLOY_DIR%\ApexNotification"

if exist "%PROJECT_DIR%\.git" (
    echo [..] Проект уже есть, обновляю...
    cd /d "%PROJECT_DIR%"
    git pull >nul 2>&1
    echo [OK] Репозиторий обновлён.
    goto :SETUP_VENV
)

echo [..] Клонирую репозиторий...
git clone https://github.com/averysultan3-creator/ApexNotification.git "%PROJECT_DIR%" 2>&1

:: Проверяем по папке, а не по errorlevel (git пишет прогресс в stderr)
if not exist "%PROJECT_DIR%\main.py" (
    echo.
    echo [ERROR] Клонирование не удалось!
    echo Репозиторий приватный. Нужен GitHub аккаунт с доступом.
    echo Войди в GitHub через браузер или настрой Git Credential Manager.
    pause & exit /b 1
)
echo [OK] Репозиторий склонирован.

:SETUP_VENV
cd /d "%PROJECT_DIR%"

:: ════════════════════════════════════════════════════════════════════════════
:: 3. ВИРТУАЛЬНОЕ ОКРУЖЕНИЕ
:: ════════════════════════════════════════════════════════════════════════════

if exist ".venv\Scripts\python.exe" (
    echo [OK] .venv уже есть.
) else (
    echo [..] Создаю .venv...
    python -m venv .venv
    if not exist ".venv\Scripts\python.exe" (
        echo [ERROR] Не удалось создать .venv
        pause & exit /b 1
    )
    echo [OK] .venv создано.
)

:: ════════════════════════════════════════════════════════════════════════════
:: 4. ЗАВИСИМОСТИ
:: ════════════════════════════════════════════════════════════════════════════

echo [..] Обновляю pip...
.venv\Scripts\python.exe -m pip install --upgrade pip -q

echo [..] Устанавливаю зависимости (займёт ~30 сек)...
.venv\Scripts\pip.exe install -r requirements.txt -q
if not exist ".venv\Lib\site-packages\aiogram" (
    echo [ERROR] aiogram не установился. Проверь интернет.
    pause & exit /b 1
)
echo [OK] Зависимости установлены.

:: ════════════════════════════════════════════════════════════════════════════
:: 5. .env
:: ════════════════════════════════════════════════════════════════════════════

if not exist ".env" (
    echo [..] Создаю .env...
    (
        echo BOT_TOKEN=8656058191:AAE0ervW58sqNV9tAqfhNjrixM_BIBfG788
        echo ADMIN_IDS=
        echo BOT_USERNAME=apexnotification_bot
        echo DATABASE_URL=sqlite+aiosqlite:///./leadform_hub.db
        echo LOG_LEVEL=INFO
        echo PAGE_SIZE=10
    ) > .env
    echo [OK] .env создан.
) else (
    echo [OK] .env уже есть.
)

:: ════════════════════════════════════════════════════════════════════════════
:: 6. МИГРАЦИИ
:: ════════════════════════════════════════════════════════════════════════════

echo [..] Применяю миграции БД...
.venv\Scripts\python.exe -m alembic upgrade head >nul 2>&1
if exist "leadform_hub.db" (
    echo [OK] База данных готова.
) else (
    echo [WARN] База не создалась сразу, попробуй run_windows.bat — она создастся при старте.
)

:: ════════════════════════════════════════════════════════════════════════════
:: 7. СОЗДАТЬ run_windows.bat В ПАПКЕ ПРОЕКТА (удобный ярлык)
:: ════════════════════════════════════════════════════════════════════════════

:: Создаём START_BOT.bat прямо рядом с SETUP_SERVER.bat для удобства
(
    echo @echo off
    echo cd /d "%PROJECT_DIR%"
    echo call .venv\Scripts\activate.bat
    echo echo Бот запускается... Ctrl+C чтобы остановить.
    echo python main.py
    echo pause
) > "%DEPLOY_DIR%\START_BOT.bat"
echo [OK] START_BOT.bat создан рядом с этим файлом.

:: ════════════════════════════════════════════════════════════════════════════
:: ГОТОВО
:: ════════════════════════════════════════════════════════════════════════════

echo.
echo ============================================================
echo   ГОТОВО! Установка завершена.
echo ============================================================
echo.
echo   Запусти бота двойным кликом:
echo.
echo     %DEPLOY_DIR%\START_BOT.bat
echo.
echo   После запуска напиши /start боту в Telegram —
echo   ты автоматически станешь super_admin.
echo.
echo   Для обновлений: запусти SETUP_SERVER.bat снова.
echo.
pause


:: ════════════════════════════════════════════════════════════════════════════
:: 1. ПРОВЕРКИ
:: ════════════════════════════════════════════════════════════════════════════

:: Проверить Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден!
    echo.
    echo   Установи Python 3.10+ c https://python.org
    echo   При установке ОБЯЗАТЕЛЬНО поставь галку "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

:: Проверить Git
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git не найден!
    echo.
    echo   Установи Git c https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)
echo [OK] Git найден.

:: ════════════════════════════════════════════════════════════════════════════
:: 2. СКАЧАТЬ ПРОЕКТ
:: ════════════════════════════════════════════════════════════════════════════

:: Определить папку — там где лежит этот bat файл
set "DEPLOY_DIR=%~dp0"
:: Убрать завершающий слеш
if "%DEPLOY_DIR:~-1%"=="\" set "DEPLOY_DIR=%DEPLOY_DIR:~0,-1%"
set "PROJECT_DIR=%DEPLOY_DIR%\ApexNotification"

:: Если проект уже есть — просто обновить
if exist "%PROJECT_DIR%\.git" (
    echo [..] Проект уже есть — делаю git pull ...
    cd /d "%PROJECT_DIR%"
    git pull
    if errorlevel 1 (
        echo [ERROR] git pull не прошёл. Проверь интернет или конфликты.
        pause
        exit /b 1
    )
    echo [OK] Репозиторий обновлён.
    goto :SETUP_VENV
)

:: Иначе — клонировать
:: Репозиторий приватный. GitHub попросит логин/пароль или PAT.
:: Если на Windows уже настроен Credential Manager — всё пройдёт само.
echo [..] Клонирую репозиторий в %PROJECT_DIR% ...
git clone https://github.com/averysultan3-creator/ApexNotification.git "%PROJECT_DIR%"
if errorlevel 1 (
    echo.
    echo [ERROR] git clone не прошёл!
    echo.
    echo   Репозиторий приватный. Возможные решения:
    echo   1. Убедись что ты залогинен в Git (Windows Credential Manager)
    echo   2. Или введи свой GitHub логин/пароль когда Git попросит
    echo   3. Или используй Personal Access Token как пароль
    echo      (генерируется на: https://github.com/settings/tokens)
    echo.
    pause
    exit /b 1
)
echo [OK] Репозиторий склонирован.

:SETUP_VENV
cd /d "%PROJECT_DIR%"

:: ════════════════════════════════════════════════════════════════════════════
:: 3. ВИРТУАЛЬНОЕ ОКРУЖЕНИЕ
:: ════════════════════════════════════════════════════════════════════════════

if exist ".venv\Scripts\activate.bat" (
    echo [OK] .venv уже существует.
) else (
    echo [..] Создаю виртуальное окружение .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать .venv
        pause
        exit /b 1
    )
    echo [OK] .venv создано.
)

:: ════════════════════════════════════════════════════════════════════════════
:: 4. УСТАНОВКА ЗАВИСИМОСТЕЙ
:: ════════════════════════════════════════════════════════════════════════════

echo [..] Обновляю pip ...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet

echo [..] Устанавливаю зависимости ...
.venv\Scripts\pip.exe install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] pip install не прошёл. Проверь интернет и requirements.txt
    pause
    exit /b 1
)
echo [OK] Зависимости установлены.

:: ════════════════════════════════════════════════════════════════════════════
:: 5. СОЗДАТЬ .env С РЕАЛЬНЫМ ТОКЕНОМ
:: ════════════════════════════════════════════════════════════════════════════

if not exist ".env" (
    echo [..] Создаю .env ...
    (
        echo BOT_TOKEN=8656058191:AAE0ervW58sqNV9tAqfhNjrixM_BIBfG788
        echo ADMIN_IDS=
        echo BOT_USERNAME=your_bot_username_without_at
        echo DATABASE_URL=sqlite+aiosqlite:///./leadform_hub.db
        echo LOG_LEVEL=INFO
        echo PAGE_SIZE=10
    ) > .env
    echo [OK] .env создан.
) else (
    echo [OK] .env уже существует — не перезаписываю.
)

:: ════════════════════════════════════════════════════════════════════════════
:: 6. МИГРАЦИИ БАЗЫ ДАННЫХ
:: ════════════════════════════════════════════════════════════════════════════

echo [..] Применяю миграции базы данных ...
.venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (
    echo [WARN] Миграции не прошли — заполни .env и перезапусти этот файл.
) else (
    echo [OK] База данных готова.
)

:: ════════════════════════════════════════════════════════════════════════════
:: 7. ИТОГ
:: ════════════════════════════════════════════════════════════════════════════

echo.
echo ============================================================
echo   Установка завершена!
echo ============================================================
echo.
echo   ШАГ 1: Открой файл и заполни BOT_USERNAME:
echo.
echo     %PROJECT_DIR%\.env
echo.
echo   Замени строку:
echo     BOT_USERNAME=your_bot_username_without_at
echo   На:
echo     BOT_USERNAME=username_твоего_бота  (без @)
echo.
echo   ШАГ 2: Запусти бота:
echo.
echo     %PROJECT_DIR%\run_windows.bat
echo.
echo   ШАГ 3: Напиши /start боту — ты автоматически станешь super_admin.
echo.
echo   ШАГ 4: Обновления в будущем:
echo.
echo     %PROJECT_DIR%\update_windows.bat
echo.
pause

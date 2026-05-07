# setup_server.ps1
# ──────────────────────────────────────────────────────────────────────────────
# ApexNotification — New server setup script
# Usage:
#   powershell -ExecutionPolicy Bypass -File setup_server.ps1
#
# Run this from ANY empty folder where you want the project to live, e.g.:
#   mkdir D:\bots\ApexNotification
#   cd D:\bots\ApexNotification
#   powershell -ExecutionPolicy Bypass -File setup_server.ps1
# ──────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$GITHUB_REPO = "https://github.com/averysultan3-creator/ApexNotification.git"
$PROJECT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ApexNotification — Server Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ── Check Git ─────────────────────────────────────────────────────────────────
Write-Host "[..] Checking git ..." -NoNewline
try {
    $null = git --version 2>&1
    Write-Host " OK" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "[ERROR] git not found. Install Git from https://git-scm.com/download/win" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Check Python ──────────────────────────────────────────────────────────────
Write-Host "[..] Checking Python ..." -NoNewline
try {
    $pyver = python --version 2>&1
    Write-Host " $pyver OK" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "[ERROR] Python not found. Install Python 3.10+ from https://python.org" -ForegroundColor Red
    Write-Host "        Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# ── Clone or update repo ──────────────────────────────────────────────────────
if (Test-Path (Join-Path $PROJECT_DIR ".git")) {
    Write-Host "[..] Repository already cloned — pulling latest ..."
    Push-Location $PROJECT_DIR
    git pull
    Pop-Location
    Write-Host "[OK] Repository updated." -ForegroundColor Green
} elseif ((Get-ChildItem $PROJECT_DIR -Force | Where-Object { $_.Name -ne "setup_server.ps1" }).Count -eq 0) {
    # Empty folder (only this script) — clone into current directory
    Write-Host "[..] Cloning $GITHUB_REPO ..."
    $tmp = Join-Path $env:TEMP "apex_clone_tmp"
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
    git clone $GITHUB_REPO $tmp
    # Move everything from tmp to current dir
    Get-ChildItem $tmp -Force | Move-Item -Destination $PROJECT_DIR -Force
    Remove-Item $tmp -Recurse -Force
    Write-Host "[OK] Repository cloned." -ForegroundColor Green
} else {
    # Non-empty folder without .git — clone into subfolder
    $cloneTarget = Join-Path $PROJECT_DIR "ApexNotification"
    Write-Host "[..] Cloning into $cloneTarget ..."
    git clone $GITHUB_REPO $cloneTarget
    Set-Location $cloneTarget
    $PROJECT_DIR = $cloneTarget
    Write-Host "[OK] Repository cloned." -ForegroundColor Green
}

Push-Location $PROJECT_DIR

# ── Create virtual environment ────────────────────────────────────────────────
if (Test-Path ".venv") {
    Write-Host "[OK] Virtual environment already exists." -ForegroundColor Green
} else {
    Write-Host "[..] Creating virtual environment ..."
    python -m venv .venv
    Write-Host "[OK] Virtual environment created." -ForegroundColor Green
}

# ── Activate and install deps ─────────────────────────────────────────────────
Write-Host "[..] Installing dependencies ..."
& ".venv\Scripts\pip.exe" install --upgrade pip --quiet
& ".venv\Scripts\pip.exe" install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install failed." -ForegroundColor Red
    Pop-Location
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[OK] Dependencies installed." -ForegroundColor Green

# ── Create .env with real values ─────────────────────────────────────────────
# Repo is private — credentials stored here for zero-touch deployment.
# First /start → automatic super_admin. No ADMIN_IDS needed.
if (-not (Test-Path ".env")) {
    $envContent = @"
BOT_TOKEN=8656058191:AAE0ervW58sqNV9tAqfhNjrixM_BIBfG788
ADMIN_IDS=
BOT_USERNAME=your_bot_username_without_at
DATABASE_URL=sqlite+aiosqlite:///./leadform_hub.db
LOG_LEVEL=INFO
PAGE_SIZE=10
"@
    $envContent | Set-Content ".env" -Encoding UTF8
    Write-Host "[OK] .env создан с токеном бота." -ForegroundColor Green
    Write-Host "[!]  Осталось только заполнить BOT_USERNAME в .env" -ForegroundColor Yellow
} else {
    Write-Host "[OK] .env already exists." -ForegroundColor Green
}

# ── Apply migrations ──────────────────────────────────────────────────────────
Write-Host "[..] Applying database migrations ..."
try {
    & ".venv\Scripts\python.exe" -m alembic upgrade head 2>&1 | Out-Null
    Write-Host "[OK] Database ready." -ForegroundColor Green
} catch {
    Write-Host "[WARN] Alembic migration skipped (fill .env first, then run update_windows.bat)" -ForegroundColor Yellow
}

Pop-Location

# ── Final instructions ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. Открой .env и заполни BOT_USERNAME:" -ForegroundColor White
Write-Host "       notepad $PROJECT_DIR\.env" -ForegroundColor Gray
Write-Host ""
Write-Host "     BOT_USERNAME = username бота без @ (например: mybot)" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Запусти бот:" -ForegroundColor White
Write-Host "       $PROJECT_DIR\run_windows.bat" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Первый кто напишет /start боту — станет super_admin автоматически." -ForegroundColor Green
Write-Host ""
Write-Host "  4. Для будущих обновлений:" -ForegroundColor White
Write-Host "       $PROJECT_DIR\update_windows.bat" -ForegroundColor Gray
Write-Host ""
Read-Host "Press Enter to close"

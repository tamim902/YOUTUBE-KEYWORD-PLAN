# ==============================================================================
# KEYWORD STUDIO -- ADVANCED YOUTUBE SEO INTELLIGENCE
# Windows PowerShell Launcher
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "       KEYWORD STUDIO -- ADVANCED YOUTUBE SEO INTELLIGENCE                    " -ForegroundColor Cyan
Write-Host "                     PowerShell Launcher                                      " -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Environment Template Check
$EnvFile = Join-Path $ScriptDir ".env"
$EnvExample = Join-Path $ScriptDir ".env.example"
if (-not (Test-Path $EnvFile) -and (Test-Path $EnvExample)) {
    Write-Host "[INFO] First-time setup: Creating .env configuration from .env.example..." -ForegroundColor Yellow
    Copy-Item $EnvExample $EnvFile
    Write-Host "[INFO] Created .env successfully. You can edit it later with optional API keys." -ForegroundColor Green
    Write-Host ""
}

# 2. Virtual Environment Check
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$VenvStreamlit = Join-Path $ScriptDir ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[INFO] Virtual environment (.venv) not found. Checking system Python..." -ForegroundColor Yellow
    $SysPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $SysPython) {
        Write-Host "[ERROR] Python was not detected on your system PATH." -ForegroundColor Red
        Write-Host "To install Python 3.12 without administrator privileges, run:" -ForegroundColor Yellow
        Write-Host "  winget install --id Python.Python.3.12 --scope user" -ForegroundColor White
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "[INFO] Creating virtual environment (.venv)..." -ForegroundColor Green
    & python -m venv .venv
    Write-Host "[INFO] Installing dependencies from requirements.txt..." -ForegroundColor Green
    & "$ScriptDir\.venv\Scripts\pip.exe" install -r requirements.txt
}

if (-not (Test-Path $VenvStreamlit)) {
    Write-Host "[INFO] Installing Streamlit and locked dependencies..." -ForegroundColor Yellow
    & "$ScriptDir\.venv\Scripts\pip.exe" install -r requirements.txt
}

# 3. Launch Application
Write-Host "[INFO] Starting Keyword Studio server..." -ForegroundColor Green
Write-Host "[INFO] Local Web Address: http://localhost:8501" -ForegroundColor Cyan
Write-Host "[INFO] Note: Keep this PowerShell window open while using Keyword Studio." -ForegroundColor White
Write-Host "[INFO] Press Ctrl+C in this window to stop the server safely." -ForegroundColor Gray
Write-Host ""

# Open default browser after a short delay
Start-Process "http://localhost:8501"

& $VenvStreamlit run app.py --server.port 8501

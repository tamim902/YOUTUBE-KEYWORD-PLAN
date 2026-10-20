# YouTube Keyword Finder - PowerShell Launcher
$ErrorActionPreference = "Stop"

Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host "      YOUTUBE KEYWORD FINDER - POWERSHELL LAUNCHER      " -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Virtual Environment Check
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$VenvStreamlit = Join-Path $ScriptDir ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "[INFO] Virtual environment (.venv) not found. Checking system Python..." -ForegroundColor Yellow
    $SysPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $SysPython) {
        Write-Host "[ERROR] Python 3.12+ was not detected on your system PATH." -ForegroundColor Red
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
    Write-Host "[INFO] Installing Streamlit and dependencies..." -ForegroundColor Yellow
    & "$ScriptDir\.venv\Scripts\pip.exe" install -r requirements.txt
}

# 2. Launch Dashboard
Write-Host "[INFO] Launching YouTube Keyword Finder on http://localhost:8501..." -ForegroundColor Green
Write-Host "[INFO] Press Ctrl+C to terminate." -ForegroundColor Gray
Write-Host ""

& $VenvStreamlit run app.py --server.port 8501

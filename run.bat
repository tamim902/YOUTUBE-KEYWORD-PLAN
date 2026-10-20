@echo off
setlocal enabledelayedexpansion

title Keyword Studio - Advanced YouTube SEO Intelligence
echo ==============================================================================
echo       KEYWORD STUDIO -- ADVANCED YOUTUBE SEO INTELLIGENCE
echo                     Windows Desktop Launcher
echo ==============================================================================
echo.

cd /d "%~dp0"

:: 1. Copy .env.example to .env if .env does not exist
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] First-time setup: Creating .env configuration from .env.example...
        copy ".env.example" ".env" >nul
        echo [INFO] Created .env successfully. You can edit it later with optional API keys.
        echo.
    )
)

:: 2. Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment (.venv) not found. Checking system Python...
    where python >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python was not detected on your system PATH.
        echo.
        echo To install Python 3.12 without administrator privileges:
        echo   1. Open PowerShell and run:
        echo      winget install --id Python.Python.3.12 --scope user
        echo   2. Re-run this launcher once installation finishes.
        echo.
        pause
        exit /b 1
    )

    echo [INFO] Creating virtual environment (.venv)...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )

    echo [INFO] Installing dependencies from requirements.txt...
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\pip.exe install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install required packages.
        pause
        exit /b 1
    )
)

:: 3. Check if streamlit is present in venv
if not exist ".venv\Scripts\streamlit.exe" (
    echo [INFO] Installing Streamlit and locked dependencies...
    .\.venv\Scripts\pip.exe install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies into virtual environment.
        pause
        exit /b 1
    )
)

:: 4. Launch Application
echo [INFO] Starting Keyword Studio server...
echo [INFO] Local Web Address: http://localhost:8501
echo [INFO] Note: Keep this terminal window open while using Keyword Studio.
echo [INFO] Press Ctrl+C in this terminal window to stop the server safely.
echo.

:: Automatically open default browser after a 2-second delay in background
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8501"

.\.venv\Scripts\streamlit.exe run app.py --server.port 8501

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Streamlit exited with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

endlocal

@echo off
setlocal enabledelayedexpansion

title YouTube Keyword Finder Launcher
echo =========================================================
echo       YOUTUBE KEYWORD FINDER - WINDOWS LAUNCHER
echo =========================================================
echo.

cd /d "%~dp0"

:: 1. Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment (.venv) not found. Checking system Python...
    where python >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python 3.12+ was not detected on your system PATH.
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

:: 2. Check if streamlit is present in venv
if not exist ".venv\Scripts\streamlit.exe" (
    echo [INFO] Installing Streamlit and locked dependencies...
    .\.venv\Scripts\pip.exe install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Failed to install dependencies into virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Launch Application
echo [INFO] Starting YouTube Keyword Finder dashboard...
echo [INFO] Local Web Address: http://localhost:8501
echo [INFO] Press Ctrl+C in this terminal window to stop the server.
echo.

.\.venv\Scripts\streamlit.exe run app.py --server.port 8501

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Streamlit exited with error code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

endlocal

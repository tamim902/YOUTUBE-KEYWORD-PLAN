@echo off
setlocal
cd /d "%~dp0"

echo ==============================================================================
echo       KEYWORD STUDIO -- DATABASE BACKUP UTILITY
echo ==============================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\backup_data.py %*
) else (
    python scripts\backup_data.py %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Database backup encountered an error.
    pause
    exit /b %ERRORLEVEL%
)

echo.
pause
endlocal

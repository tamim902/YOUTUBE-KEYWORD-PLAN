@echo off
setlocal
cd /d "%~dp0"

echo ==============================================================================
echo       KEYWORD STUDIO -- DATABASE RESTORE UTILITY
echo ==============================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    .\.venv\Scripts\python.exe scripts\restore_data.py %*
) else (
    python scripts\restore_data.py %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Database restore encountered an error.
    pause
    exit /b %ERRORLEVEL%
)

echo.
pause
endlocal

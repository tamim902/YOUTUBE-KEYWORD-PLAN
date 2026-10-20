@echo off
title Push Keyword Studio to GitHub
echo ========================================================
echo        PUSHING KEYWORD STUDIO TO GITHUB (tamim902)
echo ========================================================
echo.
cd /d "%~dp0"

echo [1/2] Connecting to repository: https://github.com/tamim902/YOUTUBE-KEYWORD-PLAN.git
git remote set-url origin https://github.com/tamim902/YOUTUBE-KEYWORD-PLAN.git

echo.
echo [2/2] Uploading code to GitHub...
git push -u origin main

echo.
echo ========================================================
if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Your code is successfully uploaded to GitHub!
    echo You can now go to share.streamlit.io and deploy.
) else (
    echo [NOTE] If a browser popup opened, please click 'Sign in with your browser'.
)
echo ========================================================
echo.
pause

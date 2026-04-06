@echo off
title BoneQuest v2 — PageIndex RAG Platform
echo.
echo  ▄▄▄▄    ▒█████   ███▄    █ ▓█████   ██████   █    ██ ▓█████   ██████ ▄▄▄█████▓
echo ▓█████▄ ▒██▒  ██▒ ██ ▀█   █ ▓█   ▀ ▒██    ▒   ██  ▓██▒▓█   ▀ ▒██    ▒ ▓  ██▒ ▓▒
echo ▒██▒ ▄██▒██░  ██▒▓██  ▀█ ██▒▒███   ░ ▓██▄    ▓██  ▒██░▒███   ░ ▓██▄   ▒ ▓██░ ▒░
echo ▒██░█▀  ▒██   ██░▓██▒  ▐▌██▒▒▓█  ▄   ▒   ██▒ ▓▓█  ░██░▒▓█  ▄   ▒   ██▒░ ▓██▓ ░
echo ░▓█  ▀█▓░ ████▓▒░▒██░   ▓██░░▒████▒▒██████▒▒ ▒▒█████▓ ░▒████▒▒██████▒▒  ▒██▒ ░
echo.
echo  [v2.0] PageIndex-Powered Orthopaedic RAG Platform
echo  ================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Install Python deps if needed
if not exist "backend\__pycache__" (
    echo [SETUP] Installing Python dependencies...
    pip install -r requirements.txt
    echo.
)

:: Install Node deps if needed
if not exist "node_modules" (
    echo [SETUP] Installing Node dependencies...
    npm install
    echo.
)

echo [START] Launching BoneQuest v2...
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo.

npx concurrently -n "FRONTEND,BACKEND" -c "magenta,cyan" "npx vite" "cd backend && python -m uvicorn main:app --reload --port 8000"

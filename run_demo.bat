@echo off
title Edge-AI Food Spoilage Smart Storage System
echo ======================================================================
echo   Edge-AI Multi-Sensor Food Spoilage & Smart Storage System
echo ======================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ from python.org and check "Add Python to PATH".
    pause
    exit /b
)

echo [1/3] Checking dependencies...
pip install -r requirements.txt --quiet

echo [2/3] Opening Web Dashboard at http://127.0.0.1:8000/ ...
start "" http://127.0.0.1:8000/

echo [3/3] Starting FastAPI Server on port 8000...
echo.
echo ======================================================================
echo  Dashboard: http://127.0.0.1:8000/
echo  Swagger API Docs: http://127.0.0.1:8000/docs
echo.
echo  * To connect ESP32 hardware:
echo    Option A: Click "Connect USB ESP32" on the website (Chrome/Edge).
echo    Option B: In a separate terminal, run: python serial_bridge.py
echo ======================================================================
echo.
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause

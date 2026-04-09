@echo off
REM ================================================================
REM  start.bat  –  One-click startup for Keystroke Logging Demo
REM  Educational / Ethical Use Only
REM ================================================================

title Keystroke Logging Demonstration System

echo.
echo  ================================================================
echo   KEYSTROKE LOGGING DEMONSTRATION SYSTEM
echo   FOR EDUCATIONAL ^& ETHICAL CYBERSECURITY USE ONLY
echo  ================================================================
echo.

REM Navigate to backend folder
cd /d "%~dp0backend"

REM Check Python is installed
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from:
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Install dependencies if needed
echo [*] Checking dependencies...
pip install -r requirements.txt --quiet

echo.
echo [*] Starting FastAPI backend on http://localhost:8000 ...
echo [*] Default password: demo1234
echo [*] Open frontend\index.html in your browser
echo.
echo  Press Ctrl+C to stop the server.
echo  ================================================================
echo.

REM Start the server
python main.py

pause

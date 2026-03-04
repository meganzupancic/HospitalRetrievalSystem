@echo off
REM Quick start script for Whisper Test System
REM This script activates the virtual environment and runs the test

setlocal enabledelayedexpansion

echo ============================================================
echo         WHISPER SPEECH TEST SYSTEM - QUICK START
echo ============================================================
echo.

REM Get the parent directory (Hospital Retrieval System)
cd /d "%~dp0.."

REM Check if venv exists
if not exist "venv" (
    echo ERROR: Virtual environment not found!
    echo Please ensure you have activated the virtual environment first.
    echo Run: .\venv\Scripts\Activate.ps1
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Navigate back to test folder
cd /d "%~dp0"

echo.
echo Virtual environment activated successfully!
echo.
echo Starting test application...
echo ============================================================
echo.
echo 🌐 After startup, navigate to: http://127.0.0.1:5000
echo.
echo Instructions:
echo   1. The script will show numbered tests
echo   2. After "Recording..." prompt, speak your test phrase
echo   3. Press Enter after each test to continue
echo   4. Type 'q' to quit
echo.
echo ============================================================
echo.

REM Run the test
python whisper_test.py

pause

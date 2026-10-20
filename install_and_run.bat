@echo off
echo ===================================
echo  VideoCut - Setup
echo ===================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install PyQt6 opencv-python numpy --quiet

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies.
    echo Try manually: pip install PyQt6 opencv-python numpy
    pause
    exit /b 1
)

echo.
echo [2/3] Dependencies installed successfully!
echo.
echo [3/3] Starting VideoCut...
echo.

cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo App exited with an error. Check above for details.
    pause
)

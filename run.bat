@echo off
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo Failed to start. Run install_and_run.bat first to install dependencies.
    pause
)

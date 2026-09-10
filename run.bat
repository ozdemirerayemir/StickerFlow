@echo off
setlocal enabledelayedexpansion
title StickerFlow Launcher

:: Switch to script's directory
cd /d "%~dp0"

echo ==================================================
echo   StickerFlow - Quick Launcher
echo ==================================================
echo.

:: 1. Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 was not found on your system!
    echo Please install Python 3.10 or newer from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Set up virtual environment if missing
if not exist "%~dp0.venv" (
    echo [1/3] Setting up virtual environment...
    python -m venv "%~dp0.venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: 3. Activate virtual environment
call ".venv\Scripts\activate.bat"

:: 4. Verify/install dependencies
echo [2/3] Checking dependencies...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: 5. Launch Application
echo [3/3] Launching StickerFlow...
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"
) else (
    start "" pythonw "%~dp0main.py" 2>nul || start "" python "%~dp0main.py"
)
exit /b 0

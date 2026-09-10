@echo off
REM StickerFlow Windows Build Script
REM Requires: Python 3.10+, pip
REM Usage: build_scripts\build_windows.bat

setlocal enabledelayedexpansion

echo ============================================
echo  StickerFlow — Windows Build
echo ============================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ and add it to PATH.
    exit /b 1
)

REM Create / activate virtual environment
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Run tests
echo Running tests...
python -m pytest tests/ -v
if errorlevel 1 (
    echo ERROR: Tests failed. Aborting build.
    exit /b 1
)

REM PyInstaller build
echo Building with PyInstaller...
pyinstaller ^
    --onedir ^
    --windowed ^
    --name StickerFlow ^
    --icon assets\icon.ico ^
    --add-data "ui;ui" ^
    --add-data "docs;docs" ^
    --hidden-import customtkinter ^
    --hidden-import PIL ^
    --hidden-import rembg ^
    --hidden-import onnxruntime ^
    main.py

echo ============================================
echo  Build complete: dist\StickerFlow\
echo ============================================
echo NOTE: FFmpeg must be installed separately by the end user.
echo NOTE: rembg model will download on first use (requires internet).
echo NOTE: Antivirus software may flag the executable as a false positive.
echo ============================================

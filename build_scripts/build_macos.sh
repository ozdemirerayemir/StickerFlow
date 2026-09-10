#!/usr/bin/env bash
# StickerFlow macOS Build Script
# Requires: Python 3.10+, pip, Homebrew (optional for FFmpeg)
# Usage: bash build_scripts/build_macos.sh

set -euo pipefail

echo "============================================"
echo " StickerFlow — macOS Build"
echo "============================================"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10+ from https://python.org"
    exit 1
fi

# Create / activate virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run tests
echo "Running tests..."
python -m pytest tests/ -v

# PyInstaller build
echo "Building with PyInstaller..."
pyinstaller \
    --onedir \
    --windowed \
    --name StickerFlow \
    --add-data "ui:ui" \
    --add-data "docs:docs" \
    --hidden-import customtkinter \
    --hidden-import PIL \
    --hidden-import rembg \
    --hidden-import onnxruntime \
    main.py

echo "============================================"
echo " Build complete: dist/StickerFlow/"
echo "============================================"
echo "NOTE: FFmpeg must be installed separately (brew install ffmpeg)."
echo "NOTE: rembg model downloads on first use (~170 MB)."
echo "NOTE: You may need to sign the .app bundle for Gatekeeper:"
echo "      codesign --deep --force --sign - dist/StickerFlow.app"
echo "============================================"

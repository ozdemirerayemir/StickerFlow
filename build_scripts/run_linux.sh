#!/usr/bin/env bash
# StickerFlow Linux Run Script
# Requires: Python 3.10+, pip, FFmpeg
# Usage:
#   bash build_scripts/run_linux.sh          — run the app
#   bash build_scripts/run_linux.sh --test   — run tests before starting

set -euo pipefail

echo "============================================"
echo " StickerFlow — Linux"
echo "============================================"

RUN_TESTS=false
if [[ "${1:-}" == "--test" ]]; then
    RUN_TESTS=true
fi

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found."
    echo "Install with: sudo apt install python3 python3-pip python3-venv"
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

if $RUN_TESTS; then
    echo "Running tests..."
    python -m pytest tests/ -v
fi

# Check FFmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "WARNING: FFmpeg not found in PATH."
    echo "Video features will be disabled until FFmpeg is installed."
    echo "Install with: sudo apt install ffmpeg"
fi

echo "Starting StickerFlow..."
python main.py

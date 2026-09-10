#!/usr/bin/env bash
set -e

# Change to script directory
cd "$(dirname "$0")"

echo "=================================================="
echo "  StickerFlow - Quick Launcher"
echo "=================================================="
echo ""

# 1. Check Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "[ERROR] Python 3 was not found on your system!"
    echo "Please install Python 3.10 or newer."
    exit 1
fi

# 2. Virtual environment
if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment (.venv)..."
    $PYTHON_CMD -m venv .venv
fi

# 3. Activate
source .venv/bin/activate

# 4. Dependencies
echo "[2/3] Checking dependencies..."
pip install -r requirements.txt --quiet

# 5. Launch
echo "[3/3] Launching StickerFlow..."
echo ""
python main.py

#!/bin/bash

# =========================================================================
# GPLINKS AFFILIATE FORWARDER - LINUX LAUNCHER
# =========================================================================

# Get the script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================================="
echo "            ⚡ GPLINKS AFFILIATE FORWARDER - LINUX LAUNCHER ⚡"
echo "========================================================================="

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in PATH!"
    echo "Please install Python 3.9+ and try again."
    exit 1
fi

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating virtual environment (.venv)..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "[WARNING] Failed to create virtual environment. Running globally..."
    fi
fi

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    echo "[INFO] Activating virtual environment..."
    source .venv/bin/activate
fi

# Install/Update dependencies
echo "[INFO] Installing/updating package dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Dependency installation failed! Check internet connection."
    exit 1
fi

# Start Server
echo "[SUCCESS] Launching FastAPI Control Center on Port 8000..."
python3 web_dashboard.py

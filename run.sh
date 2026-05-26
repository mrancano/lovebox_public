#!/bin/bash
# run.sh - Start the Lovebox listener

# Exit immediately if a command fails
set -e

# Define variables
APP_DIR="$HOME/src/lovebox"

echo "=== Starting Lovebox Listener ==="
if [ ! -d "$APP_DIR" ]; then
    echo "App directory not found at $APP_DIR. Run setup.sh first."
    exit 1
fi

cd "$APP_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run setup.sh first."
    exit 1
fi

# Activate venv and run the listener
source .venv/bin/activate
python listener_v2.py

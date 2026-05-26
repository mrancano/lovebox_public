#!/bin/bash
# setup.sh - Run this to provision the Lovebox

# Exit immediately if a command fails
set -e 

# Define variables
REPO_URL="https://github.com/mrancano/lovebox_public.git"
APP_DIR="$HOME/src/lovebox"

echo "=== Updating System OS ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== Installing Dependencies ==="
sudo apt-get install -y git python3-venv python3-pip

echo "=== Setting up Lovebox Directory ==="
if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO_URL" "$APP_DIR"
else
    echo "Directory already exists. Pulling latest changes..."
    cd "$APP_DIR" && git pull
fi

echo "=== Creating Virtual Environment ==="
cd "$APP_DIR"
python3 -m venv .venv

echo "=== Installing Python Requirements ==="
# Use the pip executable directly from the venv to ensure it installs there
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo "=== Activating SPI === "
sudo raspi-config nonint do_spi 0

echo "=== Setup Complete! Rebooting ==="
sudo reboot
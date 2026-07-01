#!/bin/bash
# bootstrap.sh — Disaster recovery: turn a blank Pi into a working Lovebox.
#
# Keep this file on YOUR LAPTOP. When you visit your girlfriend with a
# fresh SD card:
#
#   1. Flash Raspberry Pi OS Lite with the Pi Imager
#      (set hostname "lovebox", enable SSH, pre-configure a temp WiFi)
#   2. Boot the Pi, SSH in
#   3. scp bootstrap.sh pi@lovebox:~/
#   4. ssh pi@lovebox
#   5. bash bootstrap.sh
#   6. Done. Reboot. The Lovebox is ready.
#
# This script is self-contained — it installs git, clones the repo,
# then delegates to the repo's setup.sh and wifi_provision.sh.

set -e

REPO_URL="https://github.com/mrancano/lovebox_public.git"
APP_DIR="$HOME/src/lovebox"

echo "============================================"
echo "  Lovebox Bootstrap — Fresh Pi Setup"
echo "============================================"
echo ""

# ── 1. Install git ──────────────────────────────────────────────
if ! command -v git &> /dev/null; then
    echo "[1/3] Installing git..."
    sudo apt-get update -qq
    sudo apt-get install -y git
else
    echo "[1/3] git already installed."
fi

# ── 2. Clone the repository ─────────────────────────────────────
echo "[2/3] Cloning lovebox repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "      Repo already exists — pulling latest."
    cd "$APP_DIR" && git pull
else
    rm -rf "$APP_DIR"  # Clean slate if partial clone exists
    git clone "$REPO_URL" "$APP_DIR"
fi

# ── 3. Run setup + provisioning ─────────────────────────────────
echo "[3/3] Running setup.sh (dependencies, audio, venv)..."
cd "$APP_DIR"
bash setup.sh

echo ""
echo "      Running wifi_provision.sh (RaspAP, systemd, sudoers)..."
bash wifi_provision.sh

echo ""
echo "============================================"
echo "  Bootstrap complete!"
echo "============================================"
echo ""
echo "Next steps (optional):"
echo "  • Create .env with TELEGRAM_KEY and MY_CHAT_ID"
echo "    echo 'TELEGRAM_KEY=...' > $APP_DIR/.env"
echo "    echo 'MY_CHAT_ID=...'   >> $APP_DIR/.env"
echo ""
echo "  • Reboot: sudo reboot"
echo ""
echo "After reboot, the listener starts automatically."
echo "No known WiFi? → 'Lovebox Setup' hotspot appears."
echo ""

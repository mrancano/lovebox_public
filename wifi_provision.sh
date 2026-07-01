#!/bin/bash
# wifi_provision.sh — Install RaspAP for headless WiFi provisioning.
# Idempotent: safe to run multiple times. Already-installed steps are skipped.
#
# What this does:
# 1. Installs RaspAP (lightweight AP + captive portal)
# 2. Configures the AP SSID to "Lovebox Setup"
# 3. Grants passwordless sudo for modprobe (I2S audio reload)
# 4. Installs & enables the lovebox systemd service
# 5. On boot: if no known WiFi is found, AP mode activates
# 6. Girlfriend connects phone to "Lovebox Setup" WiFi → picks her WiFi → reboots

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== WiFi Provisioning for Lovebox ==="

# ── Step 1: RaspAP ──────────────────────────────────────────────
if [ -f /etc/hostapd/hostapd.conf ]; then
    echo "[SKIP] RaspAP already installed (hostapd.conf exists)."
else
    echo "[INSTALL] RaspAP (WiFi hotspot + captive portal)..."
    curl -sL https://install.raspap.com | bash -s -- --yes --openvpn-disable --adblock-disable
fi

# ── Step 2: AP SSID ─────────────────────────────────────────────
echo "[CONFIG] Setting AP name to 'Lovebox Setup'..."
sudo sed -i 's/^ssid=.*/ssid=Lovebox Setup/' /etc/hostapd/hostapd.conf 2>/dev/null || true

RASPAP_CONFIG="/etc/raspap/hostapd.ini"
if [ -f "$RASPAP_CONFIG" ]; then
    sudo sed -i 's/^ssid[[:space:]]*=.*/ssid = Lovebox Setup/' "$RASPAP_CONFIG" 2>/dev/null || true
fi

# ── Step 3: Passwordless sudo for modprobe ──────────────────────
SUDOERS_FILE="/etc/sudoers.d/lovebox"
if [ -f "$SUDOERS_FILE" ]; then
    echo "[SKIP] Sudoers drop-in already exists."
else
    echo "[INSTALL] Passwordless modprobe (for I2S audio reload)..."
    echo "mrancano ALL=(ALL) NOPASSWD: /usr/sbin/modprobe" | sudo tee "$SUDOERS_FILE" > /dev/null
    sudo chmod 440 "$SUDOERS_FILE"
fi

# ── Step 4: systemd service ────────────────────────────────────
SERVICE_FILE="$SCRIPT_DIR/lovebox.service"
if [ -f "$SERVICE_FILE" ]; then
    sudo cp "$SERVICE_FILE" /etc/systemd/system/lovebox.service
    sudo systemctl daemon-reload
    sudo systemctl enable lovebox.service
    echo "[INSTALL] systemd service installed & enabled."
else
    echo "[WARN] lovebox.service not found in $SCRIPT_DIR — skipping."
fi

echo ""
echo "=== Done! ==="
echo ""
echo "How it works for your girlfriend:"
echo "  1. She plugs in the Lovebox at her apartment"
echo "  2. Pi boots → no known WiFi → starts 'Lovebox Setup' hotspot"
echo "  3. She connects her phone to 'Lovebox Setup' WiFi"
echo "  4. A captive portal opens (or she goes to http://10.3.141.1)"
echo "  5. She picks her apartment WiFi, enters the password"
echo "  6. Pi reboots → connects to her WiFi → Lovebox starts!"
echo ""
echo "Default RaspAP admin: username=admin, password=secret"
echo ""
echo "Reboot with: sudo reboot"

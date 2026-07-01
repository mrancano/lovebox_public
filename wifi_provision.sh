#!/bin/bash
# wifi_provision.sh — Install RaspAP for headless WiFi provisioning
# Run this ONCE on the Pi before giving the Lovebox to your girlfriend.
#
# What this does:
# 1. Installs RaspAP (lightweight AP + captive portal)
# 2. Configures the AP SSID to "Lovebox Setup"
# 3. On boot: if no known WiFi is found within ~60s, AP mode activates
# 4. Girlfriend connects phone to "Lovebox Setup" WiFi
# 5. Portal shows available networks → she picks hers + enters password
# 6. Pi reboots → connects to her WiFi → Lovebox listener auto-starts

set -e

echo "=== Installing RaspAP (WiFi Provisioning) ==="

# Install RaspAP with minimal extras (no OpenVPN, no ad blocking)
curl -sL https://install.raspap.com | bash -s -- --yes --openvpn-disable --adblock-disable

echo ""
echo "=== Configuring AP name to 'Lovebox Setup' ==="

# RaspAP stores hotspot SSID in /etc/hostapd/hostapd.conf
# Default is "raspi-webgui", change to "Lovebox Setup"
sudo sed -i 's/^ssid=.*/ssid=Lovebox Setup/' /etc/hostapd/hostapd.conf 2>/dev/null || true

# Also update RaspAP's config so the web UI shows the correct name
RASPAP_CONFIG="/etc/raspap/hostapd.ini"
if [ -f "$RASPAP_CONFIG" ]; then
    sudo sed -i 's/^ssid[[:space:]]*=.*/ssid = Lovebox Setup/' "$RASPAP_CONFIG" 2>/dev/null || true
fi

echo ""
echo "=== Allowing passwordless modprobe (I2S audio reload) ==="
# display_controller.py runs sudo modprobe to reload I2S after SPI use.
# The systemd service has no TTY, so sudo needs passwordless access.
echo "mrancano ALL=(ALL) NOPASSWD: /usr/sbin/modprobe" | sudo tee /etc/sudoers.d/lovebox > /dev/null
sudo chmod 440 /etc/sudoers.d/lovebox
echo "Sudoers drop-in created."

echo ""
echo "=== Setting up Lovebox systemd service (auto-start on boot) ==="

# Copy the service file and enable it
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/lovebox.service"

if [ -f "$SERVICE_FILE" ]; then
    sudo cp "$SERVICE_FILE" /etc/systemd/system/lovebox.service
    sudo systemctl daemon-reload
    sudo systemctl enable lovebox.service
    echo "Systemd service installed and enabled."
else
    echo "WARNING: lovebox.service not found in $SCRIPT_DIR"
    echo "Create it manually or re-clone the repo."
fi

echo ""
echo "=== WiFi Provisioning Setup Complete! ==="
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
echo "Change this at http://10.3.141.1 after connecting."
echo ""
echo "Reboot now? (y/n)"
read -r REPLY
if [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ]; then
    sudo reboot
fi

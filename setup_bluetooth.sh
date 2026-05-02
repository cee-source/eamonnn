#!/usr/bin/env bash
# Pair and connect a Bluetooth speaker to the Raspberry Pi 5.
# Run once:  bash setup_bluetooth.sh

set -e

echo "=== Bluetooth Speaker Setup ==="
echo ""

# Make sure required packages are installed
echo "[1/4] Checking packages..."
sudo apt-get install -y --quiet pulseaudio pulseaudio-module-bluetooth bluez 2>&1 | grep -E "^(Reading|Get|Unpacking|Setting|Processing)" || true
echo "      Packages OK."

# Enable and start Bluetooth service
echo "[2/4] Starting Bluetooth service..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Make PulseAudio aware of Bluetooth
echo "[3/4] Loading PulseAudio Bluetooth module..."
pactl load-module module-bluetooth-discover 2>/dev/null || true

echo ""
echo "[4/4] Starting Bluetooth scan — turn your speaker on and put it in pairing mode."
echo "      Scanning for 15 seconds..."
echo ""

# Scan and print found devices
bluetoothctl --timeout 15 scan on 2>/dev/null | grep "NEW" | awk '{print $4, $5, $6}' | sort -u || true

echo ""
echo "---"
echo "Enter the MAC address of your speaker (format: AA:BB:CC:DD:EE:FF)"
read -rp "MAC address: " MAC

if [[ -z "$MAC" ]]; then
    echo "No address entered. Exiting."
    exit 1
fi

echo ""
echo "Pairing with $MAC ..."
bluetoothctl pair "$MAC"
bluetoothctl trust "$MAC"
bluetoothctl connect "$MAC"

echo ""
echo "=== Done! ==="
echo "Your speaker ($MAC) is paired and trusted."
echo ""
echo "Test sound:  paplay meow.wav"
echo ""
echo "To reconnect after a reboot the speaker will reconnect automatically"
echo "because we trusted it.  If it does not, run:"
echo "  bluetoothctl connect $MAC"

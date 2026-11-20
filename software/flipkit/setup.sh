#!/bin/bash
set -e
echo "[flipkit] Installing dependencies..."
sudo apt-get update -qq
sudo apt-get install -y python3-flask python3-pip hostapd dnsmasq iw wireless-tools net-tools nginx

pip3 install bleak flask flask-cors --break-system-packages

# Allow flask to call iw/hostapd/dnsmasq without password prompt
SUDOERS_LINE="$USER ALL=(ALL) NOPASSWD: /sbin/iw, /sbin/ip, /usr/sbin/hostapd, /usr/sbin/dnsmasq, /bin/pkill, /sbin/iptables"
echo "$SUDOERS_LINE" | sudo tee /etc/sudoers.d/flipkit > /dev/null
sudo chmod 440 /etc/sudoers.d/flipkit

echo "[flipkit] Done. Run: python3 app.py"

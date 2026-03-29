#!/bin/bash
# PiFlip system setup script
# Run as root: sudo bash setup.sh
# Configures SPI, I2C, USB HID gadget, pigpiod service, and Python deps.

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

if [[ $EUID -ne 0 ]]; then
    error "Run as root: sudo bash setup.sh"
    exit 1
fi

info "=== PiFlip Setup ==="
info "Checking Raspberry Pi model..."
PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null || echo "Unknown")
info "Model: $PI_MODEL"

# -----------------------------------------------------------------------
# 1. Enable SPI and I2C
# -----------------------------------------------------------------------
info "Enabling SPI and I2C interfaces..."
raspi-config nonint do_spi 0    2>/dev/null || warn "raspi-config SPI failed (may already be enabled)"
raspi-config nonint do_i2c 0    2>/dev/null || warn "raspi-config I2C failed (may already be enabled)"

# Verify overlays are in /boot/config.txt (or /boot/firmware/config.txt on newer OS)
BOOT_CONFIG="/boot/config.txt"
[[ -f "/boot/firmware/config.txt" ]] && BOOT_CONFIG="/boot/firmware/config.txt"

grep -q "^dtparam=spi=on"  "$BOOT_CONFIG" || echo "dtparam=spi=on"  >> "$BOOT_CONFIG"
grep -q "^dtparam=i2c_arm=on" "$BOOT_CONFIG" || echo "dtparam=i2c_arm=on" >> "$BOOT_CONFIG"
info "SPI and I2C overlays confirmed in $BOOT_CONFIG"

# -----------------------------------------------------------------------
# 2. Install system packages
# -----------------------------------------------------------------------
info "Installing system packages..."
apt-get update -qq
apt-get install -y -qq \
    python3-pip python3-dev python3-venv \
    pigpio python3-pigpio \
    i2c-tools \
    libgpiod2 \
    fonts-dejavu \
    git \
    rtl-sdr \
    alsa-utils

# -----------------------------------------------------------------------
# 3. Enable and start pigpiod
# -----------------------------------------------------------------------
info "Configuring pigpiod service..."
systemctl enable pigpiod
systemctl start pigpiod
sleep 1
if systemctl is-active --quiet pigpiod; then
    info "pigpiod is running"
else
    warn "pigpiod failed to start — check: journalctl -u pigpiod"
fi

# -----------------------------------------------------------------------
# 4. Install rpitx (voice radio transmitter via GPIO4)
# -----------------------------------------------------------------------
info "Installing rpitx (GPIO FM/AM/SSB transmitter)..."
apt-get install -y -qq ffmpeg sox libsndfile1-dev

RPITX_DIR="/opt/rpitx"
if [[ ! -d "$RPITX_DIR" ]]; then
    git clone https://github.com/F5OEO/rpitx "$RPITX_DIR"
    cd "$RPITX_DIR" && bash install.sh
    ln -sf "$RPITX_DIR/rpitx" /usr/local/bin/rpitx
    info "rpitx installed"
else
    info "rpitx already installed at $RPITX_DIR"
fi

# -----------------------------------------------------------------------
# 5. Install Python dependencies
# -----------------------------------------------------------------------
info "Installing Python dependencies..."
pip3 install -r /home/user/eamonnn/requirements.txt

# -----------------------------------------------------------------------
# 5. Bad USB HID gadget (Pi Zero 2W only via OTG)
# -----------------------------------------------------------------------
info "Configuring USB HID gadget..."

PI_IS_ZERO=false
echo "$PI_MODEL" | grep -qi "Zero" && PI_IS_ZERO=true

if $PI_IS_ZERO; then
    # Enable dwc2 overlay
    grep -q "^dtoverlay=dwc2" "$BOOT_CONFIG" || echo "dtoverlay=dwc2" >> "$BOOT_CONFIG"

    MODULES_FILE="/etc/modules"
    grep -q "^dwc2"       "$MODULES_FILE" || echo "dwc2"       >> "$MODULES_FILE"
    grep -q "^libcomposite" "$MODULES_FILE" || echo "libcomposite" >> "$MODULES_FILE"

    # Create HID gadget setup script
    cat > /usr/local/bin/piflip-hid-gadget.sh << 'GADGET_EOF'
#!/bin/bash
# Configure USB HID keyboard gadget via configfs
# Run at boot via rc.local or a systemd service

modprobe libcomposite

GADGET_DIR=/sys/kernel/config/usb_gadget/piflip
mkdir -p "$GADGET_DIR"
cd "$GADGET_DIR"

echo 0x1d6b > idVendor     # Linux Foundation
echo 0x0104 > idProduct    # Multifunction Composite Gadget
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB

mkdir -p strings/0x409
echo "deadbeef01234567" > strings/0x409/serialnumber
echo "PiFlip"           > strings/0x409/manufacturer
echo "PiFlip HID"       > strings/0x409/product

mkdir -p configs/c.1/strings/0x409
echo "HID Keyboard" > configs/c.1/strings/0x409/configuration
echo 250            > configs/c.1/MaxPower

# HID function
mkdir -p functions/hid.usb0
echo 1    > functions/hid.usb0/protocol   # Keyboard
echo 1    > functions/hid.usb0/subclass   # Boot interface
echo 8    > functions/hid.usb0/report_length

# Standard boot keyboard HID descriptor
printf '\x05\x01\x09\x06\xa1\x01\x05\x07\x19\xe0\x29\xe7\x15\x00\x25\x01\x75\x01\x95\x08\x81\x02\x95\x01\x75\x08\x81\x03\x95\x05\x75\x01\x05\x08\x19\x01\x29\x05\x91\x02\x95\x01\x75\x03\x91\x03\x95\x06\x75\x08\x15\x00\x25\x65\x05\x07\x19\x00\x29\x65\x81\x00\xc0' \
    > functions/hid.usb0/report_desc

ln -sf functions/hid.usb0 configs/c.1/

# Bind to UDC
UDC=$(ls /sys/class/udc | head -1)
if [[ -n "$UDC" ]]; then
    echo "$UDC" > UDC
    echo "HID gadget bound to $UDC"
else
    echo "No UDC found — is USB cable connected to OTG port?"
fi
GADGET_EOF

    chmod +x /usr/local/bin/piflip-hid-gadget.sh

    # Create systemd service for HID gadget
    cat > /etc/systemd/system/piflip-hid.service << 'SERVICE_EOF'
[Unit]
Description=PiFlip USB HID Gadget
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/piflip-hid-gadget.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    systemctl daemon-reload
    systemctl enable piflip-hid.service
    info "HID gadget service enabled. Will activate on next boot."
    warn "Reboot required for USB HID (dwc2 overlay) to take effect."
else
    warn "Not a Pi Zero — HID gadget configured for Pi Zero 2W OTG port."
    warn "On Pi 4, connect USB-C power port to host with OTG-capable cable."
fi

# -----------------------------------------------------------------------
# 6. Set up autostart (optional)
# -----------------------------------------------------------------------
info "Creating PiFlip launcher..."
cat > /usr/local/bin/piflip << 'LAUNCHER_EOF'
#!/bin/bash
cd /home/user/eamonnn
python3 main.py "$@"
LAUNCHER_EOF
chmod +x /usr/local/bin/piflip

# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
echo ""
info "=== Setup Complete ==="
info "Run PiFlip:   piflip"
info "With debug:   piflip --debug"
info "Terminal UI:  piflip --headless"
echo ""
warn "A reboot is recommended to activate all changes."

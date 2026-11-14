#!/usr/bin/env bash
# FlipKit Pi — Maximum Performance Setup
# Run once as root on the Pi 5 after first boot.
# Reboots at the end.
set -euo pipefail

RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GRN}[+]${NC} $*"; }
warn()  { echo -e "${YLW}[!]${NC} $*"; }
die()   { echo -e "${RED}[x]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && die "Run as root: sudo bash setup_performance.sh"

# ── 1. Overclock Pi 5 to 3.0 GHz ────────────────────────────────────────────
info "Applying Pi 5 overclock (3.0 GHz CPU / 1.0 GHz GPU)..."
CONFIG=/boot/firmware/config.txt
cp "$CONFIG" "${CONFIG}.bak"

# Remove any existing freq lines first
sed -i '/^arm_freq=/d;/^gpu_freq=/d;/^over_voltage/d' "$CONFIG"

cat >> "$CONFIG" <<'EOF'

# FlipKit Pi — performance overclock
arm_freq=3000
gpu_freq=1000
over_voltage_delta=50000
force_turbo=1
EOF
info "Overclock written to $CONFIG"

# ── 2. zram — compressed virtual RAM (200 % of physical = ~16 GB from 8 GB) ─
info "Setting up zram (lz4 compression, 200% RAM)..."
apt-get install -y zram-tools >/dev/null 2>&1

cat > /etc/default/zramswap <<'EOF'
ALGO=lz4
PERCENT=200
PRIORITY=100
EOF

systemctl enable zramswap
systemctl restart zramswap
info "zram active — $(free -h | awk '/Swap/{print $2}') swap available"

# ── 3. CPU governor → performance (all cores) ────────────────────────────────
info "Pinning CPU governor to performance..."
apt-get install -y linux-cpupower >/dev/null 2>&1 || true
cpupower frequency-set -g performance 2>/dev/null || \
  for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "$gov"
  done

# Persist across reboots
cat > /etc/systemd/system/flipkit-performance.service <<'EOF'
[Unit]
Description=FlipKit Pi — CPU performance governor
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/bash -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $g; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable flipkit-performance.service
info "Performance governor locked in"

# ── 4. NVMe I/O scheduler → none (best for SSDs) ────────────────────────────
info "Setting NVMe I/O scheduler..."
for dev in /sys/block/nvme*/queue/scheduler; do
  echo none > "$dev" 2>/dev/null && info "  $dev → none"
done

# Persist via udev
cat > /etc/udev/rules.d/60-flipkit-nvme.rules <<'EOF'
ACTION=="add|change", KERNEL=="nvme[0-9]n[0-9]", ATTR{queue/scheduler}="none"
EOF

# ── 5. Mount NVMe with noatime (stop wasting writes on access timestamps) ────
info "Enabling noatime on root mount..."
sed -i 's|\(UUID=[^ ]*\s\+/\s\+ext4\s\+\)defaults|\1defaults,noatime|' /etc/fstab || \
  warn "Could not patch fstab — do it manually: add noatime to / mount"

# ── 6. Increase vm.swappiness so zram gets used aggressively ─────────────────
info "Tuning kernel memory parameters..."
cat > /etc/sysctl.d/99-flipkit.conf <<'EOF'
vm.swappiness=180
vm.watermark_boost_factor=0
vm.watermark_scale_factor=125
vm.page-cluster=0
EOF
sysctl -p /etc/sysctl.d/99-flipkit.conf >/dev/null

# ── 7. Faster Python startup — bytecode cache on NVMe ────────────────────────
info "Pre-compiling FlipKit Python modules..."
python3 -m compileall /home/user/eamonnn -q 2>/dev/null || true

# ── Summary ──────────────────────────────────────────────────────────────────
echo
echo -e "${GRN}════════════════════════════════════════${NC}"
echo -e "${GRN}  FlipKit Pi — TURBO BUILD COMPLETE${NC}"
echo -e "${GRN}════════════════════════════════════════${NC}"
echo
echo "  CPU         3.0 GHz (was 2.4 GHz)"
echo "  RAM         $(free -h | awk '/Mem:/{print $2}') physical"
echo "  SWAP (zram) $(free -h | awk '/Swap:/{print $2}') compressed (lz4)"
echo "  NVMe I/O    none (SSD optimal)"
echo "  Governor    performance (all cores)"
echo
warn "Reboot required for overclock to take effect."
read -rp "Reboot now? [Y/n] " yn
[[ "${yn,,}" != "n" ]] && reboot

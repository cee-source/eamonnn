# FlipKit Pi — Maximum RAM & Speed Upgrades

## Software (do now — free)

Run `sudo bash setup_performance.sh` after first boot. What it does:

| Tweak | Before | After |
|---|---|---|
| CPU clock | 2.4 GHz | **3.0 GHz** |
| GPU clock | 910 MHz | **1.0 GHz** |
| Effective RAM (zram lz4) | 8 GB | **~16 GB** |
| NVMe I/O scheduler | mq-deadline | **none (SSD)** |
| CPU governor | ondemand | **performance** |

---

## Hardware (order these for maximum specs)

### Tier 1 — Pi 5 maxed out (~$150 total upgrade)

| Part | Spec | Where |
|---|---|---|
| Raspberry Pi 5 — **8GB** | 8 GB LPDDR4X · 2.4→3.0 GHz OC | rpilocator.com |
| Raspberry Pi M.2 HAT+ | PCIe Gen 2 × 1 NVMe slot | official Pi store |
| WD Black SN770 **2 TB** M.2 2280 | ~3,500 MB/s read · 2 TB | Amazon / Newegg |
| GeeekPi Pi 5 Active Cooler | keeps 3.0 GHz stable under load | Amazon |
| 65 W USB-C PD power bank | enough current for Pi 5 + HATs | Anker/Baseus |

**Result: 8 GB RAM · 2 TB NVMe · 3.0 GHz · ~$150**

---

### Tier 2 — 16 GB RAM (Compute Module 5)

The Pi CM5 ships with up to **16 GB** LPDDR4X — double the Pi 5.
Needs a carrier board that breaks out GPIO, HDMI, USB, and the M.2 slot.

| Part | Note |
|---|---|
| Raspberry Pi CM5 Lite **16GB** | no eMMC — boots from NVMe |
| Waveshare CM5-IO-BASE-A | full GPIO + 2× HDMI + M.2 slot |
| Same 2 TB SN770 as above | same slot |

**Result: 16 GB RAM · 2 TB NVMe · 3.0 GHz · ~$220**
All existing HATs (MFRC522, CC1101, etc.) work unchanged — same 40-pin header.

---

### Tier 3 — Absolutely insane (NVIDIA Jetson Orin NX)

If you want 64 GB unified CPU+GPU memory and CUDA cores for ML/vision:

| Part | Spec |
|---|---|
| Jetson AGX Orin **64 GB** | 64 GB · 12-core A78AE · 2048 CUDA cores |
| Jetson carrier board (Seeed A607) | 40-pin GPIO header — HATs plug straight in |
| 2 TB NVMe | M.2 slot on carrier |

**Result: 64 GB RAM · 2 TB NVMe · 2 TFLOPS AI · ~$1,100**
Still runs all the FlipKit modules (same Linux, same Python, same GPIO pinout).

---

## Which tier?

- **Portable pocket device** → Tier 1 (Pi 5 8GB + NVMe)
- **Full power, still Pi** → Tier 2 (CM5 16GB)
- **Absolutely no limits** → Tier 3 (Jetson AGX Orin 64GB)

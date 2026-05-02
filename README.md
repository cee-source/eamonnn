# PIR Motion Cat Meow Alert

When the PIR sensor detects movement, a Bluetooth speaker plays a cat meow sound.

---

## What You Need

- Raspberry Pi 5
- PIR motion sensor (HC-SR501 or similar)
- Bluetooth speaker
- 3 female-to-female jumper wires
- A meow sound file (`meow.wav`)

---

## Wiring the PIR Sensor to the Pi 5

The PIR sensor has **3 pins** — check the label on yours (may say VCC, OUT, GND or +, OUT, -).

```
PIR Pin   →   Raspberry Pi 5 Pin
--------      ------------------
VCC  (+)  →   Pin 2  (5V)
OUT       →   Pin 11 (GPIO 17)
GND  (-)  →   Pin 6  (Ground)
```

### GPIO diagram (looking at the Pi with the USB ports on the right):

```
 [Pin 1 - 3.3V]  [Pin 2 - 5V]  ← connect VCC here
 [Pin 3]          [Pin 4 - 5V]
 [Pin 5]          [Pin 6 - GND] ← connect GND here
 [Pin 7]          [Pin 8]
 [Pin 9]          [Pin 10]
 [Pin 11 - GPIO17] [Pin 12]     ← connect OUT here
```

> The HC-SR501 needs a few seconds to warm up when first powered on — this is normal.

---

## Setting Up the Bluetooth Speaker

Run the setup script once to pair your speaker:

```bash
bash setup_bluetooth.sh
```

It will scan for nearby Bluetooth devices, show you their addresses, and ask which one to connect to.

Or pair manually:

```bash
bluetoothctl
# Inside bluetoothctl:
power on
agent on
scan on
# Wait for your speaker to appear, note its address (e.g. AA:BB:CC:DD:EE:FF)
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
connect AA:BB:CC:DD:EE:FF
exit
```

---

## Getting a Meow Sound File

Download a free meow WAV file and save it as `meow.wav` in this folder:

```bash
# Option 1 — use the download helper:
python3 get_meow.py

# Option 2 — use any meow.wav you already have, just copy it here:
cp /path/to/your/meow.wav ./meow.wav
```

---

## Installing Dependencies

```bash
sudo apt update
sudo apt install -y python3-rpi.gpio python3-pip pulseaudio pulseaudio-module-bluetooth
pip3 install RPi.GPIO
```

---

## Running the Script

```bash
python3 pir_meow.py
```

Move your hand in front of the PIR sensor — the speaker should meow!
Press `Ctrl+C` to stop.

---

## Run Automatically on Boot (Optional)

```bash
sudo cp pir_meow.service /etc/systemd/system/
sudo systemctl enable pir_meow
sudo systemctl start pir_meow
```

Check if it's running:

```bash
sudo systemctl status pir_meow
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No sound from speaker | Run `bluetoothctl` and check it says `Connected: yes` |
| PIR triggers constantly | Turn the sensitivity dial on the PIR down (small orange pot) |
| PIR never triggers | Turn the sensitivity dial up, or check your wiring |
| `GPIO` not found error | Run `sudo apt install python3-rpi.gpio` |
| Sound plays from wrong device | Run `pactl list sinks short` to list audio devices |

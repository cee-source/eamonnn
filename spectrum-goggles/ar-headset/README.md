# AR Pass-Through Build (V2)

A bigger, pricier upgrade to the base [Spectrum Goggles](../README.md) build:
instead of a text readout on a small OLED, a camera feed is shown live on two
small displays — one per eye, VR-style — with the current band's reading
drawn as a moving overlay on top of the scene (rings for radio/microwave, a
laser line for infrared, violet rays for ultraviolet, a proximity-driven
green glow for gamma). Try the
[interactive simulator](../README.md#simulator) first — the overlay drawing
logic here matches it band-for-band.

## Why this needs a bigger board

The Arduino Nano in the base build can read sensors and drive a tiny OLED,
but it can't decode a camera stream or drive two independent video outputs.
This tier swaps the "brain" for a **Raspberry Pi 4** (the only Pi model with
two independent micro-HDMI outputs — genuinely one display per eye, not a
single screen split in half) and keeps the Arduino Nano as a dedicated
**sensor hub**, talking to the Pi over USB serial.

```
[ sensors ] --> [ Arduino Nano ]  --USB serial--> [ Raspberry Pi 4 ] --HDMI--> [ left-eye display ]
                                                          |------------HDMI--> [ right-eye display ]
                                                          ^
                                                     [ USB camera ]
```

One camera feeds both eyes (duplicated), so this is pass-through AR, not
true stereo 3D — a real depth-sensing version would need two cameras, which
is a straightforward but separate upgrade (swap in a stereo USB camera and
composite each eye from its own lens).

## Honesty note

The same physical limits from the base build still apply here — a laser
beam, expanding rings, and a glow are a *visual convention* for signal
strength, not literal images of invisible light. See the base
[README's feasibility table](../README.md#reality-check) for what's real
sensor data vs. simulated per band.

## Parts (in addition to the base build's four sensors)

| Qty | Part | Notes |
|---|---|---|
| 1 | Raspberry Pi 4 Model B (2GB+) | needs the dual micro-HDMI output |
| 1 | microSD card (16GB+) with Raspberry Pi OS | boot media |
| 1 | USB webcam (or Raspberry Pi Camera Module + USB capture, since the CSI camera port is single) | the pass-through feed |
| 2 | Small HDMI display panels (3.5"–5", with driver board) | one per eye |
| 2 | Micro-HDMI to HDMI (or Mini-HDMI, check your panels) cables | short, to fit inside the headset shell |
| 1 | VR headset shell/lens housing with two biconvex lenses (~34mm), or a 3D-printed equivalent | holds the two displays at eye distance |
| 1 | USB-C power supply, 5V/3A | Pi 4 power |
| 1 | USB-A to Mini/Micro-USB cable | Arduino Nano → Pi serial link |

The four sensors, the potentiometer, and its wiring are unchanged from the
[base build](../README.md) — the Arduino Nano keeps doing exactly what it
did before, it just also talks to the Pi now.

## Wire protocol

The firmware in `../firmware/spectrum_goggles.ino` already prints one line
per loop over serial (9600 baud):

```
<band-key>,<value>\n
```

e.g. `gamma,24` or `micro,1`. The Pi script reads whichever band is
currently selected straight off this line — the potentiometer stays wired
to the Arduino, not the Pi.

## Running it

```
pip install -r requirements.txt
python3 overlay.py --port /dev/ttyUSB0 --cam 0
```

- `--demo` runs without the Arduino attached, cycling through bands with
  simulated values — useful for testing the display/lens setup before the
  sensors are wired up.
- Output is a single window sized to two eyes side by side. Configure the Pi
  desktop (`raspi-config` / `xrandr`) so the two HDMI outputs form one
  extended desktop, left display first, then run the script fullscreen —
  each half lands on its own physical screen.

## Build order

1. Get both HDMI displays showing an extended desktop and confirm
   `overlay.py --demo` renders a full scene across both correctly before
   wiring anything else.
2. Wire the Arduino sensor hub exactly as in the base build, confirm its
   serial output with `screen /dev/ttyUSB0 9600` (or the Arduino Serial
   Monitor) shows `key,value` lines.
3. Run `overlay.py --port ...` without `--demo` and confirm the overlay
   reacts to the potentiometer and sensors.
4. Only then move everything into the headset shell — debugging is much
   easier on the bench.

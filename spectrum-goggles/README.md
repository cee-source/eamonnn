# Spectrum Goggles

Wearable goggles that read out several bands of the electromagnetic spectrum
using cheap, real sensors, switched with a potentiometer on the side.

Two build tiers:

- **This README** — an OLED readout build on an Arduino Nano. Cheap, simple,
  a good first build.
- **[`ar-headset/`](./ar-headset/)** — a VR-style upgrade: a camera feed on
  two eye displays with the current band drawn as a moving overlay on the
  scene, on a Raspberry Pi 4. Bigger, pricier, builds on top of this one.

## Simulator

Try the interactive simulator first to see the concept before you solder
anything: it shows what each band's readout (and, in the AR build, its
overlay) looks like, and which sensors behind it are real vs. simulated.

## Reality check

You cannot see radio waves, X-rays, or gamma rays with your eyes no matter
what's strapped to your face — those bands need fundamentally different
detection hardware (antennas, scintillators, photomultipliers), and some of
it isn't safe or legal for a hobbyist wearable. This build gives you a
genuine sensor reading for each band where one exists, and is honest about
the bands where it doesn't:

| Band | Feasible on goggles? | Sensor |
|---|---|---|
| Radio waves | Add-on | Simple diode envelope detector + antenna — signal strength only, no decoding |
| Microwaves | Yes | RCWL-0516 Doppler radar module — genuine presence/motion detection |
| Infrared | Yes | MLX90614 non-contact IR thermometer — real thermal readout |
| Visible light | Yes | BH1750 ambient light sensor — real lux readout (your eyes already do the "seeing" part) |
| Ultraviolet | Yes | GUVA-S12SD analog UV sensor — real UV index |
| X-rays | No | Needs a scintillator + photomultiplier or an X-ray source; not wearable-safe. Not included. |
| Gamma rays | Add-on | SBM-20 Geiger–Müller tube module — real background radiation count (CPM), safe (passive, no source needed) |

## Parts list

- Arduino Nano (or any 5V ATmega328 board) — main controller
- SSD1306 128×64 I2C OLED display
- 10 kΩ linear potentiometer — band select dial, mounted on the side of the goggle frame
- BH1750 ambient light sensor (I2C)
- GUVA-S12SD UV sensor (analog)
- MLX90614 IR thermometer (I2C)
- RCWL-0516 microwave Doppler module (digital)
- Optional: SBM-20 Geiger counter module (e.g. "RadiationD-v1.1 CAJOE" board, serial/pulse output)
- Optional: diode + short whip antenna for the radio-band signal meter
- Goggle/headband frame, 3.7 V LiPo + charge module, on/off switch, hookup wire

See [`SHOPPING_LIST.md`](./SHOPPING_LIST.md) for exact part specs, quantities,
and rough costs.

Note: MLX90614 and BH1700 both use I2C, both default to fixed addresses — check
your specific breakout board's address if you run into conflicts, and use an
I2C multiplexer or address-changeable variant if needed.

## Wiring

All I2C devices share SDA/SCL; only one device per non-I2C signal.

| Signal | Arduino Nano pin |
|---|---|
| OLED SDA / BH1750 SDA / MLX90614 SDA | A4 (shared I2C bus) |
| OLED SCL / BH1750 SCL / MLX90614 SCL | A5 (shared I2C bus) |
| Potentiometer wiper | A0 |
| GUVA-S12SD signal | A1 |
| RCWL-0516 OUT | D2 |
| Geiger module pulse output (optional) | D3 (interrupt pin) |
| Radio diode detector (optional) | A2 |
| All sensor VCC | 5V (check each module's actual voltage rating) |
| All sensor GND | GND |

Potentiometer: outer legs to 5V and GND, wiper to A0. Mount it on the side of
the frame within thumb's reach, matching the reference "dial on the side"
concept.

## Firmware

`firmware/spectrum_goggles.ino` reads the potentiometer to pick one of the
seven bands (matching the simulator), reads the real sensor for that band
when one is wired up, and shows the band name + reading on the OLED. Bands
without a wired sensor (X-rays always, others if you skip the optional part)
show "NO SENSOR" instead of a fake number.

### Libraries (Arduino Library Manager)

- `Adafruit_GFX`
- `Adafruit_SSD1306`
- `BH1750`
- `Adafruit_MLX90614`

## Build order

1. Wire the OLED + potentiometer only, flash the firmware, confirm the dial
   scrolls through all seven band names on screen.
2. Add BH1750, GUVA-S12SD, and MLX90614 one at a time, confirming each
   readout against a known source (a lamp, direct sun, your own hand).
3. Add the RCWL-0516 and confirm it flags presence when you wave a hand
   nearby.
4. Optionally add the Geiger module last — it's the most expensive and
   fragile part, and the firmware works fine without it (that channel just
   reads "NO SENSOR").

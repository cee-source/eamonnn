# Shopping List

Everything needed to build the goggles in this folder, grouped by function.
Prices are rough US ballparks from generic electronics retailers (AliExpress/
Amazon/Adafruit) — check current listings, but they'll tell you what's cheap
vs. what's the real cost driver (the Geiger module).

## Brain, display, dial

| Qty | Part | Notes | Approx. cost |
|---|---|---|---|
| 1 | Arduino Nano (or clone, ATmega328P + CH340/FTDI) | main controller | $4–8 |
| 1 | SSD1306 0.96" 128×64 I2C OLED display | white or blue, 4-pin (VCC/GND/SCL/SDA) | $4–7 |
| 1 | 10 kΩ linear potentiometer (B10K), panel-mount style | the side dial | $1–2 |
| 1 | Matching knob cap for the potentiometer shaft | grip for the dial | $1 |

## Sensors — the four real ones

| Qty | Part | Notes | Approx. cost |
|---|---|---|---|
| 1 | BH1750 ambient light sensor breakout (often sold as "GY-302") | visible light, I2C | $2–4 |
| 1 | GUVA-S12SD UV sensor breakout | ultraviolet, analog output | $2–5 |
| 1 | MLX90614 IR thermometer breakout (often sold as "GY-906") | infrared, I2C — buy the ESF (5°) FOV variant unless you want a wide field | $8–15 |
| 1 | RCWL-0516 microwave Doppler radar module | microwave presence, digital output | $2–3 |

## Add-on bands (optional but real)

| Qty | Part | Notes | Approx. cost |
|---|---|---|---|
| 1 | Geiger counter module, e.g. "RadiationD-v1.1 (CAJOE)" with SBM-20 tube | gamma/background radiation, pulse output — by far the priciest single part | $20–35 |
| 1 | 1N34A germanium diode | for the DIY radio envelope detector | $1 (usually sold in packs) |
| 1 | Short telescoping whip antenna (or ~15–30 cm solid wire) | radio pickup | $1–3 |
| 1 | 100 kΩ resistor + 100 pF–1 nF ceramic capacitor | smooths the diode's output into a DC level the analog pin can read | pennies (buy an assortment pack) |

## Power

Pick one path — don't need both.

**Simple (no charging):**
| Qty | Part | Notes |
|---|---|---|
| 1 | 4×AAA battery holder with switch | ~6V into Arduino's VIN pin, runs the onboard regulator directly, no boost converter needed |

**Rechargeable:**
| Qty | Part | Notes |
|---|---|---|
| 1 | 3.7V LiPo battery, 500–1000 mAh, with JST connector | flat "goggle strap" cell shapes exist if you want it to disappear into the headband |
| 1 | TP4056 LiPo charger/protection module (USB-C preferred) | charging + over-discharge protection |
| 1 | MT3608 (or similar) boost converter module | steps 3.7–4.2V up to a clean 5V into the Arduino's 5V pin — a single LiPo cell is too low to drive VIN through the onboard regulator |
| 1 | SPST slide switch | power on/off |

## Mechanical / wearable (no-solder build)

| Qty | Part | Notes |
|---|---|---|
| 1 | Ski-goggle frame, safety-glasses frame, or headband mount | whatever you're building into — wide-strap ski goggles give the most room for electronics on the side |
| 1 | Half-size or full-size solderless breadboard | mounting point for the Nano + all modules — no soldering needed |
| 1 | Small project box, or just the breadboard's own backing | houses the Nano, breadboard, and battery on the goggle's side arm |
| — | Hot glue sticks (for the glue gun below) | mounts the breadboard, battery, and enclosure to the frame — this replaces solder as the "permanent" step |
| — | Double-sided foam tape | extra hold under the breadboard/battery before gluing, if you want it repositionable first |

## Wiring & build supplies (no-solder)

| Qty | Part | Notes |
|---|---|---|
| 1 set | Jumper wires (M-M, M-F, F-F, Dupont-style) | breadboard-to-module wiring — the only "wiring" this build needs |
| 1 set | Alligator-clip test leads (4–6) | connects the side-mounted potentiometer to the breadboard, since it sits too far away to plug in directly |

**Buy modules "with pins" / "pre-soldered header"** — nearly all BH1750,
GUVA-S12SD, MLX90614, RCWL-0516, OLED, and Geiger module listings already
ship this way, but check the listing photo before ordering so nothing
arrives needing a soldering iron. The Arduino Nano itself always ships with
headers pre-soldered.

**Battery wiring**: pick a battery holder with bare wire leads, strip ~5mm
of insulation, and push the wires straight into the breadboard's power rail
— no connector needed. A dab of hot glue over the hole keeps it from
wiggling loose.

## Tools (if you don't already have them)

- Hot glue gun + extra glue sticks
- Multimeter (continuity + voltage checks while wiring)
- Small Phillips/hex driver set (for frame and enclosure screws, if using a project box)
- Wire strippers (for the battery leads)

## AR headset upgrade (V2, optional)

Adds a camera pass-through view with the band overlay drawn on the scene —
see [`ar-headset/`](./ar-headset/). Everything above still applies; this
replaces the OLED with two eye displays and adds a Pi as the video brain.

| Qty | Part | Notes | Approx. cost |
|---|---|---|---|
| 1 | Raspberry Pi 4 Model B (2GB+) | needs dual micro-HDMI — cheaper Pi models only have one | $35–55 |
| 1 | microSD card, 16GB+ | Pi OS boot media | $5–8 |
| 1 | USB webcam | the pass-through camera feed | $8–20 |
| 2 | Small HDMI display panel + driver board (3.5"–5") | one per eye | $15–25 each |
| 2 | Micro-HDMI to HDMI cable (short) | check your panel's connector | $3–5 each |
| 1 | VR lens housing / lens cups (~34mm biconvex) or 3D-printed equivalent | holds displays at eye distance | $8–15 |
| 1 | USB-C power supply, 5V/3A | Pi 4 power | $8–10 |
| 1 | USB-A to Micro-USB cable | Arduino → Pi serial link | $2–4 |

Rough total for the V2 upgrade on top of the base build: **~$120–170**.

## Rough total

- Core build (no add-ons, simple battery power): **~$25–40**
- With radio + Geiger add-ons and rechargeable power: **~$60–90**, driven mostly by the Geiger module

## Where the corners can't be cut

- **MLX90614** and **BH1750** genuinely need to be the named parts (or close
  clones) — there isn't a "generic photoresistor" substitute that gives you a
  calibrated lux or temperature reading.
- The **Geiger module** is the one part worth buying from a reputable seller
  (e.g. Adafruit, or a well-reviewed CAJOE listing) rather than the cheapest
  listing — the SBM-20 tube and its HV driver circuit are the whole product.
- Everything else (resistors, wire, breadboard, enclosure) is genuinely
  generic — buy whatever's cheapest and on hand.
- **No soldering is required anywhere in this build.** The breadboard plus
  jumper wires and alligator clips handle every electrical connection; hot
  glue handles every mechanical one (mounting the breadboard, battery, and
  dial to the frame).

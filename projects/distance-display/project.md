# Project: Distance Display

HC-SR04 ultrasonic sensor + LCD1602 display on an Arduino Nano.  
Shows the live distance in centimetres on the screen.

---

## What You'll Need

| Part | Quantity |
|------|----------|
| Arduino Nano | 1 |
| Breadboard | 1 |
| HC-SR04 ultrasonic sensor | 1 |
| LCD1602 display (16-pin) | 1 |
| Potentiometer 10kΩ | 1 |
| Resistor 220Ω | 1 |
| Jumper wires | ~14 |
| USB mini cable | 1 |

---

## Which LCD Do You Have?

Look at the **back** of the screen:

- **Flat back, all 16 pins exposed** → you have the plain LCD1602. Follow this guide.
- **Small blue/black circuit board soldered onto the back, only 4 pins sticking out** → you have the I2C version. The wiring is much simpler (see the note at the bottom).

---

## Part 1: LCD1602 Wiring

The LCD has 16 pins numbered left to right when the screen faces you (pin 1 is on the left):

```
LCD1602 (face-up view):
  ┌─────────────────────────────────┐
  │  [screen area - 16 cols x 2 rows] │
  └─────────────────────────────────┘
  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 16
  ↓  ↓  ↓  ↓  ↓  ↓  
 GND 5V CTR RS RW  E  (D0-D3 unused)  D4 D5 D6 D7 BL+ BL-
```

### LCD Pin Connections

| LCD Pin | LCD Name | Connect to |
|---------|----------|-----------|
| 1 | VSS (GND) | Arduino GND |
| 2 | VDD (5V) | Arduino 5V |
| 3 | V0 (contrast) | Potentiometer **middle** leg |
| 4 | RS | Arduino **D12** |
| 5 | RW | Arduino GND |
| 6 | E (Enable) | Arduino **D11** |
| 7–10 | D0–D3 | **Not connected** |
| 11 | D4 | Arduino **D7** |
| 12 | D5 | Arduino **D6** |
| 13 | D6 | Arduino **D5** |
| 14 | D7 | Arduino **D4** |
| 15 | A (backlight +) | 220Ω resistor → Arduino 5V |
| 16 | K (backlight –) | Arduino GND |

### Contrast Potentiometer

```
Pot left leg   → GND
Pot middle leg → LCD pin 3 (V0)
Pot right leg  → 5V
```

Turn the knob until you can see the characters clearly. If the screen is blank but the backlight glows, the contrast is the issue — try turning the pot.

---

## Part 2: HC-SR04 Wiring

| HC-SR04 Pin | Connect to |
|-------------|-----------|
| VCC | Arduino 5V |
| TRIG | Arduino **D9** |
| ECHO | Arduino **D8** |
| GND | Arduino GND |

---

## Full Wiring Summary

```
Arduino Nano
                  ┌──────────────────────────┐
            GND ──┤ GND              D12 ─────┼─── LCD pin 4 (RS)
             5V ──┤ 5V               D11 ─────┼─── LCD pin 6 (E)
                  │                   D7 ─────┼─── LCD pin 11 (D4)
             D9 ──┤ TRIG (HC-SR04)    D6 ─────┼─── LCD pin 12 (D5)
             D8 ──┤ ECHO (HC-SR04)    D5 ─────┼─── LCD pin 13 (D6)
                  │                   D4 ─────┼─── LCD pin 14 (D7)
                  └──────────────────────────┘

HC-SR04: VCC→5V, GND→GND, TRIG→D9, ECHO→D8

LCD:  Pin 1 → GND
      Pin 2 → 5V
      Pin 3 → Pot middle leg
      Pin 4 → D12
      Pin 5 → GND
      Pin 6 → D11
      Pins 7-10 → not connected
      Pin 11 → D7
      Pin 12 → D6
      Pin 13 → D5
      Pin 14 → D4
      Pin 15 → 220Ω → 5V
      Pin 16 → GND

Potentiometer: left→GND, middle→LCD pin 3, right→5V
```

---

## The Code

File: `code/distance_display/distance_display.ino`

The `LiquidCrystal` library is **built into the Arduino IDE** — no need to download anything.

---

## Uploading to the Nano

1. In Arduino IDE: **Tools > Board > Arduino Nano**
2. **Tools > Processor > ATmega328P** (if upload fails, try "ATmega328P (Old Bootloader)")
3. **Tools > Port** — select the Nano's port
4. Upload!

---

## What You Should See

```
┌────────────────┐
│ Distance:      │   ← stays there, never changes
│ 24 cm          │   ← updates every 200ms
└────────────────┘
```

Move your hand toward and away from the sensor and watch the number update live!

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Screen is blank, backlight on | Turn the contrast potentiometer — this is almost always the issue |
| Screen shows garbage characters | Contrast is too high — turn pot the other way |
| Shows "0 cm" or wild numbers | Check TRIG/ECHO pins aren't swapped |
| Screen doesn't light up at all | Check pin 15 resistor and pin 16 GND |
| Upload fails | Try "ATmega328P (Old Bootloader)" in Tools > Processor |

---

## Note: I2C LCD Version

If your LCD has a blue board on the back with only 4 pins, it's the **I2C version**. Much simpler wiring:

```
I2C adapter → Arduino Nano
GND → GND
VCC → 5V
SDA → A4
SCL → A5
```

You'll also need to install the `LiquidCrystal_I2C` library:  
**Tools > Manage Libraries** → search for `LiquidCrystal I2C` by Frank de Brabander → Install

Then change the top of the code to:
```cpp
#include <LiquidCrystal_I2C.h>
LiquidCrystal_I2C lcd(0x27, 16, 2);
// (if 0x27 doesn't work, try 0x3F)
```
And in `setup()` replace `lcd.begin(16, 2)` with:
```cpp
lcd.init();
lcd.backlight();
```
Everything else stays the same.

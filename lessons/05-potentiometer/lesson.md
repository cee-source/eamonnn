# Lesson 05: Dimmer Switch

**You'll build:** Turn a knob to control how bright an LED glows.  
**New idea:** The difference between digital (on/off) and analog (any value in between).

**You'll learn:**
- Analog inputs with `analogRead()` — reads values 0 to 1023
- PWM outputs with `analogWrite()` — controls brightness 0 to 255
- The Serial Monitor — see values printed on your computer
- Variables and maths in code

---

## Background

So far we've dealt with **digital** — things that are either fully ON or fully OFF. But the real world is full of things that can be *in between*. How bright is the light? How fast is the wind? How warm is it?

### Analog Input

The potentiometer (the knob) is an **analog** component. As you turn it, it sends a voltage anywhere from 0V to 5V to the Arduino's analog pin. The Arduino converts this to a number between **0** (all the way off) and **1023** (all the way on) — that's 1024 different values!

### PWM Output (Dimming LEDs)

Normal digital pins can only be HIGH (5V) or LOW (0V). But some pins on the Arduino support **PWM** — Pulse Width Modulation. PWM pins rapidly switch between HIGH and LOW, but by controlling how long they stay HIGH vs LOW, they *appear* to be somewhere in between.

```
Full brightness (255):  ████████████████  (always HIGH)
Half brightness (128):  ████    ████    ████    (HIGH half the time)
Quarter (64):           ██      ██      ██      (HIGH quarter of the time)
Off (0):                                (always LOW)
```

PWM pins on the Uno are: **3, 5, 6, 9, 10, 11** — look for the `~` symbol next to the pin number.

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Breadboard | 1 |
| LED (any colour) | 1 |
| Resistor 220Ω | 1 |
| Potentiometer | 1 |
| Jumper wires | 6 |
| USB cable | 1 |

---

## Wiring

### The Potentiometer

A potentiometer has 3 legs:

```
  Left leg  ──── GND (0V)
  Middle leg ─── Signal (goes to analog pin A0) — this is what we read
  Right leg ──── 5V power
```

The middle leg outputs a voltage between 0V and 5V depending on the knob position.

### The Circuit

```
Arduino 5V  ──── Pot right leg
Arduino GND ──── Pot left leg
Arduino A0  ──── Pot middle leg (signal)

Arduino Pin 9 ──── Resistor 220Ω ──── LED long leg (+) ──── LED short leg (–) ──── GND
```

### Step-by-Step Breadboard Instructions

**Unplug Arduino before wiring!**

**Step 1:** Push the potentiometer into the breadboard (it has 3 pins in a row). Let's say rows 5–7, column c.

**Step 2:** Wire the **left pin** (row 5) → Arduino **GND**.

**Step 3:** Wire the **middle pin** (row 6) → Arduino **A0**.

**Step 4:** Wire the **right pin** (row 7) → Arduino **5V**.

**Step 5:** Place your LED with long leg in row 12 col c, short leg in row 13 col c.

**Step 6:** Place a 220Ω resistor from row 10 col c to row 12 col c.

**Step 7:** Wire row 10 col a → Arduino **Pin 9**.

**Step 8:** Wire row 13 col a → Arduino **GND**.

### Connection Summary

| From | To |
|------|----|
| Arduino 5V | Potentiometer right leg |
| Arduino GND | Potentiometer left leg |
| Arduino A0 | Potentiometer middle leg (signal) |
| Arduino Pin 9 | 220Ω resistor → LED long leg (+) |
| LED short leg (–) | Arduino GND |

---

## The Code

```cpp
int potPin = A0;
int ledPin = 9;

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  int potValue  = analogRead(potPin);
  int brightness = potValue / 4;

  analogWrite(ledPin, brightness);

  Serial.print("Knob: ");
  Serial.print(potValue);
  Serial.print("   Brightness: ");
  Serial.println(brightness);

  delay(50);
}
```

After uploading, open the **Serial Monitor** by clicking the magnifying glass icon (top right of the IDE). Make sure it's set to **9600 baud**. You'll see the values update as you turn the knob!

---

## Code Explained

### `Serial.begin(9600)`

```cpp
Serial.begin(9600);
```

This starts communication between your Arduino and your computer over the USB cable. The number `9600` is the **baud rate** — the speed of communication. Both sides must use the same number.

### `analogRead(potPin)`

```cpp
int potValue = analogRead(potPin);
```

Reads the voltage on pin A0 and converts it to a number from **0 to 1023**:
- All the way left: `0`
- All the way right: `1023`
- Halfway: around `512`

### The Maths

```cpp
int brightness = potValue / 4;
```

`analogRead` gives us 0–1023. But `analogWrite` takes 0–255. Since 1024 ÷ 4 = 256, dividing by 4 converts our range:

```
0    ÷ 4 = 0    (LED off)
512  ÷ 4 = 128  (LED half bright)
1023 ÷ 4 = 255  (LED full bright)
```

### `analogWrite(ledPin, brightness)`

```cpp
analogWrite(ledPin, brightness);
```

Sets the LED brightness using PWM:
- `0` = off
- `128` = half brightness
- `255` = full brightness

### `Serial.print()` and `Serial.println()`

```cpp
Serial.print("Knob: ");    // prints text, no new line
Serial.print(potValue);    // prints the number, no new line
Serial.println(brightness); // prints with a new line at the end
```

`print` keeps on the same line. `println` (print line) moves to the next line. Use both together to format your output nicely.

---

## What to Expect

Turn the knob one way and the LED gets brighter. Turn it the other way and it gets dimmer. Watch the Serial Monitor to see the numbers change in real time!

---

## Challenges

1. **Map it properly** — instead of dividing by 4, use the `map()` function:
   ```cpp
   int brightness = map(potValue, 0, 1023, 0, 255);
   ```
   This does the same thing but is clearer to read.

2. **Serial Plotter** — go to **Tools > Serial Plotter** instead of Serial Monitor. You'll see a live graph of the values as you turn the knob!

3. **Blink speed control** — instead of controlling brightness, make the knob control how fast the LED blinks:
   ```cpp
   int blinkTime = map(potValue, 0, 1023, 50, 2000);
   digitalWrite(ledPin, HIGH);
   delay(blinkTime);
   digitalWrite(ledPin, LOW);
   delay(blinkTime);
   ```

4. **Two LEDs** — add a second LED on pin 10. When the knob is in the left half, LED 1 is on. When it's in the right half, LED 2 is on.

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| Analog | A value that can be anywhere in a range (not just on/off) |
| `analogRead()` | Reads a voltage on an analog pin, returns 0–1023 |
| PWM | Rapidly switching to simulate in-between values |
| `analogWrite()` | Sets PWM brightness on a PWM pin, 0–255 |
| Potentiometer | A variable resistor controlled by a knob |
| Serial Monitor | A window on your computer that shows messages from Arduino |
| Baud rate | The speed of serial communication (9600 is standard) |

---

**Next up: [Lesson 06 — Buzzer Music](../06-buzzer/lesson.md)** — make your Arduino play a tune!

# Lesson 08: Night Light

**You'll build:** A light that automatically gets brighter when the room gets darker.  
**New idea:** Reading from a real-world sensor and reacting to it.

**You'll learn:**
- Photoresistors (light sensors)
- The `map()` function — converting between value ranges
- Combining analog input with analog output
- Using the Serial Monitor to understand your sensor

---

## Background

A **photoresistor** (also called a Light Dependent Resistor or LDR) is a component whose electrical resistance changes with light. In bright light, its resistance is low (letting more electricity flow). In darkness, its resistance is high (blocking electricity flow).

We use this to measure how much light there is in the room, then do the opposite with the LED brightness — bright room → dim LED, dark room → bright LED. Night light!

### How the Sensor Circuit Works

The photoresistor and a fixed resistor (10kΩ) form a **voltage divider**:

```
   5V
    │
   [LDR — changes with light]
    │
    ├──── A0 reads this voltage
    │
   [10kΩ fixed resistor]
    │
   GND
```

As light increases, the LDR's resistance drops, and more voltage appears at A0 (higher reading). In darkness, resistance is high, so less voltage at A0 (lower reading).

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Breadboard | 1 |
| Photoresistor (LDR) | 1 |
| Resistor 10kΩ | 1 |
| LED (any colour) | 1 |
| Resistor 220Ω | 1 |
| Jumper wires | 5 |
| USB cable | 1 |

The **10kΩ resistor** has brown-black-orange colour bands.

---

## Wiring

### The Circuit

```
Arduino 5V ──── Photoresistor leg 1
                Photoresistor leg 2 ──┬──── Arduino A0
                                      │
                              10kΩ resistor
                                      │
                                    Arduino GND

Arduino Pin 9 ──── Resistor 220Ω ──── LED long leg (+) ──── LED short leg (–) ──── GND
```

### Step-by-Step Breadboard Instructions

**Unplug Arduino before wiring!**

**Step 1:** Push the photoresistor into the breadboard (rows 4–5, col c). The LDR has no polarity so either leg can go either way.

**Step 2:** Wire **row 4 col a** → Arduino **5V**.

**Step 3:** Wire **row 5 col a** → Arduino **A0** (this is the signal — the point between the two resistors).

**Step 4:** Place the 10kΩ resistor from **row 5 col e** to **row 7 col e**.

**Step 5:** Wire **row 7 col e (or any connected hole)** → Arduino **GND**.

**Step 6:** Place the LED long leg in row 11 col c, short leg in row 12 col c.

**Step 7:** Place a 220Ω resistor from row 9 col c to row 11 col c.

**Step 8:** Wire **row 9 col a** → Arduino **Pin 9**.

**Step 9:** Wire **row 12 col a** → Arduino **GND**.

### Connection Summary

| From | To |
|------|----|
| Arduino 5V | LDR leg 1 |
| LDR leg 2 | Arduino A0 **and** 10kΩ resistor top |
| 10kΩ resistor bottom | Arduino GND |
| Arduino Pin 9 | 220Ω resistor → LED long leg (+) |
| LED short leg (–) | Arduino GND |

---

## The Code

```cpp
int ldrPin = A0;
int ledPin = 9;

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  int lightValue = analogRead(ldrPin);

  // Bright room = high lightValue = dim LED
  // Dark room   = low lightValue  = bright LED
  int brightness = map(lightValue, 0, 1023, 255, 0);

  analogWrite(ledPin, brightness);

  Serial.print("Light sensor: ");
  Serial.print(lightValue);
  Serial.print("   LED brightness: ");
  Serial.println(brightness);

  delay(100);
}
```

Open the **Serial Monitor** at 9600 baud to see the sensor values as you cover the LDR with your hand!

---

## Code Explained

### `map()` — Converting Between Ranges

```cpp
int brightness = map(lightValue, 0, 1023, 255, 0);
```

`map()` takes a value from one range and converts it to another:

```
map(value, fromLow, fromHigh, toLow, toHigh)
```

In our case:
- The input range is 0–1023 (from `analogRead`)
- The output range is **255–0** (notice: reversed!)

This reversal is the key — when light is low (0), brightness is high (255). When light is high (1023), brightness is low (0). The LED gets brighter as it gets darker.

Without `map()`, you'd write:
```cpp
int brightness = 255 - (lightValue / 4);  // harder to read
```

`map()` makes the intention clear.

### Reading Your Sensor Values

Before writing the full code, it's useful to just read the sensor and print it:

```cpp
void loop() {
  Serial.println(analogRead(A0));
  delay(100);
}
```

Open the Serial Monitor and cover the LDR with your hand, then uncover it. Note the values in bright and dark conditions — you'll need these for the next challenge!

---

## What to Expect

In normal room lighting, the LED will be dim or off. Cover the photoresistor with your hand (making it dark) and the LED will gradually get brighter. Point a torch at it and it'll go off.

Open the Serial Monitor to see the numbers change in real time as the light level changes!

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| LED is always bright or always off | Your sensor value range might not match 0-1023; check Serial Monitor to see actual values |
| Values don't change when you cover the sensor | Check the 10kΩ resistor is in the right place |
| LED flickers randomly | The sensor might be reading from a flickering light source (e.g. fluorescent lights) — try adding a `delay(200)` |

---

## Challenges

1. **Find your thresholds** — use the Serial Monitor to find the light value where you'd call it "dark" in your room. Then rewrite the code to turn the LED fully ON when below that value, fully OFF when above it (no gradual dimming):
   ```cpp
   if (lightValue < 400) {
     digitalWrite(ledPin, HIGH);  // dark: LED on
   } else {
     digitalWrite(ledPin, LOW);   // bright: LED off
   }
   ```
   Replace `400` with your actual threshold value!

2. **Gradual but with a threshold** — only start dimming below 600, and turn fully off above 800. You'll need an `if/else if/else` chain.

3. **Light alarm** — add a buzzer from Lesson 06. If the room suddenly gets very dark (someone turned off the lights), play an alarm tone.

4. **Serial Plotter** — go to **Tools > Serial Plotter**. Cover and uncover the sensor and watch the graph! Try different light sources (torch, lamp, sunlight).

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| Photoresistor (LDR) | A sensor whose resistance changes with light level |
| Voltage divider | Two resistors in series that split the voltage — used to read sensors |
| `map()` | Converts a value from one range to another |
| Threshold | A specific value that triggers a change in behaviour |

---

**Next up: [Lesson 09 — Servo Motor](../09-servo/lesson.md)** — make something move to an exact position!

# Lesson 07: RGB LED

**You'll build:** A single LED that can display any colour.  
**New idea:** Mixing red, green, and blue light to make millions of colours — just like your phone screen!

**You'll learn:**
- RGB colour mixing
- Writing your own functions
- Using `analogWrite()` on multiple pins

---

## Background

Your TV, phone, and computer screen are made of millions of tiny dots, each one capable of producing red, green, and blue light. By mixing those three colours at different brightnesses, they can make any colour imaginable.

Your RGB LED works the same way — it has three tiny LEDs inside one package:

```
  Red LED   ─┐
  Green LED  ─┤── share one common leg (GND)
  Blue LED  ─┘
```

By controlling how bright each colour is (0–255), you can mix them:

| Red | Green | Blue | Result |
|-----|-------|------|--------|
| 255 | 0 | 0 | Red |
| 0 | 255 | 0 | Green |
| 0 | 0 | 255 | Blue |
| 255 | 255 | 0 | Yellow |
| 0 | 255 | 255 | Cyan |
| 255 | 0 | 255 | Magenta/Purple |
| 255 | 255 | 255 | White |
| 0 | 0 | 0 | Off |
| 255 | 128 | 0 | Orange |

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Breadboard | 1 |
| RGB LED (4-legged) | 1 |
| Resistors 220Ω | 3 |
| Jumper wires | 4 |
| USB cable | 1 |

---

## The RGB LED's Legs

The RGB LED has **4 legs**. The longest one is the **common cathode** (GND). The other three are Red, Green, Blue:

```
  RGB LED legs (from left to right):
  
  R  GND  G  B
  |   |   |  |
  |   |   |  |
  (long = GND)
  
  Hold the LED so the flat side faces you:
  left to right: Red, GND (longest), Green, Blue
```

**Common Cathode** means all three LEDs share one GND. Each of the other three legs controls one colour.

---

## Wiring

### The Circuit

```
Arduino Pin 11 ──── Resistor 220Ω ──── RGB LED Red leg
Arduino Pin 10 ──── Resistor 220Ω ──── RGB LED Green leg
Arduino Pin 9  ──── Resistor 220Ω ──── RGB LED Blue leg
                                        RGB LED GND leg ──── Arduino GND
```

### Step-by-Step Breadboard Instructions

**Unplug Arduino before wiring!**

**Step 1:** Push the RGB LED into the breadboard. It has 4 legs, so push it across 4 columns, e.g. rows 5–8 col c (each leg in its own row).

**Step 2:** Identify which row has the **longest leg** — that's GND. Wire that row → Arduino **GND**.

**Step 3:** The remaining legs are Red, Green, Blue (in order away from the GND leg). Connect each through a **220Ω resistor** to:
   - Red leg → resistor → Arduino **Pin 11**
   - Green leg → resistor → Arduino **Pin 10**
   - Blue leg → resistor → Arduino **Pin 9**

**Note:** Pins 9, 10, and 11 are all PWM pins (marked with `~`) — that's essential for colour mixing!

### Connection Summary

| From | To |
|------|----|
| Arduino Pin 11 | 220Ω resistor → RGB LED Red leg |
| Arduino Pin 10 | 220Ω resistor → RGB LED Green leg |
| Arduino Pin 9 | 220Ω resistor → RGB LED Blue leg |
| RGB LED GND leg (longest) | Arduino GND |

---

## The Code

```cpp
int redPin   = 11;
int greenPin = 10;
int bluePin  =  9;

void setup() {
  pinMode(redPin,   OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin,  OUTPUT);
}

void setColour(int r, int g, int b) {
  analogWrite(redPin,   r);
  analogWrite(greenPin, g);
  analogWrite(bluePin,  b);
}

void loop() {
  setColour(255, 0,   0);    delay(1000);  // Red
  setColour(0,   255, 0);    delay(1000);  // Green
  setColour(0,   0,   255);  delay(1000);  // Blue
  setColour(255, 200, 0);    delay(1000);  // Orange
  setColour(255, 0,   255);  delay(1000);  // Magenta
  setColour(0,   255, 255);  delay(1000);  // Cyan
  setColour(255, 255, 255);  delay(1000);  // White
  setColour(0,   0,   0);    delay(500);   // Off
}
```

---

## Code Explained

### Writing Your Own Function

```cpp
void setColour(int r, int g, int b) {
  analogWrite(redPin,   r);
  analogWrite(greenPin, g);
  analogWrite(bluePin,  b);
}
```

This is a **function you wrote yourself**! Just like `setup()` and `loop()`, you can write your own functions that do a specific job, then call them from anywhere.

- `void` — means this function doesn't return a value
- `setColour` — the name you gave it (you can choose any name)
- `(int r, int g, int b)` — **parameters**: the values you pass in when you call it

When you call `setColour(255, 0, 0)`:
- `r` becomes 255
- `g` becomes 0
- `b` becomes 0

Then it runs `analogWrite` three times, one for each colour.

**Why use a function?** Instead of writing three `analogWrite` lines every time you want to set a colour, you just call `setColour()` once. Cleaner, easier to read, and if you want to change how it works, you only change it in one place.

### Calling the Function

```cpp
setColour(255, 0, 0);  delay(1000);  // Red
```

You call your function by writing its name and passing in the red, green, and blue values. The `delay(1000)` on the same line just keeps it tidy — you can also put it on the next line.

---

## What to Expect

The LED should cycle through red, green, blue, orange, magenta, cyan, white, then off — changing every second.

If a colour looks wrong (e.g. blue when you expect red), your Red/Green/Blue legs might be in a different order. Try swapping the pin numbers in the code to match your LED.

---

## Challenges

1. **Smooth rainbow** — instead of jumping between colours, fade smoothly through the rainbow using a `for` loop:
   ```cpp
   // Fade from red to green:
   for (int i = 0; i <= 255; i++) {
     setColour(255 - i, i, 0);
     delay(10);
   }
   ```

2. **Knob colour mixer** — use **three potentiometers** (one for R, one for G, one for B) to mix any colour you like manually

3. **Random colours** — use `random(0, 256)` to pick random colour values each time:
   ```cpp
   setColour(random(0, 256), random(0, 256), random(0, 256));
   delay(500);
   ```

4. **Mood light** — pick 5 of your favourite colours and have the LED slowly cycle through them

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| RGB | Red, Green, Blue — the three primary colours of light |
| Common cathode | The shared GND leg of an RGB LED |
| Function | A named block of code that does a specific job |
| Parameters | Values you pass into a function (like ingredients in a recipe) |
| Colour mixing | Combining R, G, B at different brightnesses to make any colour |

---

**Next up: [Lesson 08 — Night Light](../08-night-light/lesson.md)** — use a sensor to make a light that turns itself on in the dark!

# Lesson 03: Traffic Light

**You'll build:** A working 3-colour traffic light (Irish/UK style).  
**New idea:** Controlling multiple components and using variables.

**You'll learn:**
- Using variables to name pin numbers
- Controlling multiple outputs in sequence
- Comments to explain your code

---

## Background

Real traffic lights follow a strict sequence: red → red+amber → green → amber → red. We're going to replicate that with three LEDs. This lesson introduces **variables** — names you give to values so you don't have to remember numbers.

Instead of writing `digitalWrite(11, HIGH)` everywhere and forgetting which LED is which, you can write `digitalWrite(redPin, HIGH)` which is much easier to read and understand!

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Breadboard | 1 |
| Red LED | 1 |
| Yellow/Amber LED | 1 |
| Green LED | 1 |
| Resistors 220Ω | 3 |
| Jumper wires | 5 |
| USB cable | 1 |

---

## Wiring

### The Circuit

```
Pin 11 ──── Resistor 220Ω ──── RED LED (+) ──── RED LED (–) ──── GND
Pin 10 ──── Resistor 220Ω ──── YELLOW LED (+) ──── YELLOW LED (–) ──── GND
Pin 9  ──── Resistor 220Ω ──── GREEN LED (+) ──── GREEN LED (–) ──── GND
```

### Step-by-Step Breadboard Instructions

**Unplug Arduino before wiring!**

Place the three LEDs in a column on the breadboard, with a bit of space between them:

```
     a  b  c  d  e
 4  [ ][ ][ ][ ][ ]   <- Red LED long leg, col c
 5  [ ][ ][ ][ ][ ]   <- Red LED short leg, col c
 6  [ ][ ][ ][ ][ ]
 8  [ ][ ][ ][ ][ ]   <- Yellow LED long leg, col c
 9  [ ][ ][ ][ ][ ]   <- Yellow LED short leg, col c
10  [ ][ ][ ][ ][ ]
12  [ ][ ][ ][ ][ ]   <- Green LED long leg, col c
13  [ ][ ][ ][ ][ ]   <- Green LED short leg, col c
```

**Step 1:** Place the **red LED** with long leg in row 4 col c, short leg in row 5 col c.

**Step 2:** Place a **220Ω resistor** from row 2 col c to row 4 col c (row 4 connects to the LED's long leg).

**Step 3:** Wire row 2 col a → Arduino **Pin 11** (the red LED's control pin).

**Step 4:** Wire row 5 col a → Arduino **GND**.

**Step 5:** Repeat for **yellow LED** with rows 8–9, resistor at row 6–8, control wire to **Pin 10**, GND wire from row 9.

**Step 6:** Repeat for **green LED** with rows 12–13, resistor at row 10–12, control wire to **Pin 9**, GND wire from row 13.

### Connection Summary

| From | To |
|------|----|
| Arduino Pin 11 | 220Ω resistor → Red LED long leg |
| Red LED short leg | Arduino GND |
| Arduino Pin 10 | 220Ω resistor → Yellow LED long leg |
| Yellow LED short leg | Arduino GND |
| Arduino Pin 9 | 220Ω resistor → Green LED long leg |
| Green LED short leg | Arduino GND |

---

## The Code

```cpp
// Traffic light pin numbers
int redPin    = 11;
int yellowPin = 10;
int greenPin  =  9;

void setup() {
  pinMode(redPin,    OUTPUT);
  pinMode(yellowPin, OUTPUT);
  pinMode(greenPin,  OUTPUT);
}

void loop() {
  // --- RED: Stop ---
  digitalWrite(redPin, HIGH);
  delay(3000);

  // --- RED + YELLOW: Get ready ---
  digitalWrite(yellowPin, HIGH);
  delay(1000);

  // --- GREEN: Go ---
  digitalWrite(redPin,    LOW);
  digitalWrite(yellowPin, LOW);
  digitalWrite(greenPin,  HIGH);
  delay(3000);

  // --- YELLOW: Slow down ---
  digitalWrite(greenPin,  LOW);
  digitalWrite(yellowPin, HIGH);
  delay(1000);

  // --- Back to red ---
  digitalWrite(yellowPin, LOW);
}
```

---

## Code Explained

### Variables

```cpp
int redPin = 11;
```

This creates a **variable** called `redPin` and stores the number `11` in it. Now anywhere in the code you write `redPin`, the Arduino uses the number 11.

- `int` means "integer" — a whole number (no decimals)
- `redPin` is the name you chose (you could call it anything — `myRedLight`, `rLed`, etc.)
- `= 11` gives it the starting value

**Why use variables?** Imagine you wanted to move the red LED to pin 7. Without variables you'd have to find and change every line that says `11`. With a variable, you change it once at the top.

### Comments

```cpp
// --- RED: Stop ---
```

Lines starting with `//` are **comments**. The Arduino ignores them completely. They're just notes for humans reading the code. Use them to explain what you're doing — especially when you come back to your code weeks later and can't remember!

### The Sequence

```
loop() runs forever:

  RED on ──────────────────────────── 3 seconds
  RED on + YELLOW on ──────────────── 1 second
  RED off, YELLOW off, GREEN on ───── 3 seconds
  GREEN off, YELLOW on ────────────── 1 second
  YELLOW off ──────────────────────── (goes back to top)
```

---

## What to Expect

The three LEDs should cycle through the Irish/UK traffic light sequence. If they don't change in the right order, double-check which LED is plugged into which pin.

---

## Challenges

1. **Change the timing** — make the red phase last 5 seconds instead of 3
2. **US-style lights** — US traffic lights go red → green → yellow → red (no red+yellow phase). Change the code to match
3. **Add a pedestrian button** — using what you'll learn in Lesson 04, make the green phase cut short when a button is pressed (try reading ahead!)
4. **Night mode** — at night some traffic lights just flash amber. After 5 complete cycles, make it just flash the yellow LED on and off

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| Variable | A named box that stores a value |
| `int` | Data type for whole numbers |
| Comment (`//`) | A note in code that the Arduino ignores |
| Sequence | Doing things one after another in a specific order |

---

**Next up: [Lesson 04 — Push Button](../04-button/lesson.md)** — time to add an input!

# Lesson 02: External LED

**You'll build:** An LED circuit on a breadboard that flashes.  
**New idea:** You're building a real circuit for the first time!

**You'll learn:**
- How electricity flows through a circuit
- What a resistor does
- How to use a breadboard
- The difference between LED legs

---

## Background

In Lesson 01 we used the tiny built-in LED. Now we'll connect our own LED to the breadboard. This is exciting because you're actually building a **circuit** — a path for electricity to travel.

### How Electricity Flows

Think of electricity like water flowing through pipes:
- The Arduino's pin 9 is like a tap that you can turn on and off
- The resistor is like a narrow section of pipe that slows the flow
- The LED is like a special part of the pipe that glows when water (electricity) flows through it
- The GND pin is where the electricity returns

```
Pin 9 (5V) ──► [Resistor 220Ω] ──► [LED] ──► GND (0V)
```

The electricity **must** flow through the resistor first. Without it, too much electricity flows through the LED and it burns out. The 220Ω resistor is the right size to protect most LEDs.

### LED Legs

An LED has two legs, and they must be connected the right way:

```
        LED
       /   \
      /     \
  (–)|(       )|(+)
      \_____/
        |  |
        |  |
     short long
      leg  leg
     (–)   (+)
   cathode anode
```

- **Long leg (+)** = anode = positive = connect to power (through resistor)
- **Short leg (–)** = cathode = negative = connect to GND

If you put it in backwards, it won't light up (but it won't break either — just flip it around).

---

## Parts You Need

| Part | Quantity | From your kit |
|------|----------|--------------|
| Arduino Uno | 1 | Yes |
| Breadboard | 1 | Yes |
| LED (any colour) | 1 | Yes |
| Resistor 220Ω | 1 | Yes (red-red-brown bands) |
| Jumper wires | 3 | Yes |
| USB cable | 1 | Yes |

---

## Wiring

### The Circuit

```
Arduino Pin 9 ──── Resistor (220Ω) ──── LED long leg (+)
                                         LED short leg (–) ──── Arduino GND
```

### Step-by-Step Breadboard Instructions

**Always unplug your Arduino before changing the wiring!**

```
  Breadboard layout:

      a  b  c  d  e
  5  [ ][ ][ ][ ][ ]   <-- jumper wire from Pin 9 goes here (row 5, col a)
  6  [ ][ ][ ][ ][ ]   
  7  [ ][ ][ ][ ][ ]   <-- resistor goes from row 5 to row 7 (col c)
  8  [ ][ ][ ][ ][ ]
  9  [ ][ ][ ][ ][ ]   <-- LED long leg here (row 9, col c, same row as bottom of resistor)
 10  [ ][ ][ ][ ][ ]   <-- LED short leg here (row 10, col c)
 11  [ ][ ][ ][ ][ ]   <-- jumper wire from GND goes here (row 10, col a) -> GND
```

Do it in this order:

**Step 1:** Take your LED. Find the long leg (+). Push the long leg into **row 9, column c** and the short leg into **row 10, column c**.

**Step 2:** Take a 220Ω resistor. Push one leg into **row 5, column c** and the other leg into **row 9, column c**. The resistor is now in the same row as the LED's long leg — they're connected!

**Step 3:** Take a jumper wire. Push one end into **row 5, column a** (same row as the top of the resistor) and plug the other end into **pin 9** on the Arduino.

**Step 4:** Take another jumper wire. Push one end into **row 10, column a** (same row as the LED's short leg) and plug the other end into any **GND** pin on the Arduino.

**Step 5:** Plug in the USB cable.

### Connection Summary

| From | To |
|------|----|
| Arduino Pin 9 | Breadboard row 5 |
| Resistor leg 1 | Breadboard row 5 (same row as above) |
| Resistor leg 2 | Breadboard row 9 |
| LED long leg (+) | Breadboard row 9 (same row as resistor bottom) |
| LED short leg (–) | Breadboard row 10 |
| Arduino GND | Breadboard row 10 (same row as LED short leg) |

---

## The Code

Open the Arduino IDE and type this:

```cpp
void setup() {
  pinMode(9, OUTPUT);
}

void loop() {
  digitalWrite(9, HIGH);
  delay(500);
  digitalWrite(9, LOW);
  delay(500);
}
```

This is almost identical to Lesson 01, but now we're using **pin 9** instead of pin 13, and we've changed the delay to 500ms so it blinks faster.

Upload it and your LED should flash on and off twice a second!

---

## Code Explained

The only change from Lesson 01 is:
- `pinMode(9, OUTPUT)` — now we're using pin 9
- `delay(500)` — 500 milliseconds = half a second, so it blinks faster

Everything else is exactly the same logic.

---

## What to Expect

Your LED should blink on and off, half a second each. If it doesn't:

| Problem | Fix |
|---------|-----|
| LED doesn't light up at all | Check the LED is the right way round — long leg toward the resistor |
| LED stays on solidly (not blinking) | Code might not have uploaded — check the IDE |
| LED is very dim | Check your resistor value — make sure it's 220Ω not 10kΩ |
| Error uploading | Check Tools > Port is set correctly |

---

## Challenges

1. **Slower blink** — change `delay(500)` to `delay(2000)` and observe
2. **Different pin** — change pin 9 to pin 6 or pin 7 (remember to change it in BOTH places: `pinMode` and `digitalWrite`)
3. **Two LEDs** — add a second LED on pin 8 with its own resistor. Make one flash while the other is off:
   ```
   digitalWrite(9, HIGH);
   digitalWrite(8, LOW);
   delay(500);
   digitalWrite(9, LOW);
   digitalWrite(8, HIGH);
   delay(500);
   ```
4. **Heartbeat pattern** — make it flash twice quickly, then pause:
   - on 100ms, off 100ms, on 100ms, off 700ms... repeat

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| Circuit | A complete path for electricity to flow |
| Resistor | Limits how much electricity flows |
| Anode (+) | The positive leg of an LED (long leg) |
| Cathode (–) | The negative leg of an LED (short leg) |
| Ohm (Ω) | The unit of resistance |
| 220Ω | 220 ohms — the right resistor size for most LEDs |

---

**Next up: [Lesson 03 — Traffic Light](../03-traffic-light/lesson.md)** — three LEDs, one circuit!

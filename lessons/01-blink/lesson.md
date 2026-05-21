# Lesson 01: Blink — Your First Program

**You'll build:** A flashing LED using the built-in LED on your Arduino board.  
**No extra parts needed for this one!**

**You'll learn:**
- The structure of every Arduino program
- `setup()` and `loop()`
- `pinMode()`, `digitalWrite()`, and `delay()`

---

## Background

Every computer program in history started with "Hello, World!" — a program that just prints that message to show everything is working. For electronics, our "Hello, World" is making an LED blink. It proves your code runs and your board works.

Your Arduino has a tiny LED already built onto the board, labelled **L** or connected to **pin 13**. We'll use that one so you don't need any extra components.

---

## No Wiring Needed

Just plug your Arduino into your computer with the USB cable. That's it!

---

## The Code

Open the Arduino IDE and type this exactly:

```cpp
void setup() {
  pinMode(13, OUTPUT);
}

void loop() {
  digitalWrite(13, HIGH);
  delay(1000);
  digitalWrite(13, LOW);
  delay(1000);
}
```

Save it (Ctrl+S or Cmd+S), then click the **Upload** button (the arrow). Wait for it to say "Done uploading." at the bottom.

---

## Code Explained — Line by Line

### The two required functions

Every Arduino sketch **must** have these two functions. They're not optional:

```cpp
void setup() {
  // This runs ONCE when the Arduino powers on
}

void loop() {
  // This runs OVER AND OVER, forever, until power is removed
}
```

Think of `setup()` as your preparation — like putting on your shoes before going outside. You only do it once. `loop()` is the action that keeps repeating — like walking.

### `pinMode(13, OUTPUT)`

```cpp
pinMode(13, OUTPUT);
```

This tells the Arduino: "Pin 13 is going to be an **output** — I'll send electricity out of it."

- The first number (`13`) is the **pin number**
- `OUTPUT` means we're sending signals out (not reading from a sensor)

### `digitalWrite(13, HIGH)`

```cpp
digitalWrite(13, HIGH);
```

This turns pin 13 **ON** — it sends 5 volts out of the pin, which lights up the LED.

- `HIGH` means ON (5V)
- `LOW` means OFF (0V)

### `delay(1000)`

```cpp
delay(1000);
```

This makes the program **wait** before doing the next thing. The number is in **milliseconds**.

- 1000 milliseconds = 1 second
- 500 = half a second
- 2000 = 2 seconds

### Putting it together

```
loop() runs forever:
  ┌─────────────────────────────────────┐
  │ Turn pin 13 HIGH (LED on)           │
  │ Wait 1000ms (1 second)              │
  │ Turn pin 13 LOW (LED off)           │
  │ Wait 1000ms (1 second)              │
  └──────────────────────────────────── ┘  <-- goes back to top, repeating forever
```

---

## What to Expect

After uploading, the small LED labelled **L** on your Arduino board should flash on and off once per second. If it does — congratulations, you just wrote and ran your first program!

---

## Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| "Port not found" error | Arduino not recognised | Try a different USB port; try unplugging and replugging |
| Red error: `expected ';'` | Missing semicolon | Every statement ends with `;` — check your code |
| Nothing happens after upload | Board settings wrong | Check Tools > Board = Arduino Uno, Tools > Port = correct port |
| LED blinks but very fast | delay value too small | Make sure you typed `1000` not `10` |

---

## Challenges

Try changing the code to:

1. **Blink faster** — change both `delay(1000)` to `delay(200)`
2. **Blink slower** — change them to `delay(2000)`  
3. **Long then short** — make it on for 2 seconds and off for 0.1 seconds
4. **SOS signal** — SOS in Morse code is `... --- ...` (three short, three long, three short)

For the SOS challenge, here's a hint — you'll need more `digitalWrite` and `delay` lines in your `loop()`. Try to figure out how to do three short blinks followed by three long blinks!

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| `void` | The function doesn't give back a value |
| `setup()` | Runs once at start |
| `loop()` | Runs forever |
| `pinMode()` | Set a pin as INPUT or OUTPUT |
| `digitalWrite()` | Set a pin HIGH (on) or LOW (off) |
| `delay()` | Wait for a number of milliseconds |
| `HIGH` | 5 volts (on) |
| `LOW` | 0 volts (off) |

---

**Next up: [Lesson 02 — External LED](../02-external-led/lesson.md)** — we'll add a real circuit on the breadboard!

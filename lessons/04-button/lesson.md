# Lesson 04: Push Button

**You'll build:** Press a button to turn an LED on and off.  
**New idea:** Your program can now READ from the real world, not just write to it!

**You'll learn:**
- Digital inputs with `digitalRead()`
- `INPUT_PULLUP` — the easy way to wire a button
- `if` / `else` — making decisions in code

---

## Background

So far our programs have just *done things* — they've been sending electricity out of pins. Now we're going to *read* from a pin. That means we can respond to what's happening in the real world.

A button is the simplest input: pressed or not pressed. That's all. When you press it, electricity can flow through; when you release it, it can't.

### The Pull-up Trick

Here's a puzzle: if you connect a button between a pin and GND, what does the pin read when the button **isn't** pressed? Nothing. The pin is just floating in mid-air — it might read HIGH or LOW randomly, which is useless.

The fix is a **pull-up resistor**. This connects the pin to 5V through a large resistor (10kΩ), so when the button isn't pressed, the pin reads HIGH (5V). When you press the button, it connects the pin directly to GND, which "wins" and the pin reads LOW.

The brilliant news: the Arduino has a built-in pull-up resistor you can activate with one word in your code — `INPUT_PULLUP`.

```
With INPUT_PULLUP:
  Button NOT pressed: pin reads HIGH (pulled up to 5V internally)
  Button IS pressed:  pin reads LOW  (connected directly to GND)

This feels backwards at first! 
  HIGH = not pressed
  LOW  = pressed
```

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Breadboard | 1 |
| LED (any colour) | 1 |
| Resistor 220Ω | 1 |
| Push button | 1 |
| Jumper wires | 4 |
| USB cable | 1 |

---

## Wiring

### The Button

The push button has 4 legs. They connect in pairs:

```
  Button (top view):
  
  A ──┬──────┬── B
      │      │
     [ ]    [ ]    <- the switch gap (open until pressed)
      │      │
  C ──┴──────┴── D

  A connects to B always
  C connects to D always
  A/B connects to C/D only when button is pressed
```

Use legs on the **left side** (A and C) — one to the pin, one to GND.

### The Circuit

```
Arduino Pin 2 ──── Button leg A
                   Button leg C ──── Arduino GND

Arduino Pin 9 ──── Resistor 220Ω ──── LED long leg (+) ──── LED short leg (–) ──── GND
```

### Step-by-Step Breadboard Instructions

**Unplug Arduino before wiring!**

**Step 1:** Press the button across the middle gap of the breadboard so it straddles the gap (one pair of legs on each side). Let's say rows 8–10 with the button spanning the gap.

**Step 2:** Wire **row 8, left side, col a** → Arduino **Pin 2** (this is one side of the button).

**Step 3:** Wire **row 10, left side, col a** → Arduino **GND** (this is the other side of the button).

**Step 4:** Place your LED with long leg in row 3 col c, short leg in row 4 col c.

**Step 5:** Place a 220Ω resistor from row 1 col c to row 3 col c.

**Step 6:** Wire row 1 col a → Arduino **Pin 9**.

**Step 7:** Wire row 4 col a → Arduino **GND**.

### Connection Summary

| From | To |
|------|----|
| Arduino Pin 2 | One side of button |
| Other side of button | Arduino GND |
| Arduino Pin 9 | 220Ω resistor → LED long leg (+) |
| LED short leg (–) | Arduino GND |

---

## The Code

```cpp
int ledPin    = 9;
int buttonPin = 2;

void setup() {
  pinMode(ledPin,    OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP);
}

void loop() {
  if (digitalRead(buttonPin) == LOW) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }
}
```

---

## Code Explained

### `INPUT_PULLUP`

```cpp
pinMode(buttonPin, INPUT_PULLUP);
```

We set the button pin as an input, and activate the internal pull-up resistor. Now the pin reads HIGH when the button is not pressed, and LOW when it is pressed.

### `digitalRead()`

```cpp
digitalRead(buttonPin)
```

This **reads** whether a pin is HIGH or LOW. It gives back a value — either `HIGH` or `LOW` — that you can use in your code.

### `if` / `else`

```cpp
if (digitalRead(buttonPin) == LOW) {
  // do this if button IS pressed
} else {
  // do this if button is NOT pressed
}
```

`if` is how your program makes decisions. "If this condition is true, do this. Otherwise (else), do that."

The `==` means "is equal to". One `=` sets a value; two `==` checks if they're equal. This is a common mistake to watch out for!

```
  if (something == somethingElse) {
       ^^ notice two equals signs for comparison ^^
  }
```

### The Logic Flow

```
loop() runs forever:

  Read the button pin
     |
     ├── Is it LOW? (button pressed)
     │      └── YES: turn LED ON
     │
     └── Is it LOW? (button pressed)
            └── NO:  turn LED OFF
```

---

## What to Expect

When you hold the button down, the LED lights up. When you release it, the LED goes off. Simple and satisfying!

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| LED is always on | Button wiring might be wrong — check which legs you're using |
| LED never turns on | Try pressing the button from different angles; check the button orientation |
| LED flickers | That's ok! It means the button is working; for a "clean" button press, search for "debouncing" |

---

## Challenges

1. **Flip it** — make the LED normally ON and turn OFF when you press the button (swap HIGH and LOW in the if/else)

2. **Toggle** — press once to turn ON, press again to turn OFF. This is trickier — here's a starter hint:
   ```cpp
   bool ledState = false;  // track whether LED is on or off
   bool lastButton = HIGH; // track previous button state
   
   // In loop, detect when button CHANGES from HIGH to LOW:
   bool currentButton = digitalRead(buttonPin);
   if (currentButton == LOW && lastButton == HIGH) {
     ledState = !ledState;  // flip the state
     digitalWrite(ledPin, ledState ? HIGH : LOW);
   }
   lastButton = currentButton;
   delay(50);  // prevents bouncing
   ```

3. **Two buttons** — add a second button on pin 3. Button 1 turns LED on. Button 2 turns LED off. (This is more like a real on/off switch!)

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| `digitalRead()` | Reads whether a pin is HIGH or LOW |
| `INPUT_PULLUP` | Pin reads HIGH by default; pressing button pulls it LOW |
| `if` | Runs code only when a condition is true |
| `else` | Runs code when the `if` condition is NOT true |
| `==` | "Is equal to?" (two equals signs = comparison) |
| `=` | "Set this value" (one equals sign = assignment) |

---

**Next up: [Lesson 05 — Dimmer Switch](../05-potentiometer/lesson.md)** — analog inputs and controlling brightness!

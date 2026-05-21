# Lesson 06: Buzzer Music

**You'll build:** A buzzer that plays "Mary Had a Little Lamb".  
**New idea:** Sound is just vibrations — we can control how fast things vibrate to make different notes!

**You'll learn:**
- Making sounds with `tone()`
- Arrays — a list of values
- `for` loops — doing something a set number of times
- `#define` — giving names to constants

---

## Background

Sound is made by vibrations in the air. A buzzer has a tiny disc inside that flexes back and forth — that vibration moves air, and air movement is sound.

The **frequency** of a sound is how many times per second it vibrates. Higher frequency = higher pitch.

- Low C (C4): 262 vibrations per second (262 Hz)
- Middle A (A4): 440 Hz — this is the standard tuning note
- High C (C5): 523 Hz

The Arduino's `tone()` function makes a pin switch HIGH and LOW at a specific frequency, which vibrates the buzzer at exactly that rate. Very clever!

### Passive vs Active Buzzer

Your Elegoo kit includes **two types** of buzzer:
- **Active buzzer** — just supply power and it beeps at a fixed pitch
- **Passive buzzer** — you control the frequency, so you can play different notes

**We need the passive buzzer for this lesson.** It usually has a green circuit board on the bottom. The active buzzer has a black sticker. Check both — if you're not sure, try one; if only one pitch comes out regardless of your code, swap to the other.

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Breadboard | 1 |
| Passive buzzer | 1 |
| Jumper wires | 2 |
| USB cable | 1 |

---

## Wiring

The buzzer has 2 legs (or pins):
- **Positive (+)** leg — the longer one, or marked with `+`
- **Negative (–)** leg — shorter, or unmarked

### The Circuit

```
Arduino Pin 8 ──── Buzzer (+) long leg
Arduino GND   ──── Buzzer (–) short leg
```

### Step-by-Step

**Step 1:** Push the buzzer into the breadboard (say rows 5–6, col c).

**Step 2:** Wire the **long/+ leg** (row 5) → Arduino **Pin 8**.

**Step 3:** Wire the **short/– leg** (row 6) → Arduino **GND**.

That's it — buzzer is simple to wire!

---

## The Code

```cpp
#define NOTE_C4  262
#define NOTE_D4  294
#define NOTE_E4  330
#define NOTE_F4  349
#define NOTE_G4  392
#define NOTE_A4  440
#define NOTE_B4  494
#define NOTE_C5  523

int buzzerPin = 8;

// Mary Had a Little Lamb -- notes
int melody[] = {
  NOTE_E4, NOTE_D4, NOTE_C4, NOTE_D4,
  NOTE_E4, NOTE_E4, NOTE_E4,
  NOTE_D4, NOTE_D4, NOTE_D4,
  NOTE_E4, NOTE_G4, NOTE_G4,
  NOTE_E4, NOTE_D4, NOTE_C4, NOTE_D4,
  NOTE_E4, NOTE_E4, NOTE_E4, NOTE_E4,
  NOTE_D4, NOTE_D4, NOTE_E4, NOTE_D4,
  NOTE_C4
};

int noteLength = 300;  // milliseconds per note

void setup() {
  pinMode(buzzerPin, OUTPUT);
}

void loop() {
  int numNotes = sizeof(melody) / sizeof(melody[0]);

  for (int i = 0; i < numNotes; i++) {
    tone(buzzerPin, melody[i], noteLength);
    delay(noteLength + 30);
    noTone(buzzerPin);
  }

  delay(2000);
}
```

---

## Code Explained

### `#define`

```cpp
#define NOTE_C4  262
```

`#define` creates a **named constant**. Everywhere in your code that says `NOTE_C4`, the Arduino substitutes `262`. It's like a find-and-replace that happens before the code even runs.

We use `#define` instead of variables for things that never change — musical note frequencies are always the same!

### Arrays

```cpp
int melody[] = {
  NOTE_E4, NOTE_D4, NOTE_C4, ...
};
```

An **array** is a list of values stored under one name. `melody[]` is a list of integers (the note frequencies).

- Square brackets `[]` show it's an array
- The values go inside curly braces `{}`
- Each value is separated by a comma

You access individual values using their **index** (position), starting at 0:
```cpp
melody[0]  // first note: NOTE_E4 = 330
melody[1]  // second note: NOTE_D4 = 294
melody[7]  // eighth note
```

### `sizeof()` — How Long Is the Array?

```cpp
int numNotes = sizeof(melody) / sizeof(melody[0]);
```

`sizeof(melody)` gives the total memory size of the array in bytes. `sizeof(melody[0])` gives the size of one element. Dividing them gives the number of elements — the length of the melody.

This is a common trick because arrays in C++ don't know their own length!

### `for` Loop

```cpp
for (int i = 0; i < numNotes; i++) {
  tone(buzzerPin, melody[i], noteLength);
  delay(noteLength + 30);
  noTone(buzzerPin);
}
```

A `for` loop repeats code a specific number of times. Breaking it down:

```cpp
for (start; condition; step) {
    // code to repeat
}
```

- **Start:** `int i = 0` — create a counter variable `i` starting at 0
- **Condition:** `i < numNotes` — keep going while `i` is less than the number of notes
- **Step:** `i++` — add 1 to `i` after each round (`i++` is shorthand for `i = i + 1`)

So the loop runs for `i = 0, 1, 2, 3, ... numNotes-1` — playing every note in the array!

### `tone()` and `noTone()`

```cpp
tone(buzzerPin, melody[i], noteLength);
```

- First argument: which pin
- Second argument: frequency in Hz
- Third argument: how long to play it in milliseconds

```cpp
noTone(buzzerPin);
```

Stops any playing tone on that pin.

---

## What to Expect

You should hear "Mary Had a Little Lamb" playing repeatedly with a 2-second gap between repetitions. If you hear random beeping or nothing, try swapping to the other buzzer (active vs passive).

---

## Challenges

1. **Change the speed** — double `noteLength` to 600 for a slower version, or halve it to 150 for a faster version

2. **Add a second melody** — after the 2 second delay, play a different song. Look up the notes to "Happy Birthday" or "Twinkle Twinkle" online and add them

3. **Button trigger** — add a button (from Lesson 04). Only play the melody when the button is held down:
   ```cpp
   if (digitalRead(buttonPin) == LOW) {
     // play the melody
   }
   ```

4. **Doorbell** — combine with Lesson 04. Press a button once and it plays the melody once, then stops until you press it again

5. **Your own song** — look up the frequencies for notes you know and create your own melody array!

---

## Note Frequency Reference

| Note | Frequency |
|------|-----------|
| C4 (middle C) | 262 Hz |
| D4 | 294 Hz |
| E4 | 330 Hz |
| F4 | 349 Hz |
| G4 | 392 Hz |
| A4 | 440 Hz |
| B4 | 494 Hz |
| C5 | 523 Hz |
| D5 | 587 Hz |
| E5 | 659 Hz |

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| Frequency | How many times per second something vibrates (Hz) |
| `tone()` | Makes a pin vibrate at a set frequency (plays a note) |
| `noTone()` | Stops the tone |
| Array | A list of values stored under one name |
| Index | The position of an item in an array (starts at 0) |
| `for` loop | Repeats code a set number of times using a counter |
| `i++` | Adds 1 to the variable `i` |
| `#define` | Names a constant value |

---

**Next up: [Lesson 07 — RGB LED](../07-rgb-led/lesson.md)** — mix any colour you like!

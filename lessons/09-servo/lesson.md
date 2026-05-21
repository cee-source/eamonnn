# Lesson 09: Servo Motor

**You'll build:** A motor arm that sweeps back and forth from 0° to 180°.  
**New idea:** Using a library — code someone else wrote that you can use in your own program!

**You'll learn:**
- What a servo motor is and how it differs from a regular motor
- `#include` — importing a library
- Creating objects and calling methods
- Controlling position with a number (the angle)

---

## Background

A **servo motor** is a special type of motor that can turn to a specific angle and hold it. Unlike a regular DC motor that just spins around and around, you tell a servo "go to 90 degrees" and it moves there and stays.

Inside the servo is:
- A DC motor
- Gears (to slow it down and increase strength)
- A sensor that measures the current angle
- Electronics that compare where it is to where you want it to go

The range is 0° to 180° — a half circle.

Servos are used in RC cars (steering), robotic arms, camera holders, and much more.

### What Is a Library?

A **library** is a collection of code that someone else wrote and packaged up for others to use. Instead of figuring out exactly how to pulse the servo signal yourself, you use the `Servo` library which does it for you.

Think of it like using a calculator — you don't need to know how the calculator works internally, you just need to know how to press the buttons.

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Micro servo motor (SG90 or similar) | 1 |
| Jumper wires | 3 |
| USB cable | 1 |

The servo motor has a cable attached with 3 wires:
- **Brown/Black** = GND
- **Red** = 5V power
- **Orange/Yellow/White** = Signal (control)

---

## Wiring

Servos draw a fair bit of power, so we'll connect power directly to the Arduino's 5V and GND pins.

### The Circuit

```
Servo brown/black wire ──── Arduino GND
Servo red wire         ──── Arduino 5V
Servo orange wire      ──── Arduino Pin 9
```

You don't need the breadboard for this lesson — you can plug the servo wires directly into the Arduino pins using jumper wires!

### Step-by-Step

**Step 1:** Take three jumper wires. Connect one end of each to the servo's three pins (you might need to use the female-to-male jumper wires from your kit, or push a male jumper into the servo's plug).

**Step 2:** Connect the **brown/black** wire → Arduino **GND**.

**Step 3:** Connect the **red** wire → Arduino **5V**.

**Step 4:** Connect the **orange/yellow** wire → Arduino **Pin 9**.

### Connection Summary

| Servo wire | Arduino |
|-----------|---------|
| Brown / Black (GND) | GND |
| Red (Power) | 5V |
| Orange / Yellow / White (Signal) | Pin 9 |

---

## The Code

```cpp
#include <Servo.h>

Servo myServo;

int servoPin = 9;

void setup() {
  myServo.attach(servoPin);
}

void loop() {
  // Sweep from 0 to 180 degrees
  for (int angle = 0; angle <= 180; angle++) {
    myServo.write(angle);
    delay(15);
  }

  // Sweep back from 180 to 0 degrees
  for (int angle = 180; angle >= 0; angle--) {
    myServo.write(angle);
    delay(15);
  }

  delay(500);
}
```

---

## Code Explained

### `#include <Servo.h>`

```cpp
#include <Servo.h>
```

This tells the Arduino IDE to import the Servo library. The `< >` angle brackets mean it's a built-in library (it comes with the IDE). If a library needed to be downloaded separately, you'd use `" "` quotes.

You must put `#include` at the very top of your sketch, before anything else.

### Creating a Servo Object

```cpp
Servo myServo;
```

This creates a **servo object** called `myServo`. An object is a way of bundling code and data together. The `Servo` library defines what a servo object is and everything it can do.

You could call it anything: `armServo`, `doorServo`, `s` — but `myServo` is clear.

### `myServo.attach(servoPin)`

```cpp
myServo.attach(servoPin);
```

Connects the servo object to a physical pin. The `.` (dot) is how you call functions that belong to an object — these are called **methods**. 

`attach()` tells the library "this is the pin where the servo is connected."

### `myServo.write(angle)`

```cpp
myServo.write(angle);
```

Tells the servo to move to a specific angle (0–180 degrees).

### `i--` in the Reverse Loop

```cpp
for (int angle = 180; angle >= 0; angle--) {
```

This `for` loop counts **down** instead of up:
- Start at 180
- Keep going while `angle >= 0` (greater than or equal to 0)
- `angle--` subtracts 1 each time (opposite of `angle++`)

### The 15ms Delay

```cpp
myServo.write(angle);
delay(15);
```

We move the servo 1 degree at a time with a 15ms pause. This makes it sweep smoothly rather than jumping straight to 180°. Servos need a moment to physically reach the commanded position.

---

## What to Expect

The servo arm will sweep slowly from one end to the other and back, repeating forever. It should make a gentle whirring sound as it moves.

If the servo just twitches or vibrates, check your wiring — especially that power is connected correctly.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Servo just buzzes/vibrates | Power issue — check 5V and GND connections |
| Servo moves but to wrong angles | Try `myServo.write(0)` and `myServo.write(180)` separately to test the range |
| Upload fails with servo connected | Disconnect servo, upload, then reconnect — servo sometimes interferes |
| Servo gets hot | It's working against something (being held back) — don't force it |

---

## Challenges

1. **Potentiometer control** — use a potentiometer (from Lesson 05) to control the servo angle:
   ```cpp
   int potValue = analogRead(A0);
   int angle    = map(potValue, 0, 1023, 0, 180);
   myServo.write(angle);
   delay(15);
   ```
   Turn the knob to point the servo arm anywhere from 0° to 180°!

2. **Button position** — add two buttons. One moves the servo to 0°, the other to 180°. Or make it move in 10-degree steps each time you press.

3. **Three positions** — make the servo go to specific positions for "open", "halfway", and "closed" with delays in between. Think of a servo-powered latch!

4. **Distance pointer** — combine with Lesson 10 (coming up). Use the distance sensor reading to control what angle the servo points to. Like a gauge on a dashboard!

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| Servo motor | A motor that turns to a specific angle and holds it |
| Library | Packaged code written by someone else that you can use |
| `#include` | Imports a library into your sketch |
| Object | A bundle of code and data that represents something (like a servo) |
| Method | A function that belongs to an object (called with a `.`) |
| `attach()` | Connects a servo object to a physical pin |
| `write()` | Tells the servo which angle to go to |
| `i--` | Subtracts 1 from a variable (opposite of `i++`) |

---

**Next up: [Lesson 10 — Parking Sensor](../10-distance-sensor/lesson.md)** — measure distance with sound and make a beeping alarm!

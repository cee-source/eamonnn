# Lesson 10: Parking Sensor

**You'll build:** A sensor that beeps faster the closer an object gets — just like a car parking sensor!  
**New idea:** Measuring the real world using sound waves, and writing helper functions.

**You'll learn:**
- How the HC-SR04 ultrasonic sensor works
- `pulseIn()` — measuring the time of a pulse
- Distance calculation with maths
- Writing a helper function that *returns* a value

---

## Background

The HC-SR04 sensor measures distance using **ultrasonic sound** — the same principle as how bats navigate in the dark!

Here's how it works:

```
     HC-SR04
  ┌───────────┐
  │  (T) (R)  │
  └───────────┘
     │    │
  Transmit Receive

1. TRIG pin sends a brief ultrasonic pulse (too high-pitched to hear)
2. The pulse bounces off a nearby object
3. ECHO pin receives the returning pulse
4. We measure how long the echo took to return
5. Use the speed of sound to calculate distance
```

Sound travels at about **343 metres per second** in air. If the echo takes 2000 microseconds, the sound travelled:

```
distance = (time × speed) / 2
         = (0.002 seconds × 343 m/s) / 2
         = 0.343 metres
         = 34.3 cm

(We divide by 2 because the sound went THERE and came BACK)
```

In simpler terms: distance in cm = duration in microseconds ÷ 58.

---

## Parts You Need

| Part | Quantity |
|------|----------|
| Arduino Uno | 1 |
| Breadboard | 1 |
| HC-SR04 ultrasonic sensor | 1 |
| Passive buzzer | 1 |
| Jumper wires | 6 |
| USB cable | 1 |

---

## The HC-SR04 Pins

The sensor module has 4 pins:

| Pin | Function |
|-----|----------|
| VCC | Power (5V) |
| TRIG | Trigger — sends the pulse |
| ECHO | Echo — receives the reflection |
| GND | Ground |

---

## Wiring

### The Circuit

```
Arduino 5V   ──── HC-SR04 VCC
Arduino GND  ──── HC-SR04 GND
Arduino Pin 9 ─── HC-SR04 TRIG
Arduino Pin 10 ── HC-SR04 ECHO

Arduino Pin 8 ─── Buzzer (+) long leg
Arduino GND   ─── Buzzer (–) short leg
```

### Step-by-Step Breadboard Instructions

**Unplug Arduino before wiring!**

**Step 1:** Push the HC-SR04 into the breadboard (4 pins in a row, rows 3–6 col c).

**Step 2:** Wire **VCC row** → Arduino **5V**.

**Step 3:** Wire **GND row** → Arduino **GND**.

**Step 4:** Wire **TRIG row** → Arduino **Pin 9**.

**Step 5:** Wire **ECHO row** → Arduino **Pin 10**.

**Step 6:** Push the passive buzzer into the breadboard (rows 10–11). Wire long leg (+) row → Arduino **Pin 8**, short leg (–) row → Arduino **GND**.

### Connection Summary

| From | To |
|------|----|
| Arduino 5V | HC-SR04 VCC |
| Arduino GND | HC-SR04 GND |
| Arduino Pin 9 | HC-SR04 TRIG |
| Arduino Pin 10 | HC-SR04 ECHO |
| Arduino Pin 8 | Buzzer long leg (+) |
| Arduino GND | Buzzer short leg (–) |

---

## The Code

```cpp
int trigPin   =  9;
int echoPin   = 10;
int buzzerPin =  8;

void setup() {
  pinMode(trigPin,   OUTPUT);
  pinMode(echoPin,   INPUT);
  pinMode(buzzerPin, OUTPUT);
  Serial.begin(9600);
}

long getDistance() {
  // Send a 10-microsecond pulse on TRIG
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Measure how long ECHO stays HIGH
  long duration = pulseIn(echoPin, HIGH);

  // Convert to centimetres
  long distance = duration / 58;
  return distance;
}

void loop() {
  long distance = getDistance();

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  // Beep faster as object gets closer (like a car parking sensor)
  if (distance < 5) {
    tone(buzzerPin, 1000);
    delay(80);
    noTone(buzzerPin);
    delay(30);
  } else if (distance < 15) {
    tone(buzzerPin, 800);
    delay(100);
    noTone(buzzerPin);
    delay(150);
  } else if (distance < 30) {
    tone(buzzerPin, 600);
    delay(100);
    noTone(buzzerPin);
    delay(400);
  } else {
    noTone(buzzerPin);
    delay(200);
  }
}
```

---

## Code Explained

### A Function That Returns a Value

```cpp
long getDistance() {
  ...
  return distance;
}
```

Until now, our functions were `void` — they didn't give back a result. This function is different: it returns a `long` (a whole number that can be very large).

- `long` is like `int` but can hold bigger numbers (useful for microseconds!)
- `return distance;` sends the value back to whoever called the function

You call it like this:
```cpp
long distance = getDistance();
```

The value that `getDistance()` returns gets stored in your local variable `distance`.

### `delayMicroseconds()`

```cpp
delayMicroseconds(10);
```

Like `delay()` but in **microseconds** (millionths of a second) instead of milliseconds. We need to send a pulse that's exactly 10 microseconds long — too fast for `delay()`.

```
1 second = 1,000 milliseconds = 1,000,000 microseconds
```

### Triggering the Sensor

```cpp
digitalWrite(trigPin, LOW);
delayMicroseconds(2);
digitalWrite(trigPin, HIGH);
delayMicroseconds(10);
digitalWrite(trigPin, LOW);
```

To trigger the sensor:
1. Make sure TRIG is LOW first (clean start)
2. Pull it HIGH for exactly 10 microseconds
3. Pull it LOW again

This sends out 8 ultrasonic pulses automatically.

### `pulseIn()`

```cpp
long duration = pulseIn(echoPin, HIGH);
```

`pulseIn()` waits for the ECHO pin to go HIGH, then measures how many microseconds it stays HIGH before going LOW again. That duration is the time the sound wave took to travel out and back.

### The Distance Formula

```cpp
long distance = duration / 58;
```

Sound travels at roughly 343 m/s = 0.0343 cm/μs. For a round trip (out and back), we use:

```
distance (cm) = duration (μs) × 0.0343 / 2
              ≈ duration / 58
```

### `else if` — Multiple Conditions

```cpp
if (distance < 5) {
  // very close
} else if (distance < 15) {
  // close
} else if (distance < 30) {
  // medium
} else {
  // far
}
```

`else if` lets you check multiple conditions in a chain. The Arduino tests them in order and runs the first one that's true. If none match, `else` catches everything else.

---

## What to Expect

Open the Serial Monitor and move your hand toward and away from the sensor. You should see the distance in centimetres update in real time. When you get within 30cm, beeping starts. The closer you get, the faster it beeps. Under 5cm, it's almost a solid tone!

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Distance reads 0 constantly | Check TRIG/ECHO pins aren't swapped |
| Distance reads very large numbers | The echo isn't returning — make sure nothing is absorbing the sound (soft materials don't reflect well) |
| Erratic readings | Keep the sensor level and pointed at a flat surface |
| No buzzer sound | Check passive buzzer orientation and pin connections |

---

## Challenges

1. **LED bar** — add 3 LEDs. Green when far, yellow when medium, red when close. Update them based on distance.

2. **Servo pointer** — combine with Lesson 09. Use the servo as a "distance gauge" — point to 0° when far, 180° when very close:
   ```cpp
   int angle = map(distance, 0, 50, 180, 0);
   angle = constrain(angle, 0, 180);
   myServo.write(angle);
   ```

3. **Measure things** — measure the width of your desk, the height of your ceiling, the distance to the wall. How accurate is the sensor?

4. **Security sensor** — if something comes closer than 20cm, play an alarm on the buzzer for 3 seconds! Use a flag variable to track whether the alarm is already ringing.

5. **Two sensors** — if you have a second HC-SR04, point one forward and one sideways. Print both distances and beep based on whichever is closer.

---

## New Words You Learned

| Word | Meaning |
|------|---------|
| Ultrasonic | Sound at a frequency too high for humans to hear |
| `pulseIn()` | Measures how long a pin stays HIGH or LOW |
| `delayMicroseconds()` | Waits for a number of microseconds (millionths of a second) |
| `return` | Sends a value back from a function |
| `long` | A whole number data type that can hold very large values |
| `else if` | Tests a second condition if the first `if` was false |
| `constrain()` | Keeps a value within a minimum and maximum range |

---

## What's Next?

Congratulations, Eamonn! You've completed all 10 lessons and learned:

- How to write Arduino programs from scratch
- How circuits work on a breadboard
- Digital and analog inputs and outputs
- Variables, functions, loops, arrays, and libraries
- How to use sensors, motors, LEDs, and sound

Here are some project ideas that combine everything you've learned:

| Project | What it uses |
|---------|-------------|
| **Simon Says game** | 4 LEDs, 4 buttons, buzzer — memorise and repeat patterns |
| **Automatic plant waterer** | Moisture sensor, relay, water pump |
| **Mini weather station** | DHT11 sensor, LCD display — temperature and humidity |
| **Robot arm** | 2–3 servos, potentiometers to control each joint |
| **Reaction timer** | LED, button — how fast can you press when the light comes on? |
| **Laser trip wire alarm** | Laser pointer, LDR, buzzer |

The skills you have now are the foundation for all of these. Happy building!

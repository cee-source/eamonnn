# Lesson 00: Getting Started

Before we build anything, let's get to know our tools.

---

## What Is an Arduino?

An Arduino is a tiny computer that you can program to control lights, motors, sensors, and all kinds of gadgets. Unlike your games computer, it doesn't have a screen or keyboard — but it's connected to the **real world** through its **pins** (the small metal holes along its edges).

When you write code and send it to the Arduino, it remembers your program and runs it every single time it powers on. You could take out the USB cable, plug in a battery, and your gadget keeps working!

---

## Meet Your Arduino Uno

```
                        Arduino Uno (top view)
                   ___________________________________
                  |  [ ] [ ] [ ] [ ] [ ] [ ] [ ] [ ] |  <-- Digital pins 0-13
                  |                                   |      (and GND, 5V, 3.3V)
                  |    [USB port]   [Power jack]      |
                  |   ___________                     |
    Analog pins  |  |           |                    |
    A0 - A5  --> |  |ATmega328P |   [ ] RESET        |
                  |  |___________|                    |
                  |___________________________________|
```

The important parts right now:

| Part | What it does |
|------|-------------|
| USB port | Connects to your computer to upload programs, also powers the board |
| Digital pins 0–13 | Can be ON or OFF (like a light switch) |
| Analog pins A0–A5 | Can read values from sensors (0 to 1023) |
| 5V pin | Gives 5 volts of power to components |
| GND pins | Ground — the "return path" for electricity |
| Built-in LED | A tiny LED already on the board, connected to pin 13 |

---

## What Is a Breadboard?

A breadboard lets you build circuits **without soldering**. Push wires and components into the holes and they connect electrically on the inside.

```
     Breadboard (top view)
  
  [+]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[+]  <-- Power rail (+), all holes connected
  [–]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[–]  <-- Ground rail (–), all holes connected
  
      a  b  c  d  e     f  g  h  i  j
  1 [ ][ ][ ][ ][ ]   [ ][ ][ ][ ][ ]
  2 [ ][ ][ ][ ][ ]   [ ][ ][ ][ ][ ]    <- each ROW (a–e) is connected together
  3 [ ][ ][ ][ ][ ]   [ ][ ][ ][ ][ ]       and each ROW (f–j) is connected together
  4 [ ][ ][ ][ ][ ]   [ ][ ][ ][ ][ ]
  5 [ ][ ][ ][ ][ ]   [ ][ ][ ][ ][ ]
     ↑               ↑
   Left half        Right half
   (separate)       (separate)
```

**The rules:**
- Holes in the **same row** (a–e, or f–j) are connected to each other
- The **middle gap** separates the left and right halves — nothing crosses it
- The **+ rail** (red line) is for power (5V from Arduino)
- The **– rail** (blue line) is for Ground (GND from Arduino)

---

## Installing the Arduino IDE

The Arduino IDE is the program where you write your code and send it to your board.

1. Go to **arduino.cc/en/software** on your computer
2. Download the version for your operating system (Windows, Mac, or Linux)
3. Run the installer and click through it
4. Plug in your Arduino with the USB cable
5. Open the Arduino IDE
6. Click **Tools > Board** and choose **"Arduino Uno"**
7. Click **Tools > Port** and choose the port that appeared when you plugged in the Arduino
   - On Windows it looks like `COM3` or `COM4`
   - On Mac it looks like `/dev/cu.usbmodem...`

If the Arduino has a small green or orange LED glowing steadily, it's powered and ready!

---

## The Arduino IDE Layout

```
  ┌─────────────────────────────────────────────────────┐
  │  [✓ Verify]  [→ Upload]   sketch_name               │
  ├─────────────────────────────────────────────────────┤
  │                                                      │
  │   void setup() {                                     │  <-- Code editor
  │     // your code here                                │      (write here)
  │   }                                                  │
  │                                                      │
  │   void loop() {                                      │
  │     // your code here                                │
  │   }                                                  │
  │                                                      │
  ├─────────────────────────────────────────────────────┤
  │  Done compiling.                                     │  <-- Messages area
  │  Sketch uses 924 bytes of program storage space.     │      (errors show here)
  └─────────────────────────────────────────────────────┘
```

- **Verify (tick)** — checks your code for mistakes without uploading
- **Upload (arrow)** — sends your code to the Arduino
- **Messages area** — shows errors in red; read them carefully, they usually tell you what's wrong

---

## Parts in Your Kit We'll Use

| Component | Picture hint | What it does |
|-----------|-------------|-------------|
| Arduino Uno R3 | Green board with USB port | The brain — runs your programs |
| Breadboard | White rectangle with holes | Holds components, no soldering needed |
| Jumper wires | Colourful cables with pins | Connect things together |
| LEDs | Small bulb, two legs | Lights up when electricity flows through |
| Resistors | Small cylinder with colour bands | Limits how much electricity flows |
| Push buttons | Small square with 4 legs | An input — you press them |
| Potentiometer | Blue box with a knob | Controls voltage with a twist |
| Photoresistor (LDR) | Small clear disc | Changes resistance based on light level |
| Passive buzzer | Small black disc | Makes sounds |
| RGB LED | 4-legged LED | One LED that makes any colour |
| Servo motor | Small motor with a horn | Turns to a specific angle |
| HC-SR04 | Module with two silver cylinders | Measures distance using sound |

---

## How Resistors Work (and How to Read Them)

LEDs (and many other components) can be damaged by too much electricity. A **resistor** limits the flow, like a narrow pipe limits water flow.

Resistors have **colour bands** that tell you their value in ohms (Ω):

```
  ┌──────────────┐
  │  ┃ ┃   ┃ ┃  │   4-band resistor example
  └──────────────┘
     ↑ ↑   ↑ ↑
     │ │   │ └── Multiplier band
     │ │   └──── Second digit
     │ └──────── First digit
     └────────── (tolerance — ignore for now)
```

The resistors we'll use most often:

| Resistance | Colour bands | Used for |
|-----------|-------------|---------|
| 220 Ω | Red – Red – Brown | Protecting LEDs |
| 10,000 Ω (10kΩ) | Brown – Black – Orange | Buttons and sensors |

Don't worry about memorising these — just check the label on the packet or count from the bag you got them in.

---

## Ready?

You're all set! Head to **Lesson 01** and write your very first Arduino program.

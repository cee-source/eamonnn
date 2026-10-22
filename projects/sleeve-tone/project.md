# Sleeve Tone Device

Hold a hidden button → a high-pitched tone plays from a hidden speaker.
Release the button → silence.

The tone is 17,500 Hz — this is the "mosquito frequency". At this pitch,
your ears can't figure out which direction the sound is coming from,
so people look around confused.

---

## Parts

| Part | From |
|------|------|
| Arduino Nano | Elegoo kit |
| Passive buzzer (no sticker on top) | Elegoo kit |
| Tactile push button | Elegoo kit |
| Jumper wires | Elegoo kit |
| Small USB power bank | Your own (any phone charging bank) |
| Micro-USB cable | Elegoo kit |

> **Passive vs Active buzzer:** The passive buzzer has no label sticker on top.
> The active one has a black sticker. You need the PASSIVE one so `tone()` works.

---

## Wiring

```
Arduino Nano
   Pin 2  ──────── Button leg A
   GND    ──────── Button leg B
   
   Pin 9  ──────── Buzzer + (long leg)
   GND    ──────── Buzzer – (short leg)
   
   USB    ──────── USB power bank
```

Run a long wire from pin 2 and GND to a button near your hand.
Put the Nano + buzzer somewhere else in your sleeve.
The power bank can sit in a pocket.

---

## Code

File: `code/sleeve_tone/sleeve_tone.ino`

Upload it to the Nano using the Arduino IDE (Tools → Board: Arduino Nano,
Processor: ATmega328P Old Bootloader if needed).

---

## How it works

- `INPUT_PULLUP` means the button reads HIGH when not pressed, LOW when pressed.
- `tone(pin, 17500)` plays a 17,500 Hz square wave on pin 9.
- `noTone(pin)` stops it.
- No `delay()` needed — the loop checks the button constantly.

// Sleeve Tone Device
// Hold the button → plays a high-pitched tone (hard to locate)
// Release the button → silence
//
// Wiring:
//   Button: one leg → pin 2, other leg → GND
//   Passive buzzer: + (long leg) → pin 9, – (short leg) → GND
//   Power: USB power bank → Nano USB port

int buttonPin = 2;
int speakerPin = 9;

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);
}

void loop() {
  if (digitalRead(buttonPin) == LOW) {
    tone(speakerPin, 17500);   // 17,500 Hz — hard to locate
  } else {
    noTone(speakerPin);
  }
}

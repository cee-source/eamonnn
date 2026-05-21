// Lesson 06: Buzzer Music
// Plays "Mary Had a Little Lamb" on a passive buzzer.
//
// Wiring:
//   Pin 8 --> Buzzer long leg (+)
//   GND   --> Buzzer short leg (-)
//
// Use the PASSIVE buzzer (green circuit board underneath).
// The active buzzer (black sticker) will only beep one note.

// Musical note frequencies in Hz
#define NOTE_C4  262
#define NOTE_D4  294
#define NOTE_E4  330
#define NOTE_F4  349
#define NOTE_G4  392
#define NOTE_A4  440
#define NOTE_B4  494
#define NOTE_C5  523

int buzzerPin = 8;

// Mary Had a Little Lamb
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
  // sizeof(array) / sizeof(one element) = number of elements
  int numNotes = sizeof(melody) / sizeof(melody[0]);

  for (int i = 0; i < numNotes; i++) {
    tone(buzzerPin, melody[i], noteLength);  // play note
    delay(noteLength + 30);                  // wait for note to finish + small gap
    noTone(buzzerPin);                       // stop cleanly between notes
  }

  delay(2000);  // pause before repeating
}

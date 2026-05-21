// Lesson 04: Push Button
// Hold the button to turn the LED on. Release to turn it off.
//
// Wiring:
//   Pin 2 --> one side of button --> other side of button --> GND
//   Pin 9 --> 220Ω resistor --> LED long leg (+) --> LED short leg (-) --> GND
//
// Note: With INPUT_PULLUP, the button reads LOW when pressed, HIGH when not pressed.

int ledPin    = 9;
int buttonPin = 2;

void setup() {
  pinMode(ledPin,    OUTPUT);
  pinMode(buttonPin, INPUT_PULLUP);  // built-in pull-up, so HIGH = not pressed, LOW = pressed
}

void loop() {
  if (digitalRead(buttonPin) == LOW) {
    // Button is pressed (LOW because of INPUT_PULLUP)
    digitalWrite(ledPin, HIGH);
  } else {
    // Button is not pressed
    digitalWrite(ledPin, LOW);
  }
}

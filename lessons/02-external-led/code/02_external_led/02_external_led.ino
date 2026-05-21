// Lesson 02: External LED
// Blinks an LED on the breadboard using pin 9.
//
// Wiring:
//   Pin 9 --> 220 ohm resistor --> LED long leg (+)
//   LED short leg (-) --> GND

void setup() {
  pinMode(9, OUTPUT);  // Pin 9 is an output (we send electricity out)
}

void loop() {
  digitalWrite(9, HIGH);  // Turn LED on
  delay(500);             // Wait half a second
  digitalWrite(9, LOW);   // Turn LED off
  delay(500);             // Wait half a second
}

// Lesson 07: RGB LED
// Cycles through colours by mixing Red, Green, and Blue.
//
// Wiring:
//   Pin 11 --> 220Ω --> RGB LED Red leg
//   Pin 10 --> 220Ω --> RGB LED Green leg
//   Pin  9 --> 220Ω --> RGB LED Blue leg
//   RGB LED longest leg (GND) --> Arduino GND

int redPin   = 11;
int greenPin = 10;
int bluePin  =  9;

void setup() {
  pinMode(redPin,   OUTPUT);
  pinMode(greenPin, OUTPUT);
  pinMode(bluePin,  OUTPUT);
}

// Set the LED to any colour using values 0-255 for each channel
void setColour(int r, int g, int b) {
  analogWrite(redPin,   r);
  analogWrite(greenPin, g);
  analogWrite(bluePin,  b);
}

void loop() {
  setColour(255, 0,   0);    delay(1000);  // Red
  setColour(0,   255, 0);    delay(1000);  // Green
  setColour(0,   0,   255);  delay(1000);  // Blue
  setColour(255, 200, 0);    delay(1000);  // Orange
  setColour(255, 0,   255);  delay(1000);  // Magenta
  setColour(0,   255, 255);  delay(1000);  // Cyan
  setColour(255, 255, 255);  delay(1000);  // White
  setColour(0,   0,   0);    delay(500);   // Off
}

// Lesson 03: Traffic Light
// Three LEDs cycle through an Irish/UK traffic light sequence.
//
// Wiring:
//   Pin 11 --> 220Ω --> Red LED (+) --> Red LED (-) --> GND
//   Pin 10 --> 220Ω --> Yellow LED (+) --> Yellow LED (-) --> GND
//   Pin  9 --> 220Ω --> Green LED (+) --> Green LED (-) --> GND

int redPin    = 11;
int yellowPin = 10;
int greenPin  =  9;

void setup() {
  pinMode(redPin,    OUTPUT);
  pinMode(yellowPin, OUTPUT);
  pinMode(greenPin,  OUTPUT);
}

void loop() {
  // RED: Stop
  digitalWrite(redPin, HIGH);
  delay(3000);

  // RED + YELLOW: Get ready to go
  digitalWrite(yellowPin, HIGH);
  delay(1000);

  // GREEN: Go
  digitalWrite(redPin,    LOW);
  digitalWrite(yellowPin, LOW);
  digitalWrite(greenPin,  HIGH);
  delay(3000);

  // YELLOW: Slow down, stop coming
  digitalWrite(greenPin,  LOW);
  digitalWrite(yellowPin, HIGH);
  delay(1000);

  // Turn yellow off, back to top of loop (red comes on again)
  digitalWrite(yellowPin, LOW);
}

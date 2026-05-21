// Lesson 09: Servo Motor
// Sweeps a servo arm back and forth from 0 to 180 degrees.
//
// Wiring:
//   Servo brown/black wire --> Arduino GND
//   Servo red wire         --> Arduino 5V
//   Servo orange/yellow wire --> Arduino Pin 9

#include <Servo.h>  // import the Servo library

Servo myServo;  // create a Servo object

int servoPin = 9;

void setup() {
  myServo.attach(servoPin);  // connect the servo object to pin 9
}

void loop() {
  // Sweep from 0 to 180 degrees, one degree at a time
  for (int angle = 0; angle <= 180; angle++) {
    myServo.write(angle);  // move servo to this angle
    delay(15);             // wait 15ms for servo to reach the position
  }

  // Sweep back from 180 to 0 degrees
  for (int angle = 180; angle >= 0; angle--) {
    myServo.write(angle);
    delay(15);
  }

  delay(500);  // brief pause at the start position before sweeping again
}

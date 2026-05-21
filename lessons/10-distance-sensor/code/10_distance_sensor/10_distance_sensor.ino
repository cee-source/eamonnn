// Lesson 10: Parking Sensor
// Uses an HC-SR04 ultrasonic sensor to measure distance.
// Buzzer beeps faster when an object is closer, like a car parking sensor.
// Open the Serial Monitor at 9600 baud to see the distance in centimetres.
//
// Wiring:
//   Arduino 5V   --> HC-SR04 VCC
//   Arduino GND  --> HC-SR04 GND
//   Arduino Pin 9  --> HC-SR04 TRIG
//   Arduino Pin 10 --> HC-SR04 ECHO
//   Arduino Pin 8  --> Buzzer long leg (+)
//   Arduino GND    --> Buzzer short leg (-)

int trigPin   =  9;
int echoPin   = 10;
int buzzerPin =  8;

void setup() {
  pinMode(trigPin,   OUTPUT);
  pinMode(echoPin,   INPUT);
  pinMode(buzzerPin, OUTPUT);
  Serial.begin(9600);
}

// Sends a pulse and returns the measured distance in centimetres
long getDistance() {
  // Trigger: send a 10-microsecond HIGH pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Measure how long the echo pin stays HIGH (round-trip time in microseconds)
  long duration = pulseIn(echoPin, HIGH);

  // Convert: sound travels 0.0343 cm per microsecond, divide by 2 for one way
  long distance = duration / 58;

  return distance;
}

void loop() {
  long distance = getDistance();

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.println(" cm");

  // Beep faster as object gets closer
  if (distance < 5) {
    // Very close: nearly solid tone
    tone(buzzerPin, 1000);
    delay(80);
    noTone(buzzerPin);
    delay(30);
  } else if (distance < 15) {
    // Close: fast beep
    tone(buzzerPin, 800);
    delay(100);
    noTone(buzzerPin);
    delay(150);
  } else if (distance < 30) {
    // Medium: slow beep
    tone(buzzerPin, 600);
    delay(100);
    noTone(buzzerPin);
    delay(400);
  } else {
    // Far: silence
    noTone(buzzerPin);
    delay(200);
  }
}

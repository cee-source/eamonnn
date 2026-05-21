// Lesson 08: Night Light
// LED gets brighter as the room gets darker, using a photoresistor (LDR).
// Open the Serial Monitor at 9600 baud to see sensor values.
//
// Wiring:
//   5V --> LDR leg 1
//   LDR leg 2 --> A0  AND  10kΩ resistor top
//   10kΩ resistor bottom --> GND
//   Pin 9 --> 220Ω --> LED (+) --> LED (-) --> GND

int ldrPin = A0;  // photoresistor signal pin
int ledPin = 9;   // LED on a PWM pin

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
}

void loop() {
  int lightValue = analogRead(ldrPin);  // 0 (dark) to 1023 (very bright)

  // Reverse the range: dark (low light) = bright LED, bright room = dim LED
  int brightness = map(lightValue, 0, 1023, 255, 0);

  analogWrite(ledPin, brightness);

  Serial.print("Light sensor: ");
  Serial.print(lightValue);
  Serial.print("   LED brightness: ");
  Serial.println(brightness);

  delay(100);
}

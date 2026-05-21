// Lesson 05: Dimmer Switch
// Turn the potentiometer knob to control LED brightness.
// Open the Serial Monitor at 9600 baud to see the values.
//
// Wiring:
//   Pot left leg  --> GND
//   Pot middle leg --> A0
//   Pot right leg --> 5V
//   Pin 9 --> 220Ω --> LED (+) --> LED (-) --> GND

int potPin = A0;  // potentiometer signal pin
int ledPin = 9;   // LED pin (must be a PWM pin: 3,5,6,9,10,11)

void setup() {
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);  // start serial communication with computer
}

void loop() {
  int potValue   = analogRead(potPin);        // read knob: 0 to 1023
  int brightness = map(potValue, 0, 1023, 0, 255);  // convert to 0-255 range

  analogWrite(ledPin, brightness);            // set LED brightness

  Serial.print("Knob: ");
  Serial.print(potValue);
  Serial.print("   Brightness: ");
  Serial.println(brightness);

  delay(50);  // small delay so Serial Monitor isn't overwhelmed
}

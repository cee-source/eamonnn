// Lesson 01: Blink
// Makes the built-in LED on pin 13 flash on and off.
// No extra parts needed!

void setup() {
  // Set pin 13 as an output so we can send electricity to the LED
  pinMode(13, OUTPUT);
}

void loop() {
  digitalWrite(13, HIGH);  // Turn the LED on (5V)
  delay(1000);             // Wait 1 second (1000 milliseconds)
  digitalWrite(13, LOW);   // Turn the LED off (0V)
  delay(1000);             // Wait 1 second
}

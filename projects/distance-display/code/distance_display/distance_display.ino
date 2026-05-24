// Distance Display
// Reads distance from an HC-SR04 and shows it on an LCD1602 screen.
//
// ── HC-SR04 ──────────────────────────────
//   VCC  → 5V
//   GND  → GND
//   TRIG → D9
//   ECHO → D8
//
// ── LCD1602 (16-pin, no I2C) ─────────────
//   Pin 1  (GND)       → GND
//   Pin 2  (5V)        → 5V
//   Pin 3  (Contrast)  → potentiometer middle leg
//   Pin 4  (RS)        → D12
//   Pin 5  (RW)        → GND
//   Pin 6  (E)         → D11
//   Pins 7-10          → not connected
//   Pin 11 (D4)        → D7
//   Pin 12 (D5)        → D6
//   Pin 13 (D6)        → D5
//   Pin 14 (D7)        → D4
//   Pin 15 (Backlight+)→ 220Ω resistor → 5V
//   Pin 16 (Backlight-)→ GND
//
//   Potentiometer: left→GND, middle→LCD pin 3, right→5V

#include <LiquidCrystal.h>

// LiquidCrystal(RS, E, D4, D5, D6, D7)
LiquidCrystal lcd(12, 11, 7, 6, 5, 4);

int trigPin = 9;
int echoPin = 8;

void setup() {
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);

  lcd.begin(16, 2);          // 16 columns, 2 rows
  lcd.setCursor(0, 0);
  lcd.print("Distance:");    // fixed label on top row, never changes
}

long getDistance() {
  // Send a 10-microsecond trigger pulse
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Measure how long the echo takes to return
  long duration = pulseIn(echoPin, HIGH);

  // Convert microseconds to centimetres (speed of sound ÷ 2 round-trip)
  long distance = duration / 58;

  return distance;
}

void loop() {
  long distance = getDistance();

  lcd.setCursor(0, 1);       // jump to start of second row
  lcd.print(distance);
  lcd.print(" cm      ");    // trailing spaces wipe leftover digits (e.g. "100" → "5")

  delay(200);                // update 5 times per second
}

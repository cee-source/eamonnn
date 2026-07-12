// IR Remote Code Reader
// Press buttons on your remote and see the hex codes in Serial Monitor.
//
// Wiring (VS1838B, dome facing you):
//   Left leg  (OUT) → Arduino pin 9
//   Middle leg (GND) → Arduino GND
//   Right leg  (VCC) → Arduino 5V
//
// Open Serial Monitor at 9600 baud, press each button, write down the code.

#include <IRremote.hpp>

int receiverPin = 9;

void setup() {
  Serial.begin(9600);
  IrReceiver.begin(receiverPin, ENABLE_LED_FEEDBACK);
  Serial.println("Ready! Press a button...");
}

void loop() {
  if (IrReceiver.decode()) {
    if (IrReceiver.decodedIRData.protocol != UNKNOWN) {
      Serial.print("Protocol : ");
      Serial.println(IrReceiver.getProtocolString());
      Serial.print("Code     : 0x");
      Serial.println(IrReceiver.decodedIRData.command, HEX);
      Serial.println("----");
    }
    IrReceiver.resume();
  }
}

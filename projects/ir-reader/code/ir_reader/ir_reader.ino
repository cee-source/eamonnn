// IR Remote Code Reader
// Press buttons on any remote and see the hex codes in Serial Monitor.
// Wire your IR receiver: left leg=GND, middle=5V, right=pin 11
// (pin order varies by receiver model -- check the label)
//
// Open Serial Monitor at 9600 baud, then press each button you want to use.
// Write down the code next to the button name -- you'll need them to update your turret.

#include <IRremote.h>

int receiverPin = 11;

IRrecv irrecv(receiverPin);
decode_results results;

void setup() {
  Serial.begin(9600);
  irrecv.enableIRIn();
  Serial.println("Ready! Press a button on your remote...");
}

void loop() {
  if (irrecv.decode(&results)) {
    if (results.value != 0xFFFFFFFF) {  // ignore repeat codes
      Serial.print("Code: 0x");
      Serial.println(results.value, HEX);
    }
    irrecv.resume();
  }
}

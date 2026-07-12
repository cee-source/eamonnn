// IR Remote Code Reader
// Press buttons on any remote and see the hex codes in Serial Monitor.
// Wire your IR receiver: OUT=pin 9, GND=GND, VCC=5V
// (VS1838B facing you, dome side: left=OUT, middle=GND, right=VCC)
//
// Open Serial Monitor at 9600 baud, then press each button you want to use.
// Write down the code next to the button name -- you'll need them to update your turret.

#include <IRremote.h>

int receiverPin = 9;

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

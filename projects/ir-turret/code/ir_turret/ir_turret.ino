//////////////////////////////////////////////////
              //  LICENSE  //
//////////////////////////////////////////////////
#pragma region LICENSE
/*
  ************************************************************************************
  * MIT License
  *
  * Copyright (c) 2025 Crunchlabs LLC (IRTurret Control Code)
  * Copyright (c) 2020-2022 Armin Joachimsmeyer (IRremote Library)

  * Permission is hereby granted, free of charge, to any person obtaining a copy
  * of this software and associated documentation files (the "Software"), to deal
  * in the Software without restriction, including without limitation the rights
  * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  * copies of the Software, and to permit persons to whom the Software is furnished
  * to do so, subject to the following conditions:
  *
  * The above copyright notice and this permission notice shall be included in all
  * copies or substantial portions of the Software.
  *
  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
  * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
  * OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
  *
  ************************************************************************************
*/
#pragma endregion LICENSE

//////////////////////////////////////////////////
              //  LIBRARIES  //
//////////////////////////////////////////////////
#pragma region LIBRARIES

#include <Arduino.h>
#include <Servo.h>
#define DECODE_NEC
#include <IRremote.hpp>

#pragma endregion LIBRARIES

//////////////////////////////////////////////////
               //  IR CODES  //
//////////////////////////////////////////////////
#pragma region IR CODES
/*
** Remote: Car MP3 remote
** Run the ir_reader sketch to find codes for your specific remote,
** then update the values below.
*/

#define left     0x44  // car MP3: left arrow
#define right    0x43  // car MP3: right arrow
#define up       0x46  // car MP3: up arrow
#define down     0x15  // car MP3: down arrow
#define ok       0x40  // car MP3: OK
#define star     0x09  // car MP3: *
#define hashtag  0x07  // car MP3: #
#define cmd1     0x0C  // car MP3: 1 (shake yes)
#define cmd2     0x18  // car MP3: 2 (shake no)
#define cmd3     0x47  // not mapped
#define cmd4     0x08  // not mapped
#define cmd5     0x1C  // not mapped
#define cmd6     0x5A  // not mapped
#define cmd7     0x16  // not mapped
#define cmd8     0x0D  // not mapped
#define cmd9     0x52  // not mapped
#define cmd0     0x19  // not mapped

#pragma endregion IR CODES

//////////////////////////////////////////////////
          //  PINS AND PARAMETERS  //
//////////////////////////////////////////////////
#pragma region PINS AND PARAMS
Servo yawServo;
Servo pitchServo;
Servo rollServo;

int yawServoVal = 90;
int pitchServoVal = 100;
int rollServoVal = 90;

int pitchMoveSpeed = 8;
int yawMoveSpeed = 90;
int yawStopSpeed = 90;
int rollMoveSpeed = 90;
int rollStopSpeed = 90;

int yawPrecision = 150;
int rollPrecision = 158;

int pitchMax = 150;
int pitchMin = 33;

void shakeHeadYes(int moves = 3);
void shakeHeadNo(int moves = 3);
#pragma endregion PINS AND PARAMS

//////////////////////////////////////////////////
              //  S E T U P  //
//////////////////////////////////////////////////
#pragma region SETUP
void setup() {
    Serial.begin(9600);

    yawServo.attach(10);
    pitchServo.attach(11);
    rollServo.attach(12);

    Serial.println(F("START " __FILE__ " from " __DATE__ "\r\nUsing library version " VERSION_IRREMOTE));

    IrReceiver.begin(9, ENABLE_LED_FEEDBACK);

    Serial.print(F("Ready to receive IR signals of protocols: "));
    printActiveIRProtocols(&Serial);
    Serial.println(F("at pin 9"));

    homeServos();
}
#pragma endregion SETUP

//////////////////////////////////////////////////
               //  L O O P  //
//////////////////////////////////////////////////
#pragma region LOOP

void loop() {
    if (IrReceiver.decode()) {
        IrReceiver.printIRResultShort(&Serial);
        IrReceiver.printIRSendUsage(&Serial);
        if (IrReceiver.decodedIRData.protocol == UNKNOWN) {
            Serial.println(F("Received noise or an unknown (or not yet enabled) protocol - if you wish to add this command, define it at the top of the file with the hex code printed below (ex: 0x8)"));
            IrReceiver.printIRResultRawFormatted(&Serial, true);
        }
        Serial.println();

        IrReceiver.resume();

        switch(IrReceiver.decodedIRData.command){
            case up:
              upMove(1);
              break;
            case down:
              downMove(1);
              break;
            case left:
              leftMove(1);
              break;
            case right:
              rightMove(1);
              break;
            case ok:
              fire();
              break;
            case star:
              fireAll();
              delay(50);
              break;
            case cmd1:
              shakeHeadYes(3);
              break;
            case cmd2:
              shakeHeadNo(3);
              break;
        }
    }
    delay(5);
}

#pragma endregion LOOP

//////////////////////////////////////////////////
               // FUNCTIONS  //
//////////////////////////////////////////////////
#pragma region FUNCTIONS

void leftMove(int moves){
    for (int i = 0; i < moves; i++){
        yawServo.write(yawStopSpeed + yawMoveSpeed);
        delay(yawPrecision);
        yawServo.write(yawStopSpeed);
        delay(5);
        Serial.println("LEFT");
    }
}

void rightMove(int moves){
    for (int i = 0; i < moves; i++){
        yawServo.write(yawStopSpeed - yawMoveSpeed);
        delay(yawPrecision);
        yawServo.write(yawStopSpeed);
        delay(5);
        Serial.println("RIGHT");
    }
}

void upMove(int moves){
    for (int i = 0; i < moves; i++){
        if((pitchServoVal+pitchMoveSpeed) < pitchMax){
            pitchServoVal = pitchServoVal + pitchMoveSpeed;
            pitchServo.write(pitchServoVal);
            delay(50);
            Serial.println("UP");
        }
    }
}

void downMove(int moves){
    for (int i = 0; i < moves; i++){
        if((pitchServoVal-pitchMoveSpeed) > pitchMin){
            pitchServoVal = pitchServoVal - pitchMoveSpeed;
            pitchServo.write(pitchServoVal);
            delay(50);
            Serial.println("DOWN");
        }
    }
}

void fire(){
    rollServo.write(rollStopSpeed + rollMoveSpeed);
    delay(rollPrecision);
    rollServo.write(rollStopSpeed);
    delay(5);
    Serial.println("FIRING");
}

void fireAll(){
    rollServo.write(rollStopSpeed + rollMoveSpeed);
    delay(rollPrecision * 6);
    rollServo.write(rollStopSpeed);
    delay(5);
    Serial.println("FIRING ALL");
}

void homeServos(){
    yawServo.write(yawStopSpeed);
    delay(20);
    rollServo.write(rollStopSpeed);
    delay(100);
    pitchServo.write(100);
    delay(100);
    pitchServoVal = 100;
    Serial.println("HOMING");
}

void shakeHeadYes(int moves) {
    Serial.println("YES");
    if ((pitchMax - pitchServoVal) < 15){
        pitchServoVal = pitchServoVal - 15;
    } else if ((pitchServoVal - pitchMin) < 15){
        pitchServoVal = pitchServoVal + 15;
    }
    pitchServo.write(pitchServoVal);
    int startAngle = pitchServoVal;
    int nodAngle = startAngle + 15;
    for (int i = 0; i < moves; i++){
        for (int angle = startAngle; angle <= nodAngle; angle++){
            pitchServo.write(angle);
            delay(7);
        }
        delay(50);
        for (int angle = nodAngle; angle >= startAngle; angle--){
            pitchServo.write(angle);
            delay(7);
        }
        delay(50);
    }
}

void shakeHeadNo(int moves) {
    Serial.println("NO");
    for (int i = 0; i < moves; i++){
        yawServo.write(140);
        delay(190);
        yawServo.write(yawStopSpeed);
        delay(50);
        yawServo.write(40);
        delay(190);
        yawServo.write(yawStopSpeed);
        delay(50);
    }
}

#pragma endregion FUNCTIONS

//////////////////////////////////////////////////
               //  END CODE  //
//////////////////////////////////////////////////

#include "config.h"

#define M1_DIR 4
#define M1_PWM 5
#define M2_DIR 7
#define M2_PWM 6
#define M3_DIR 8
#define M3_PWM 9

#define LIFT_DIR 2
#define LIFT_PWM 3

// drive vector {v_x, v_y, omega}
int vSpeed[3] = {0, 0, 0};
// -1 lower, 0 stay, 1 raise
int moveFork = 0;

double angleWheel1 = 90.0;
double angleWheel2 = 210.0;
double angleWheel3 = 330.0;
double localAngle  = 60.0;
double botRadius   = 100.0;
double wheelRadius = 35.0;
double wheelSpeeds[3];
double tune = 1;

void setup() {
  Serial.begin(115200);
  pinMode(M1_DIR, OUTPUT);
  pinMode(M1_PWM, OUTPUT);
  pinMode(M2_DIR, OUTPUT);
  pinMode(M2_PWM, OUTPUT);
  pinMode(M3_DIR, OUTPUT);
  pinMode(M3_PWM, OUTPUT);
  pinMode(LIFT_DIR, OUTPUT);
  pinMode(LIFT_PWM, OUTPUT);
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    parseCommand(cmd);
    Serial.println("OK");
  }
  moveBot();
}

// Commands from Pi:
//   F  = forward        B  = backward
//   L  = rotate left    R  = rotate right
//   SL = strafe left    SR = strafe right
//   FL = fwd+left       FR = fwd+right
//   BL = back+left      BR = back+right
//   U  = fork up        D  = fork down
//   S  = stop
void parseCommand(String cmd) {
  moveFork = 0;
  if      (cmd == "F")  { vSpeed[0]=0;  vSpeed[1]=-1; vSpeed[2]=0;  }
  else if (cmd == "B")  { vSpeed[0]=0;  vSpeed[1]=1;  vSpeed[2]=0;  }
  else if (cmd == "L")  { vSpeed[0]=0;  vSpeed[1]=0;  vSpeed[2]=-1; }
  else if (cmd == "R")  { vSpeed[0]=0;  vSpeed[1]=0;  vSpeed[2]=1;  }
  else if (cmd == "SL") { vSpeed[0]=-1; vSpeed[1]=0;  vSpeed[2]=0;  }
  else if (cmd == "SR") { vSpeed[0]=1;  vSpeed[1]=0;  vSpeed[2]=0;  }
  else if (cmd == "FL") { vSpeed[0]=1;  vSpeed[1]=-1; vSpeed[2]=0;  }
  else if (cmd == "FR") { vSpeed[0]=-1; vSpeed[1]=-1; vSpeed[2]=0;  }
  else if (cmd == "BL") { vSpeed[0]=1;  vSpeed[1]=1;  vSpeed[2]=0;  }
  else if (cmd == "BR") { vSpeed[0]=-1; vSpeed[1]=1;  vSpeed[2]=0;  }
  else if (cmd == "U")  { vSpeed[0]=0;  vSpeed[1]=0;  vSpeed[2]=0;  moveFork=1;  }
  else if (cmd == "D")  { vSpeed[0]=0;  vSpeed[1]=0;  vSpeed[2]=0;  moveFork=-1; }
  else                  { vSpeed[0]=0;  vSpeed[1]=0;  vSpeed[2]=0;  } // S or unknown = stop
}

void moveBot() {
  float speeds[3];
  getWheelSpeeds(speeds);
  driveWheels(speeds, maxSpeed);
  driveLift();
}

void driveWheels(float* speeds, float maxSpd) {
  float top = max(max(abs(speeds[0]), abs(speeds[1])), abs(speeds[2]));
  float ws[3];

  for (int i = 0; i < 3; i++) {
    if (top == 0) { ws[i] = 0; continue; }
    float norm = speeds[i] / top;
    ws[i] = (norm < 0 ? -pow(abs(norm), tune) : pow(norm, tune)) * maxSpd;
  }

  if (flipM1) ws[0] = -ws[0];
  if (flipM2) ws[1] = -ws[1];
  if (flipM3) ws[2] = -ws[2];

  digitalWrite(M1_DIR, ws[0] < 0 ? LOW : HIGH);
  analogWrite(M1_PWM, int(abs(ws[0])));

  digitalWrite(M2_DIR, ws[1] < 0 ? LOW : HIGH);
  analogWrite(M2_PWM, int(abs(ws[1])));

  digitalWrite(M3_DIR, ws[2] < 0 ? LOW : HIGH);
  analogWrite(M3_PWM, int(abs(ws[2])));
}

void driveLift() {
  int dir = flipM4 ? -moveFork : moveFork;
  if (dir > 0) {
    digitalWrite(LIFT_DIR, HIGH);
    analogWrite(LIFT_PWM, 255);
  } else if (dir < 0) {
    digitalWrite(LIFT_DIR, LOW);
    analogWrite(LIFT_PWM, 255);
  } else {
    analogWrite(LIFT_PWM, 0);
  }
}

void getWheelSpeeds(float* wheelList) {
  double a = localAngle;
  double r = 0.0174533;
  wheelList[0] = (-sin((a+angleWheel1)*r)*cos(a*r)*vSpeed[0] + cos((a+angleWheel1)*r)*cos(a*r)*vSpeed[1] + botRadius*vSpeed[2]) / wheelRadius;
  wheelList[1] = (-sin((a+angleWheel2)*r)*cos(a*r)*vSpeed[0] + cos((a+angleWheel2)*r)*cos(a*r)*vSpeed[1] + botRadius*vSpeed[2]) / wheelRadius;
  wheelList[2] = (-sin((a+angleWheel3)*r)*cos(a*r)*vSpeed[0] + cos((a+angleWheel3)*r)*cos(a*r)*vSpeed[1] + botRadius*vSpeed[2]) / wheelRadius;
}

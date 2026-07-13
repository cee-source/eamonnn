// Spectrum Goggles firmware
// Potentiometer on A0 selects one of 7 EM bands; OLED shows the band name
// and, where a real sensor is wired up, its live reading. See ../README.md
// for wiring and which bands have genuine hardware behind them.

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <BH1750.h>
#include <Adafruit_MLX90614.h>

#define OLED_WIDTH 128
#define OLED_HEIGHT 64
#define OLED_ADDR 0x3C

#define POT_PIN A0
#define UV_PIN A1
#define RADIO_PIN A2
#define MICROWAVE_PIN 2
#define GEIGER_PIN 3

const int NUM_BANDS = 7;

enum SensorType { SENSOR_NONE, SENSOR_RADIO, SENSOR_MICROWAVE, SENSOR_IR, SENSOR_VISIBLE, SENSOR_UV, SENSOR_GEIGER };

struct Band {
  const char *name;
  const char *range;
  SensorType sensor;
};

Band bands[NUM_BANDS] = {
  { "Radio Waves",   "> 1 m",        SENSOR_RADIO },
  { "Microwaves",    "1mm - 1m",     SENSOR_MICROWAVE },
  { "Infrared",      "700nm - 1mm",  SENSOR_IR },
  { "Visible Light", "400 - 700nm",  SENSOR_VISIBLE },
  { "Ultraviolet",   "10 - 400nm",   SENSOR_UV },
  { "X-Rays",        "0.01 - 10nm",  SENSOR_NONE },
  { "Gamma Rays",    "< 0.01nm",     SENSOR_GEIGER },
};

Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
BH1750 lightMeter;
Adafruit_MLX90614 mlx = Adafruit_MLX90614();

volatile unsigned long geigerPulseCount = 0;
unsigned long geigerWindowStart = 0;
unsigned int geigerCPM = 0;

bool hasBH1750 = false;
bool hasMLX90614 = false;

void geigerPulse() {
  geigerPulseCount++;
}

void setup() {
  Serial.begin(9600);
  Wire.begin();

  pinMode(MICROWAVE_PIN, INPUT);
  pinMode(GEIGER_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(GEIGER_PIN), geigerPulse, FALLING);
  geigerWindowStart = millis();

  display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  hasBH1750 = lightMeter.begin();
  hasMLX90614 = mlx.begin();
}

int readBandIndex() {
  int raw = analogRead(POT_PIN);
  long idx = map(raw, 0, 1023, 0, NUM_BANDS - 1);
  return constrain(idx, 0, NUM_BANDS - 1);
}

void updateGeigerCPM() {
  if (millis() - geigerWindowStart >= 60000UL) {
    noInterrupts();
    geigerCPM = geigerPulseCount;
    geigerPulseCount = 0;
    interrupts();
    geigerWindowStart = millis();
  }
}

void drawReading(const Band &band) {
  display.setCursor(0, 0);
  display.setTextSize(1);
  display.println(band.name);
  display.println(band.range);
  display.drawLine(0, 18, OLED_WIDTH, 18, SSD1306_WHITE);

  display.setCursor(0, 26);
  display.setTextSize(2);

  switch (band.sensor) {
    case SENSOR_RADIO: {
      int raw = analogRead(RADIO_PIN);
      int pct = map(raw, 0, 1023, 0, 100);
      display.print(pct);
      display.println("%");
      display.setTextSize(1);
      display.println("field strength (sim)");
      break;
    }
    case SENSOR_MICROWAVE: {
      bool detected = digitalRead(MICROWAVE_PIN) == HIGH;
      display.println(detected ? "DETECT" : "clear");
      display.setTextSize(1);
      display.println("RCWL-0516 doppler");
      break;
    }
    case SENSOR_IR: {
      if (hasMLX90614) {
        double tempC = mlx.readObjectTempC();
        display.print(tempC, 1);
        display.println(" C");
      } else {
        display.println("NO SENSOR");
      }
      display.setTextSize(1);
      display.println("MLX90614 IR temp");
      break;
    }
    case SENSOR_VISIBLE: {
      if (hasBH1750) {
        float lux = lightMeter.readLightLevel();
        display.print(lux, 0);
        display.println(" lx");
      } else {
        display.println("NO SENSOR");
      }
      display.setTextSize(1);
      display.println("BH1750 ambient light");
      break;
    }
    case SENSOR_UV: {
      int raw = analogRead(UV_PIN);
      float voltage = raw * (5.0 / 1023.0);
      float uvIndex = voltage / 0.1; // approx per GUVA-S12SD datasheet
      display.print(uvIndex, 1);
      display.println(" UVI");
      display.setTextSize(1);
      display.println("GUVA-S12SD UV index");
      break;
    }
    case SENSOR_GEIGER: {
      updateGeigerCPM();
      display.print(geigerCPM);
      display.println(" CPM");
      display.setTextSize(1);
      display.println("Geiger background rad.");
      break;
    }
    default: {
      display.println("NO SENSOR");
      display.setTextSize(1);
      display.println("needs scintillator + PMT");
      break;
    }
  }
}

void loop() {
  int idx = readBandIndex();
  const Band &band = bands[idx];

  display.clearDisplay();
  drawReading(band);
  display.display();

  delay(200);
}

#include <ld2410.h>

ld2410 radar;
unsigned long lastPrint = 0;

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial1.begin(256000, SERIAL_8N1, 14, 21);
  delay(500);
  Serial.println(radar.begin(Serial1) ? "LD2410C connected" : "LD2410C not responding");
}

void loop() {
  radar.read();

  if (millis() - lastPrint >= 1000) {
    lastPrint = millis();
    uint16_t distance = 0;
    if (radar.stationaryTargetDetected()) {
      distance = radar.stationaryTargetDistance();
    } else if (radar.movingTargetDetected()) {
      distance = radar.movingTargetDistance();
    }
    Serial.print(distance);
    Serial.println(" cm");
  }
}

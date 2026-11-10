#include <ld2410.h>
#include "FS.h"
#include "SD_MMC.h"

ld2410 radar;
const int DURATION_S = 120;
int dist[DURATION_S];
int count = 0;
unsigned long last = 0;
bool done = false;

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial1.begin(256000, SERIAL_8N1, 14, 21);
  radar.begin(Serial1);
  SD_MMC.setPins(39, 38, 40);
  if (!SD_MMC.begin("/sdcard", true)) Serial.println("WARNING: no SD card, data will only print");
  Serial.println("Recording for 2 minutes...");
  last = millis();
}

void loop() {
  radar.read();
  if (done) return;

  if (millis() - last >= 1000) {
    last += 1000;
    int d = 0;
    if (radar.stationaryTargetDetected()) d = radar.stationaryTargetDistance();
    else if (radar.movingTargetDetected()) d = radar.movingTargetDistance();
    if (d < 60) d = 0;                       // ignore the radar's own ~30 cm reflection
    dist[count] = d;
    count++;
    Serial.printf("%3d s  %3d cm\n", count, d);
  }

  if (count >= DURATION_S) {
    done = true;
    char name[20];
    int run = 1;
    do { snprintf(name, sizeof(name), "/run%d.csv", run++); } while (SD_MMC.exists(name));
    File f = SD_MMC.open(name, FILE_WRITE);
    if (f) {
      f.println("time_s,distance_cm");
      for (int i = 0; i < count; i++) f.printf("%d,%d\n", i + 1, dist[i]);
      f.close();
      Serial.printf("DONE. Saved %d readings to %s\n", count, name);
    } else {
      Serial.println("DONE, but could not write to SD card");
    }
  }
}
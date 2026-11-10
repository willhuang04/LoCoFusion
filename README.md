# LoCoFusion

Low-cost presence detection that fuses a camera with a 24 GHz mmWave radar. An ESP32-S3 streams camera frames over Wi-Fi and radar distance over USB serial. A laptop runs YOLOv8n on the frames and compares three approaches: camera only, radar only, and a simple rule-based fusion.

## Hardware

- Freenove ESP32-S3 WROOM CAM (16 MB flash, OPI PSRAM, OV3660 camera)
- HLK-LD2410C mmWave radar

### Wiring (LD2410C → ESP32-S3)

| LD2410C | ESP32-S3 |
| --- | --- |
| TX | GPIO14 (Serial1 RX) |
| RX | GPIO21 (Serial1 TX) |
| VCC | 5V |
| GND | GND |

The radar runs at 256000 baud.

## Repository layout

- `radar_test/`: radar-only smoke test that prints the distance once a second.
- `camera_radar/`: the main firmware. It is the Espressif CameraWebServer example plus LD2410C reading. It serves `/capture`, `:81/stream` and `/control`, and prints `R,<distance_cm>` on USB serial every 200 ms.
- `midterm/run_trials.py`: the trial runner. It logs camera confidence, radar distance and the three predictions for each frame.
- `midterm/results_20261109_231352/`: per-trial CSVs and `summary.md` from the midterm run.

## Build and flash

You need [arduino-cli](https://arduino.github.io/arduino-cli/), the Espressif `esp32` core and the `ld2410` library (by Nick Reynolds).

```bash
cp camera_radar/secrets.example.h camera_radar/secrets.h   # then enter your Wi-Fi SSID and password
FQBN="esp32:esp32:esp32s3:PSRAM=opi,FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,CDCOnBoot=cdc"
arduino-cli compile --fqbn "$FQBN" camera_radar
arduino-cli upload  --fqbn "$FQBN" -p /dev/cu.usbmodem101 camera_radar
```

`secrets.h` is gitignored. The board prints its IP address on serial at 115200 baud.

## Running the trials

```bash
python3 -m venv .venv
.venv/bin/pip install ultralytics opencv-python pyserial
cd midterm
../.venv/bin/python -u run_trials.py --ip <board-ip> --port /dev/cu.usbmodem101
```

The script downloads `yolov8n.pt` on first use. It walks through trials T0 to T7, giving spoken cues and showing an on-screen panel; press SPACE to start. Results go into a new `results_<timestamp>/` folder.

Fusion rule: person = camera conf > 0.6, OR (radar distance between 60 and 300 cm AND camera conf > 0.3).

## Midterm results (preliminary)

These numbers come from one run in a single room: 9,108 scored frames, of which 3,680 contain a person.

| Approach | Accuracy | Recall | False-positive rate |
| --- | --- | --- | --- |
| Camera only | 90% | 90% | 9% |
| Radar only | 65% | 84% | 48% |
| Rule fusion | 90% | 91% | 10% |

Caveats:

- Fusion added only 27 person frames that the camera alone missed.
- The "lights off" room was dim, not dark.
- Many of the radar false positives come from the setup: the waiting spot was within radar range. In the empty-room trial (T1) the false-positive rate was only 2%.

See `midterm/results_20261109_231352/summary.md` for the breakdown by trial.

# LoCoFusion midterm results

Run 2026-11-09 23:13, camera 192.168.1.157, radar /dev/cu.usbmodem101
Rules: radar person = 60-300 cm; camera person = conf > 0.6; fusion = camera > 0.6 OR (radar AND camera > 0.3)

## T0: Radar distance check

| True distance | Radar mean (cm) | Radar std (cm) | Readings |
| --- | --- | --- | --- |
| 100 cm | 195 | 67 | 285 |
| 200 cm | 209 | 3 | 285 |
| 300 cm | 268 | 34 | 286 |

## T1: Empty scene

| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |
| --- | --- | --- | --- | --- |
| Camera only | 100% | n/a | 0% | 0 / 1238 |
| Radar only | 98% | n/a | 2% | 0 / 1238 |
| Rule fusion | 100% | n/a | 0% | 0 / 1238 |

## T2: Walk through

| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |
| --- | --- | --- | --- | --- |
| Camera only | 78% | 72% | 17% | 745 / 960 |
| Radar only | 62% | 79% | 50% | 745 / 960 |
| Rule fusion | 78% | 73% | 18% | 745 / 960 |

## T3: Stand still

| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |
| --- | --- | --- | --- | --- |
| Camera only | 95% | 100% | 16% | 1156 / 482 |
| Radar only | 80% | 92% | 50% | 1156 / 482 |
| Rule fusion | 95% | 100% | 16% | 1156 / 482 |

## T4: Lights off

| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |
| --- | --- | --- | --- | --- |
| Camera only | 95% | 97% | 7% | 361 / 461 |
| Radar only | 51% | 96% | 85% | 361 / 461 |
| Rule fusion | 94% | 98% | 8% | 361 / 461 |

## T5: Partly visible

| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |
| --- | --- | --- | --- | --- |
| Camera only | 87% | 87% | 12% | 884 / 475 |
| Radar only | 66% | 64% | 32% | 884 / 475 |
| Rule fusion | 88% | 88% | 12% | 884 / 475 |

## T6: Moving object, no person

| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |
| --- | --- | --- | --- | --- |
| Camera only | 99% | n/a | 1% | 0 / 597 |
| Radar only | 37% | n/a | 63% | 0 / 597 |
| Rule fusion | 96% | n/a | 4% | 0 / 597 |

## T7: Sync check

| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |
| --- | --- | --- | --- | --- |
| Camera only | 98% | 95% | 0% | 534 / 962 |
| Radar only | 50% | 97% | 77% | 534 / 962 |
| Rule fusion | 99% | 96% | 0% | 534 / 962 |

Detection delay after cue (10 of 10 step-ins detected by both): camera 1314 ms, radar 500 ms, radar minus camera -814 ms (std 952 ms)

## All scored trials combined

| Approach | Accuracy | Recall | False-positive rate |
| --- | --- | --- | --- |
| Camera only | 90% | 90% | 9% |
| Radar only | 65% | 84% | 48% |
| Rule fusion | 90% | 91% | 10% |

Mean camera inference on laptop: 32 ms/frame; mean radar sample age: 100 ms

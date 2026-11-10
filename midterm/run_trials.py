"""
LoCoFusion midterm experiments: runs every trial automatically, speaks each instruction out loud
(macOS `say`), labels ground truth from the schedule, logs camera + radar + fusion, and prints results.

Install once:   pip3 install ultralytics opencv-python pyserial
Run all:        python3 run_trials.py --ip 192.168.1.157 --port /dev/cu.usbmodem101
Run some:       python3 run_trials.py --ip ... --port ... --trials T1,T2
Show video:     add --show

Output folder:  results_<date_time>/  with one CSV per trial, a snapshot per trial, and summary.md
"""
import argparse, csv, os, statistics, subprocess, threading, time
from datetime import datetime
import cv2, serial
from ultralytics import YOLO

RADAR_MIN, RADAR_MAX = 60, 300     # cm: radar counts a person only in this range
CAM_STRONG, CAM_WEAK = 0.6, 0.3    # camera confidence thresholds for the fusion rule
GUARD_S = 1.5                      # seconds after each cue left unlabeled (person still moving into place)

# Each phase: (label, seconds, spoken instruction). label: person / empty / none (not scored) / d100 etc.
def walk(n, stay=5, gap=6):
    p = []
    for i in range(n):
        p += [("person", stay, f"Pass {i+1}. Walk in and stand on the X."), ("empty", gap, "Go to the waiting spot.")]
    return p

TRIALS = {
    "T0": ("Radar distance check", "One person. Tape marks at 1, 2 and 3 meters straight in front of the sensor.",
           [("empty", 10, "Go to the waiting spot."),
            ("d100", 15, "Stand still on the 1 meter mark."),
            ("d200", 15, "Stand still on the 2 meter mark."),
            ("d300", 15, "Stand still on the 3 meter mark."),
            ("empty", 5, "Go to the waiting spot.")]),
    "T1": ("Empty scene", "Nobody in view. Lights on.",
           [("empty", 60, "Everyone stay out of view and still for one minute.")]),
    "T2": ("Walk through", "One person, normal pace, lights on.", walk(10)),
    "T3": ("Stand still", "One person standing as still as possible on the X.",
           [("empty", 5, "Start at the waiting spot.")] +
           sum([[("person", 20, f"Round {i+1}. Walk in and stand completely still on the X."),
                 ("empty", 8, "Go to the waiting spot.")] for i in range(3)], [])),
    "T4": ("Lights off", "Same as walk through, but with the room lights off.",
           [("none", 8, "Turn the lights off now. Friend at the waiting spot.")] + walk(5) +
           [("none", 3, "You can turn the lights back on.")]),
    "T5": ("Partly visible", "Person stands at the edge of the camera view, about half their body out of frame.",
           sum([[("person", 10, f"Round {i+1}. Stand two meters away at the edge of the view, half your body out of frame."),
                 ("empty", 6, "Go to the waiting spot.")] for i in range(5)], [])),
    "T6": ("Moving object, no person", "Something moves in view while the person stays out of view.",
           [("empty", 30, "Stay out of view and swing a bag or jacket on a broom handle near the X for thirty seconds.")]),
    "T7": ("Sync check", "Step quickly onto the X on each Now cue, then leave.",
           sum([[("person", 4, "Now!"), ("empty", 6, "Out.")] for _ in range(10)], [])),
}

ap = argparse.ArgumentParser()
ap.add_argument("--ip", required=True)
ap.add_argument("--port", required=True)
ap.add_argument("--trials", default=",".join(TRIALS))
ap.add_argument("--show", action="store_true", help="(kept for compatibility; the panel always shows video)")
ap.add_argument("--no-panel", action="store_true", help="run without the on-screen instruction panel")
ap.add_argument("--no-wait", action="store_true", help="start immediately instead of waiting for SPACE")
ap.add_argument("--countdown", type=int, default=10, help="seconds before each trial starts")
args = ap.parse_args()

def say(text):
    print(f"  >> {text}")
    try: subprocess.Popen(["say", text])
    except FileNotFoundError: pass

radar_cm, radar_t = 0, 0.0
def read_radar():
    global radar_cm, radar_t
    ser = serial.Serial(args.port, 115200, timeout=1)
    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if line.startswith("R,"):
            try: radar_cm, radar_t = int(line[2:]), time.time()
            except ValueError: pass
threading.Thread(target=read_radar, daemon=True).start()

model = YOLO("yolov8n.pt")

class Stream:  # always hands back the newest frame so slow inference doesn't build a backlog
    def __init__(self, url):
        self.cap = cv2.VideoCapture(url)
        if not self.cap.isOpened():
            raise SystemExit("Could not open the camera stream. Is the Mac on the same Wi-Fi as the board?")
        self.frame = None
        threading.Thread(target=self.loop, daemon=True).start()
    def loop(self):
        while True:
            ok, f = self.cap.read()
            if ok: self.frame = f
    def read(self):
        return self.frame
stream = Stream(f"http://{args.ip}:81/stream")
while stream.read() is None: time.sleep(0.1)


# ---------- on-screen instruction panel ----------
import numpy as np
W, H = 1400, 800
WHITE, YELLOW, GREEN, RED, GRAY = (255, 255, 255), (0, 220, 255), (80, 220, 80), (80, 80, 255), (170, 170, 170)

def wrap(text, scale, thick, width):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)[0][0] > width and cur:
            lines.append(cur); cur = wd
        else:
            cur = t
    if cur: lines.append(cur)
    return lines

def put(img, text, x, y, scale, color, thick=2, width=None):
    lines = wrap(text, scale, thick, width) if width else [text]
    h = int(42 * scale) + 8
    for i, ln in enumerate(lines):
        cv2.putText(img, ln, (x, y + i * h), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
    return y + len(lines) * h

def panel(header, now_text, remaining, next_text, video=None, status="", now_color=YELLOW):
    if args.no_panel: return None
    img = np.zeros((H, W, 3), np.uint8)
    put(img, header, 30, 55, 1.1, GRAY, 2)
    if video is not None:
        v = cv2.resize(video, (560, 420))
        img[100:520, W - 590:W - 30] = v
        put(img, status, W - 590, 555, 0.7, WHITE, 2)
    tw = W - 660
    put(img, "NOW:", 30, 140, 1.2, GRAY, 2)
    y = put(img, now_text, 30, 210, 1.7, now_color, 4, tw)
    if remaining is not None:
        put(img, f"{remaining:0.0f}s", 30, max(y + 110, 420), 4.0, WHITE, 8)
    if next_text:
        put(img, "NEXT: " + next_text, 30, 640, 1.0, GRAY, 2, tw)
    put(img, "q = quit", 30, H - 25, 0.6, GRAY, 1)
    cv2.imshow("LoCoFusion trials", img)
    k = cv2.waitKey(1) & 0xFF
    if k == ord("q"): raise KeyboardInterrupt
    return k


out = f"results_{datetime.now():%Y%m%d_%H%M%S}"
os.makedirs(out)

def run_trial(tid, next_tid):
    name, setup, phases = TRIALS[tid]
    print(f"\n=== {tid}: {name} ===\n  Setup: {setup}")
    say(f"Trial {tid[1:]}: {name}. {setup} Starting in {args.countdown} seconds.")
    header = f"Trial {tid[1:]} of {len(ORDER)-1}: {name}"
    cd_start = time.time()
    while time.time() - cd_start < args.countdown:
        panel(header, "GET READY. " + setup, args.countdown - (time.time() - cd_start), phases[0][2],
              stream.read(), now_color=GREEN)
        time.sleep(0.05)
    rows, cues = [], []
    t0 = time.time()
    snap_saved = False
    with open(f"{out}/{tid}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "phase", "label", "cam_conf", "radar_cm", "radar_age_ms", "cam_pred", "radar_pred", "fused_pred", "infer_ms"])
        for pi, (label, dur, text) in enumerate(phases):
            say(text)
            start = time.time()
            cues.append((start - t0, label))
            if pi + 1 < len(phases): nxt = phases[pi + 1][2]
            elif next_tid: nxt = f"Trial {next_tid[1:]}: {TRIALS[next_tid][0]}"
            else: nxt = "Finished"
            color = YELLOW if label in ("person",) or label.startswith("d") else (GRAY if label == "none" else WHITE)
            while time.time() - start < dur:
                frame = stream.read()
                ti = time.time()
                res = model(frame, classes=[0], verbose=False)[0]
                infer_ms = (time.time() - ti) * 1000
                conf = float(res.boxes.conf.max()) if len(res.boxes) else 0.0
                d, age = radar_cm, (time.time() - radar_t) * 1000
                cam_pred = conf > CAM_STRONG
                radar_pred = RADAR_MIN <= d <= RADAR_MAX
                fused = cam_pred or (radar_pred and conf > CAM_WEAK)
                lab = label if time.time() - start >= GUARD_S else "none"
                row = [round(time.time() - t0, 2), pi, lab, round(conf, 3), d, round(age), int(cam_pred), int(radar_pred), int(fused), round(infer_ms, 1)]
                w.writerow(row); rows.append(row)
                if label == "person" and not snap_saved and time.time() - start > 2:
                    cv2.imwrite(f"{out}/{tid}_snapshot.jpg", res.plot()); snap_saved = True
                status = f"camera {conf:.2f}   radar {d} cm   fused: {'PERSON' if fused else 'empty'}"
                panel(header + f"   (step {pi+1}/{len(phases)})", text, dur - (time.time() - start), nxt,
                      res.plot(), status, color)
    say(f"Trial {tid[1:]} done.")
    return rows, cues

def metrics(rows, col):
    tp = sum(1 for r in rows if r[2] == "person" and r[col]); fn = sum(1 for r in rows if r[2] == "person" and not r[col])
    fp = sum(1 for r in rows if r[2] == "empty" and r[col]);  tn = sum(1 for r in rows if r[2] == "empty" and not r[col])
    n = tp + tn + fp + fn
    if n == 0: return None
    rec = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    return dict(acc=(tp + tn) / n, rec=rec, fpr=fpr, n_p=tp + fn, n_e=fp + tn)

def pct(x): return "n/a" if x is None else f"{x:.0%}"

def sync_offsets(rows, cues):
    offs = []
    for (tc, lab) in cues:
        if lab != "person": continue
        win = [r for r in rows if tc <= r[0] <= tc + 4]
        tcam = next((r[0] for r in win if r[6]), None)
        trad = next((r[0] for r in win if r[7]), None)
        if tcam is not None and trad is not None:
            offs.append((tcam - tc, trad - tc))
    return offs

summary = ["# LoCoFusion midterm results", "", f"Run {datetime.now():%Y-%m-%d %H:%M}, camera {args.ip}, radar {args.port}",
           f"Rules: radar person = {RADAR_MIN}-{RADAR_MAX} cm; camera person = conf > {CAM_STRONG}; "
           f"fusion = camera > {CAM_STRONG} OR (radar AND camera > {CAM_WEAK})", ""]
all_rows = []
ORDER = [t.strip() for t in args.trials.split(",") if t.strip()]
if not args.no_panel and not args.no_wait:
    say("Ready. Press space on the laptop to start.")
    while True:
        k = panel("LoCoFusion midterm trials", "Press SPACE to start", None,
                  f"Trial {ORDER[0][1:]}: {TRIALS[ORDER[0]][0]}", stream.read(), now_color=GREEN)
        if k == ord(" "): break
        time.sleep(0.03)
say("Starting the LoCoFusion experiments.")
for i, tid in enumerate(ORDER):
    rows, cues = run_trial(tid, ORDER[i + 1] if i + 1 < len(ORDER) else None)
    all_rows += rows
    name = TRIALS[tid][0]
    summary += [f"## {tid}: {name}", ""]
    if tid == "T0":
        summary += ["| True distance | Radar mean (cm) | Radar std (cm) | Readings |", "| --- | --- | --- | --- |"]
        for lab in ("d100", "d200", "d300"):
            ds = [r[4] for r in rows if r[2] == lab]
            if ds:
                summary.append(f"| {lab[1:]} cm | {statistics.mean(ds):.0f} | {statistics.pstdev(ds):.0f} | {len(ds)} |")
        summary.append("")
        continue
    summary += ["| Approach | Accuracy | Recall (person caught) | False-positive rate | Frames (person / empty) |",
                "| --- | --- | --- | --- | --- |"]
    for nm, col in (("Camera only", 6), ("Radar only", 7), ("Rule fusion", 8)):
        m = metrics(rows, col)
        if m: summary.append(f"| {nm} | {pct(m['acc'])} | {pct(m['rec'])} | {pct(m['fpr'])} | {m['n_p']} / {m['n_e']} |")
    if tid == "T7":
        offs = sync_offsets(rows, cues)
        if offs:
            cam = [o[0] for o in offs]; rad = [o[1] for o in offs]; diff = [o[1] - o[0] for o in offs]
            summary += ["", f"Detection delay after cue ({len(offs)} of 10 step-ins detected by both): camera {statistics.mean(cam)*1000:.0f} ms, "
                        f"radar {statistics.mean(rad)*1000:.0f} ms, radar minus camera {statistics.mean(diff)*1000:+.0f} ms "
                        f"(std {statistics.pstdev(diff)*1000:.0f} ms)"]
    summary.append("")

summary += ["## All scored trials combined", "", "| Approach | Accuracy | Recall | False-positive rate |", "| --- | --- | --- | --- |"]
scored = [r for r in all_rows if r[2] in ("person", "empty")]
for nm, col in (("Camera only", 6), ("Radar only", 7), ("Rule fusion", 8)):
    m = metrics(scored, col)
    if m: summary.append(f"| {nm} | {pct(m['acc'])} | {pct(m['rec'])} | {pct(m['fpr'])} |")
if all_rows:
    summary += ["", f"Mean camera inference on laptop: {statistics.mean(r[9] for r in all_rows):.0f} ms/frame; "
                f"mean radar sample age: {statistics.mean(r[5] for r in all_rows):.0f} ms"]

open(f"{out}/summary.md", "w").write("\n".join(summary) + "\n")
print("\n" + "\n".join(summary))
print(f"\nSaved to {out}/")
say("All trials finished.")

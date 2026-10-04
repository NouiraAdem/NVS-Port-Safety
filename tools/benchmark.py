"""
Headless benchmark for NVS Port Safety (CPU).

Compares YOLO tracking speed for different input sizes and backends
(PyTorch vs OpenVINO) on the SAME frames, so the numbers are comparable.
Frames are grabbed once into memory first, so the camera FPS does not
limit the measurement.

Run from the project root:
    python tools/benchmark.py                 # use the camera
    python tools/benchmark.py path/to/video.mp4   # or a video file

Results are printed and saved to storage/benchmark_<timestamp>.csv
"""

import csv
import os
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
from ultralytics import YOLO

MODEL_PT = Path("models/yolo11n.pt")
CAMERA_DEVICE = "/dev/video0"
CONF = 0.60

WARMUP_FRAMES = 10
MEASURE_FRAMES = 100

# (backend, input size)
CONFIGS = [
    ("PyTorch", 640),
    ("PyTorch", 480),
    ("PyTorch", 416),
    ("PyTorch", 320),
    ("OpenVINO", 416),
    ("OpenVINO", 320),
]


def grab_frames(source, count):
    if source:
        cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        sys.exit("Cannot open the video source.")

    frames = []
    print(f"Grabbing {count} frames (keep a person in view)...")
    while len(frames) < count:
        ok, frame = cap.read()
        if not ok:
            if source:  # video ended
                break
            continue
        frames.append(cv2.flip(frame, 1) if not source else frame)
    cap.release()

    if not frames:
        sys.exit("No frames captured.")
    return frames


def load_model(backend, imgsz):
    if backend == "PyTorch":
        return YOLO(str(MODEL_PT))

    # OpenVINO: export for this image size, then load the exported model.
    exported = YOLO(str(MODEL_PT)).export(
        format="openvino", imgsz=imgsz, half=False, verbose=False
    )
    return YOLO(exported, task="detect")


def percentile(values, p):
    values = sorted(values)
    index = min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))
    return values[index]


def run_config(backend, imgsz, frames):
    model = load_model(backend, imgsz)

    def step(frame):
        model.track(
            frame, persist=True, imgsz=imgsz, conf=CONF, verbose=False
        )

    for frame in frames[:WARMUP_FRAMES]:
        step(frame)

    times = []
    for frame in frames[WARMUP_FRAMES:WARMUP_FRAMES + MEASURE_FRAMES]:
        t0 = time.perf_counter()
        step(frame)
        times.append((time.perf_counter() - t0) * 1000.0)

    mean = statistics.mean(times)
    return {
        "backend": backend,
        "imgsz": imgsz,
        "frames": len(times),
        "mean_ms": round(mean, 1),
        "median_ms": round(statistics.median(times), 1),
        "p95_ms": round(percentile(times, 95), 1),
        "fps": round(1000.0 / mean, 1),
    }


def main():
    if not MODEL_PT.exists():
        sys.exit(f"Model not found: {MODEL_PT} (run from the project root)")

    source = sys.argv[1] if len(sys.argv) > 1 else None
    frames = grab_frames(source, WARMUP_FRAMES + MEASURE_FRAMES)

    print(f"\nCPU: {platform.processor() or platform.machine()} "
          f"| logical cores: {os.cpu_count()}")
    print(f"Model: {MODEL_PT.name} | conf={CONF} | "
          f"{len(frames)} frames\n")

    rows = []
    for backend, imgsz in CONFIGS:
        print(f"Running {backend} @ {imgsz} ...", flush=True)
        try:
            rows.append(run_config(backend, imgsz, frames))
        except Exception as error:
            print(f"  skipped: {error}")

    if not rows:
        sys.exit("No configuration finished.")

    base = next((r for r in rows if r["backend"] == "PyTorch"
                 and r["imgsz"] == 640), rows[0])
    for r in rows:
        r["speedup"] = round(r["fps"] / base["fps"], 2)

    print("\n{:<10} {:>6} {:>9} {:>11} {:>9} {:>7} {:>8}".format(
        "Backend", "Size", "Mean ms", "Median ms", "P95 ms", "FPS", "Speedup"))
    print("-" * 66)
    for r in rows:
        print("{:<10} {:>6} {:>9} {:>11} {:>9} {:>7} {:>7}x".format(
            r["backend"], r["imgsz"], r["mean_ms"], r["median_ms"],
            r["p95_ms"], r["fps"], r["speedup"]))

    Path("storage").mkdir(exist_ok=True)
    out = Path("storage") / f"benchmark_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved: {out}")
    print("Note: speedup is relative to PyTorch @ 640. "
          "Accuracy should be checked separately when reducing the size.")


if __name__ == "__main__":
    main()

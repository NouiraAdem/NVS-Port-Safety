# NVS Port Safety

Desktop application for real-time person detection and tracking with safety-zone monitoring. It detects people in a camera stream with YOLO, checks whether they enter defined safety zones, and keeps a log of intrusion and exit events with automatic snapshots.

This project is the prototype for my graduation thesis on object recognition based on deep learning methods.

## Features

- Real-time person detection and tracking (Ultralytics YOLO)
- Safety-zone monitoring: entry and exit events are recorded in an event log
- Automatic snapshots when an intrusion is detected
- Desktop interface built with PySide6
<<<<<<< HEAD
- Runs on CPU only (no GPU required): about 20 FPS in my tests, depending on hardware
>>>>>>> 2b5bb38 (Update FPS)
- Benchmark tool for measuring performance (`tools/benchmark.py`)

## Project structure

```
main.py        application entry point
camera/        camera capture worker
core/          detector, zone monitor, event log, snapshots
config/        application settings
ui/            main window and widgets
tools/         benchmark script
models/        YOLO model weights
archive/       earlier versions of the application
```

## Installation

```
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

`requirements-lock.txt` contains the exact versions of my development environment.

## Run

```
python main.py
```

A webcam is required. When using WSL, the camera must be attached to WSL first (for example with usbipd).

## Author

Adem Nouira

from pathlib import Path


# =========================================================
# NVS Port Safety - Project Settings
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

APP_NAME = "NVS Port Safety"
COMPANY_NAME = "Nouira Vision Systems"
TAGLINE = "AI Vision for Safer Port Operations"

MODEL_PATH = BASE_DIR / "models" / "yolo11n.pt"

CAMERA_DEVICE = "/dev/video0"

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

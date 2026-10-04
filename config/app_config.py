"""Application constants for NVS Port Safety."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Camera
CAMERA_DEVICE = "/dev/video0"
FRAME_W, FRAME_H = 640, 480

# Smaller = faster on CPU (320 / 416 / 480 / 640). None = model default.
INFERENCE_SIZE = 416

# Safety zone in 640x480 frame coordinates: (x1, y1, x2, y2)
DEFAULT_ZONE = (150, 300, 490, 470)

# Consecutive frames needed to confirm an entry / an exit.
ZONE_ENTER_FRAMES = 10
ZONE_EXIT_FRAMES = 15

# Ignore weak person detections for safety events.
PERSON_CONFIDENCE = 0.60

# Max events kept in the in-memory log.
MAX_EVENTS = 100

# Automatic snapshot saved at every INTRUSION event.
SNAPSHOT_ENABLED = True
SNAPSHOT_DIR = PROJECT_ROOT / "storage" / "snapshots"
SNAPSHOT_JPEG_QUALITY = 90

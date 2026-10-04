"""Save an evidence image when an intrusion is confirmed (no Qt)."""

from datetime import datetime
from pathlib import Path

import cv2


def save_intrusion_snapshot(
    frame, zone_rect, class_name, track_id, confidence, directory, quality=90
):
    """
    Draw the safety zone and a caption on a copy of `frame` and save it as
    a JPEG. Returns the file path as a string, or None if saving failed.
    """
    try:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        image = frame.copy()

        x1, y1, x2, y2 = zone_rect
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 2)

        caption = (
            f"INTRUSION  {class_name} #{track_id}  "
            f"{confidence * 100:.0f}%  {now:%Y-%m-%d %H:%M:%S}"
        )
        cv2.rectangle(image, (0, 0), (image.shape[1], 26), (0, 0, 120), -1)
        cv2.putText(
            image, caption, (8, 18), cv2.FONT_HERSHEY_SIMPLEX,
            0.5, (255, 255, 255), 1, cv2.LINE_AA,
        )

        path = directory / f"{now:%Y%m%d_%H%M%S}_intrusion_id{track_id}.jpg"
        ok = cv2.imwrite(
            str(path), image, [cv2.IMWRITE_JPEG_QUALITY, int(quality)]
        )
        return str(path) if ok else None
    except Exception:
        return None

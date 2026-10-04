"""Camera capture + YOLO tracking in a background thread."""

import time

import cv2
from PySide6.QtCore import QThread, Signal

from config.app_config import CAMERA_DEVICE, FRAME_H, FRAME_W


class TrackerWorker(QThread):
    opened = Signal(int, int, float)
    failed = Signal(str)
    result_ready = Signal(object, list, float, float)

    def __init__(self, model, conf, imgsz, parent=None):
        super().__init__(parent)
        self.model = model
        self.conf = conf
        self.imgsz = imgsz
        self._running = True

    def stop(self):
        self._running = False
        self.wait(4000)

    def _parse(self, result):
        detections = []
        boxes = result.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        ids = boxes.id
        names = self.model.names

        for index, box in enumerate(boxes):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(
                {
                    "track_id": int(ids[index]) if ids is not None else None,
                    "class_name": names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                    "cx": int((x1 + x2) / 2),
                    "cy": int((y1 + y2) / 2),
                }
            )
        return detections

    def run(self):
        cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

        if not cap.isOpened():
            cap.release()
            self.failed.emit("Unable to open camera.")
            return

        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
        cap.set(cv2.CAP_PROP_FPS, 30)

        self.opened.emit(
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            float(cap.get(cv2.CAP_PROP_FPS)),
        )

        imgsz = self.imgsz
        fps = 0.0
        frames = 0
        t0 = time.perf_counter()
        misses = 0

        while self._running:
            ok, frame = cap.read()

            if not ok or frame is None or frame.size == 0:
                misses += 1
                if misses > 40:
                    self.failed.emit("Camera stream lost.")
                    break
                self.msleep(10)
                continue

            misses = 0
            frame = cv2.flip(frame, 1)

            t_inf = time.perf_counter()
            try:
                kwargs = {
                    "persist": True,
                    "verbose": False,
                    "conf": self.conf,
                }
                if imgsz:
                    kwargs["imgsz"] = imgsz

                try:
                    results = self.model.track(frame, **kwargs)
                except TypeError:
                    # Detector wrapper does not accept imgsz.
                    kwargs.pop("imgsz", None)
                    imgsz = None
                    results = self.model.track(frame, **kwargs)

                result = results[0]
                detections = self._parse(result)
                annotated = result.plot(line_width=2)
            except Exception as error:
                self.failed.emit(f"Tracking error: {error}")
                break

            latency = (time.perf_counter() - t_inf) * 1000.0

            frames += 1
            now = time.perf_counter()
            if now - t0 >= 0.5:
                fps = frames / (now - t0)
                frames = 0
                t0 = now

            self.result_ready.emit(annotated, detections, fps, latency)

        cap.release()

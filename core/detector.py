# core/detector.py

from ultralytics import YOLO

from config.settings import MODEL_PATH


class ObjectDetector:
    """
    NVS Port Safety - YOLO Object Detection & Tracking Engine
    """

    def __init__(self):
        self.model = YOLO(str(MODEL_PATH))

    @property
    def names(self):
        """Return YOLO class names."""
        return self.model.names

    def __call__(self, source, verbose=False, **kwargs):
        """Allow detector(source) usage."""
        return self.model(
            source,
            verbose=verbose,
            **kwargs
        )

    def detect(
        self,
        source,
        conf=0.25,
        iou=0.45,
        classes=None,
        verbose=False,
        **kwargs
    ):
        """
        Run YOLO object detection.
        """

        return self.model.predict(
            source=source,
            conf=conf,
            iou=iou,
            classes=classes,
            verbose=verbose,
            **kwargs
        )

    def track(
        self,
        source,
        conf=0.25,
        iou=0.45,
        persist=True,
        classes=None,
        verbose=False,
        **kwargs
    ):
        """
        Run YOLO object tracking.

        Important:
        This method accepts 'conf' so the UI can safely call:

            detector.track(frame, conf=0.35)

        Tracking IDs are maintained by Ultralytics when
        persist=True.
        """

        return self.model.track(
            source=source,
            conf=conf,
            iou=iou,
            persist=persist,
            classes=classes,
            verbose=verbose,
            **kwargs
        )

    def get_class_name(self, class_id):
        """
        Return the class name for a YOLO class ID.
        """

        try:
            class_id = int(class_id)

            names = self.model.names

            if isinstance(names, dict):
                return names.get(class_id, str(class_id))

            if 0 <= class_id < len(names):
                return names[class_id]

        except Exception:
            pass

        return str(class_id)
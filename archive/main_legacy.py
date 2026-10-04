import sys
import time
import cv2

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ultralytics import YOLO


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Object Recognition AI")
        self.resize(1250, 780)

        # =========================
        # YOLO
        # =========================

        self.model = YOLO("yolo11n.pt")

        # =========================
        # Image
        # =========================

        self.current_image_path = None

        # =========================
        # Camera
        # =========================

        self.camera = None
        self.camera_running = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_camera)

        # =========================
        # Accurate FPS
        # =========================

        self.fps = 0.0
        self.fps_frame_count = 0
        self.fps_start_time = time.perf_counter()

        # =========================
        # Statistics
        # =========================

        self.detected_count = 0
        self.detected_objects = []

        # =========================
        # Main Widget
        # =========================

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 25, 30, 30)
        main_layout.setSpacing(18)

        # =========================
        # Header
        # =========================

        title = QLabel("Object Recognition AI")

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: 700;
                padding: 4px;
            }
        """)

        subtitle = QLabel(
            "AI-powered real-time object detection using YOLO"
        )

        subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        subtitle.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 15px;
                padding-bottom: 4px;
            }
        """)

        # =========================
        # Main Content
        # =========================

        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        # =========================
        # Image Card
        # =========================

        image_area = QFrame()
        image_area.setObjectName("imageCard")
        image_area.setMinimumSize(750, 480)

        image_layout = QVBoxLayout(image_area)

        image_layout.setContentsMargins(
            12,
            12,
            12,
            12
        )

        self.image_label = QLabel(
            "Camera / Image Preview"
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setMinimumSize(
            650,
            400
        )

        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #111827;
                color: #6b7280;
                border-radius: 12px;
                font-size: 18px;
            }
        """)

        image_layout.addWidget(
            self.image_label
        )

        # =========================
        # Dashboard
        # =========================

        dashboard = QFrame()

        dashboard.setObjectName(
            "dashboard"
        )

        dashboard.setMinimumWidth(300)
        dashboard.setMaximumWidth(340)

        dashboard_layout = QVBoxLayout(
            dashboard
        )

        dashboard_layout.setContentsMargins(
            20,
            20,
            20,
            20
        )

        dashboard_layout.setSpacing(14)

        dashboard_title = QLabel(
            "Detection Dashboard"
        )

        dashboard_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: 700;
            }
        """)

        dashboard_layout.addWidget(
            dashboard_title
        )

        # =========================
        # Camera Status
        # =========================

        camera_title = QLabel(
            "Camera Status"
        )

        camera_title.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 13px;
                font-weight: 600;
            }
        """)

        self.camera_status = QLabel(
            "● Camera Offline"
        )

        self.camera_status.setStyleSheet("""
            QLabel {
                color: #ef4444;
                font-size: 17px;
                font-weight: 700;
            }
        """)

        dashboard_layout.addWidget(
            camera_title
        )

        dashboard_layout.addWidget(
            self.camera_status
        )

        # =========================
        # FPS
        # =========================

        fps_title = QLabel(
            "Performance"
        )

        fps_title.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 13px;
                font-weight: 600;
                margin-top: 8px;
            }
        """)

        self.fps_label = QLabel(
            "FPS: 0.0"
        )

        self.fps_label.setStyleSheet("""
            QLabel {
                color: #60a5fa;
                font-size: 24px;
                font-weight: 700;
            }
        """)

        dashboard_layout.addWidget(
            fps_title
        )

        dashboard_layout.addWidget(
            self.fps_label
        )

        # =========================
        # Object Count
        # =========================

        count_title = QLabel(
            "Detected Objects"
        )

        count_title.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 13px;
                font-weight: 600;
                margin-top: 8px;
            }
        """)

        self.count_label = QLabel(
            "0"
        )

        self.count_label.setStyleSheet("""
            QLabel {
                color: #34d399;
                font-size: 30px;
                font-weight: 700;
            }
        """)

        dashboard_layout.addWidget(
            count_title
        )

        dashboard_layout.addWidget(
            self.count_label
        )

        # =========================
        # Objects List
        # =========================

        objects_title = QLabel(
            "Objects"
        )

        objects_title.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 13px;
                font-weight: 600;
                margin-top: 8px;
            }
        """)

        self.objects_label = QLabel(
            "No objects detected"
        )

        self.objects_label.setWordWrap(True)

        self.objects_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        self.objects_label.setStyleSheet("""
            QLabel {
                color: #d1d5db;
                background-color: #111827;
                border-radius: 10px;
                padding: 12px;
                font-size: 14px;
            }
        """)

        dashboard_layout.addWidget(
            objects_title
        )

        dashboard_layout.addWidget(
            self.objects_label
        )

        dashboard_layout.addStretch()

        # =========================
        # Status
        # =========================

        self.status_label = QLabel(
            "Ready"
        )

        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.status_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 13px;
                padding: 10px;
            }
        """)

        dashboard_layout.addWidget(
            self.status_label
        )

        # =========================
        # Add Main Content
        # =========================

        content_layout.addWidget(
            image_area,
            3
        )

        content_layout.addWidget(
            dashboard,
            1
        )

        # =========================
        # Buttons
        # =========================

        open_button = QPushButton(
            "Open Image"
        )

        detect_button = QPushButton(
            "Detect Objects"
        )

        self.camera_button = QPushButton(
            "Start Camera"
        )

        for button in (
            open_button,
            detect_button,
            self.camera_button,
        ):
            button.setMinimumHeight(52)

        open_button.clicked.connect(
            self.open_image
        )

        detect_button.clicked.connect(
            self.detect_objects
        )

        self.camera_button.clicked.connect(
            self.toggle_camera
        )

        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        button_layout.addWidget(
            open_button
        )

        button_layout.addWidget(
            detect_button
        )

        button_layout.addWidget(
            self.camera_button
        )

        # =========================
        # Main Layout
        # =========================

        main_layout.addWidget(
            title
        )

        main_layout.addWidget(
            subtitle
        )

        main_layout.addLayout(
            content_layout
        )

        main_layout.addLayout(
            button_layout
        )

        # =========================
        # Global Style
        # =========================

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b1120;
            }

            QFrame#imageCard {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 16px;
            }

            QFrame#dashboard {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 16px;
            }

            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 600;
                padding: 8px 18px;
            }

            QPushButton:hover {
                background-color: #3b82f6;
            }

            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)

    # =========================================================
    # UPDATE DASHBOARD
    # =========================================================

    def update_dashboard(self, detections):

        self.detected_objects = detections
        self.detected_count = len(detections)

        self.count_label.setText(
            str(self.detected_count)
        )

        if detections:
            self.objects_label.setText(
                "\n".join(detections)
            )
        else:
            self.objects_label.setText(
                "No objects detected"
            )

    # =========================================================
    # OPEN IMAGE
    # =========================================================

    def open_image(self):

        self.stop_camera()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp)"
        )

        if not file_path:
            return

        self.current_image_path = file_path

        pixmap = QPixmap(file_path)

        if pixmap.isNull():

            self.image_label.setText(
                "Unable to load image"
            )

            return

        self.status_label.setText(
            "Image loaded. Ready for detection."
        )

        self.show_pixmap(
            pixmap
        )

        self.update_dashboard([])

    # =========================================================
    # DETECT IMAGE
    # =========================================================

    def detect_objects(self):

        if not self.current_image_path:

            self.image_label.setText(
                "Please open an image first."
            )

            self.status_label.setText(
                "Please open an image first."
            )

            return

        try:

            self.status_label.setText(
                "Running YOLO detection..."
            )

            results = self.model(
                self.current_image_path
            )

            result = results[0]

            detections = []

            if (
                result.boxes is not None
                and len(result.boxes) > 0
            ):

                for box in result.boxes:

                    class_id = int(
                        box.cls[0]
                    )

                    confidence = float(
                        box.conf[0]
                    )

                    class_name = (
                        self.model.names[class_id]
                    )

                    detections.append(
                        f"{class_name} — "
                        f"{confidence * 100:.1f}%"
                    )

            self.update_dashboard(
                detections
            )

            if detections:

                self.status_label.setText(
                    "Detection completed."
                )

            else:

                self.status_label.setText(
                    "No objects detected."
                )

            result_image = result.plot()

            self.display_frame(
                result_image
            )

        except Exception as error:

            self.status_label.setText(
                f"Detection error: {error}"
            )

    # =========================================================
    # CAMERA BUTTON
    # =========================================================

    def toggle_camera(self):

        if self.camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    # =========================================================
    # START CAMERA
    # =========================================================

    def start_camera(self):

        try:

            self.camera = cv2.VideoCapture(
                "/dev/video0",
                cv2.CAP_V4L2
            )

            if not self.camera.isOpened():

                self.camera.release()
                self.camera = None

                self.camera_status.setText(
                    "● Camera Offline"
                )

                self.status_label.setText(
                    "Unable to open camera."
                )

                return

            self.camera.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(*"MJPG")
            )

            self.camera.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                640
            )

            self.camera.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                480
            )

            self.camera_running = True

            self.camera_button.setText(
                "Stop Camera"
            )

            self.camera_status.setText(
                "● Camera Online"
            )

            self.camera_status.setStyleSheet("""
                QLabel {
                    color: #22c55e;
                    font-size: 17px;
                    font-weight: 700;
                }
            """)

            self.status_label.setText(
                "Camera running — YOLO active."
            )

            # Reset accurate FPS measurement
            self.fps = 0.0
            self.fps_frame_count = 0
            self.fps_start_time = time.perf_counter()

            self.fps_label.setText(
                "FPS: 0.0"
            )

            self.timer.start(30)

        except Exception as error:

            self.camera = None
            self.camera_running = False

            self.status_label.setText(
                f"Camera error: {error}"
            )

    # =========================================================
    # UPDATE CAMERA
    # =========================================================

    def update_camera(self):

        if self.camera is None:
            return

        ret, frame = self.camera.read()

        if not ret:

            self.status_label.setText(
                "Unable to read camera frame."
            )

            return

        # Mirror camera image
        frame = cv2.flip(
            frame,
            1
        )

        # =========================
        # Accurate FPS
        # =========================

        self.fps_frame_count += 1

        current_time = time.perf_counter()

        elapsed = (
            current_time
            - self.fps_start_time
        )

        # Update FPS every 0.5 second
        if elapsed >= 0.5:

            self.fps = (
                self.fps_frame_count
                / elapsed
            )

            self.fps_frame_count = 0
            self.fps_start_time = current_time

            self.fps_label.setText(
                f"FPS: {self.fps:.1f}"
            )

        # =========================
        # YOLO
        # =========================

        try:

            results = self.model(
                frame,
                verbose=False
            )

            result = results[0]

            annotated_frame = result.plot()

            detections = []

            if (
                result.boxes is not None
                and len(result.boxes) > 0
            ):

                for box in result.boxes:

                    class_id = int(
                        box.cls[0]
                    )

                    confidence = float(
                        box.conf[0]
                    )

                    class_name = (
                        self.model.names[class_id]
                    )

                    detections.append(
                        f"{class_name} — "
                        f"{confidence * 100:.1f}%"
                    )

            self.update_dashboard(
                detections
            )

            self.display_frame(
                annotated_frame
            )

        except Exception as error:

            self.status_label.setText(
                f"YOLO error: {error}"
            )

    # =========================================================
    # STOP CAMERA
    # =========================================================

    def stop_camera(self):

        self.timer.stop()

        if self.camera is not None:

            self.camera.release()
            self.camera = None

        self.camera_running = False

        self.camera_button.setText(
            "Start Camera"
        )

        self.camera_status.setText(
            "● Camera Offline"
        )

        self.camera_status.setStyleSheet("""
            QLabel {
                color: #ef4444;
                font-size: 17px;
                font-weight: 700;
            }
        """)

        self.fps = 0.0
        self.fps_frame_count = 0
        self.fps_start_time = time.perf_counter()

        self.fps_label.setText(
            "FPS: 0.0"
        )

        self.update_dashboard([])

        self.status_label.setText(
            "Camera stopped."
        )

    # =========================================================
    # DISPLAY FRAME
    # =========================================================

    def display_frame(self, frame):

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        height, width, channels = (
            rgb_frame.shape
        )

        bytes_per_line = (
            channels * width
        )

        q_image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        pixmap = QPixmap.fromImage(
            q_image
        )

        self.show_pixmap(
            pixmap
        )

    # =========================================================
    # SHOW PIXMAP
    # =========================================================

    def show_pixmap(self, pixmap):

        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        self.image_label.setPixmap(
            scaled_pixmap
        )

    # =========================================================
    # CLOSE APPLICATION
    # =========================================================

    def closeEvent(self, event):

        self.stop_camera()

        event.accept()


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )
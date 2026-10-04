import sys
import time
from datetime import datetime

import cv2

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.detector import ObjectDetector


class MainWindow(QMainWindow):
    """
    NVS Port Safety
    Professional YOLO detection + tracking + safety-zone monitoring
    with an in-memory security event log.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("NVS Port Safety")
        self.resize(1360, 900)
        self.setMinimumSize(1100, 760)

        # =====================================================
        # YOLO
        # =====================================================

        self.model = ObjectDetector()

        # =====================================================
        # CAMERA
        # =====================================================

        self.camera = None
        self.camera_running = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        # =====================================================
        # FPS
        # =====================================================

        self.fps = 0.0
        self.fps_frame_count = 0
        self.fps_start_time = time.perf_counter()

        # =====================================================
        # IMAGE
        # =====================================================

        self.current_image_path = None

        # =====================================================
        # DETECTIONS
        # =====================================================

        self.detected_count = 0
        self.detected_objects = []

        # =====================================================
        # SAFETY ZONE
        # Verified for the 640x480 camera stream.
        # =====================================================

        self.zone_x1 = 150
        self.zone_y1 = 300
        self.zone_x2 = 490
        self.zone_y2 = 470

        # Safety-zone debounce:
        # require several consecutive frames to confirm ENTER/EXIT.
        # This prevents YOLO confidence/box flicker from creating
        # false security events.
        self.zone_enter_threshold = 10
        self.zone_exit_threshold = 15

        # Ignore weak person detections for safety events.
        # The camera/model can occasionally produce low-confidence
        # person boxes while tracking is changing.
        self.person_confidence_threshold = 0.60

        # Per-track safety-zone state.
        self.track_zone_state = {}

        self.zone_alert_count = 0
        self.current_intruders = set()

        # =====================================================
        # EVENT LOG
        # =====================================================

        self.event_log = []
        self.max_events = 100

        # =====================================================
        # BUILD UI
        # =====================================================

        self.build_ui()
        self.apply_styles()

    # =========================================================
    # UI
    # =========================================================

    def make_section_label(self, text):
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def make_value_label(self, text="0"):
        label = QLabel(text)
        label.setObjectName("metricValue")
        return label

    def build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 22)
        root.setSpacing(14)

        # -----------------------------------------------------
        # Header
        # -----------------------------------------------------
        header = QHBoxLayout()
        header.setSpacing(14)

        brand = QVBoxLayout()
        brand.setSpacing(0)

        eyebrow = QLabel("NVS  •  INTELLIGENT PORT SECURITY")
        eyebrow.setObjectName("eyebrow")

        title = QLabel("NVS Port Safety")
        title.setObjectName("appTitle")

        subtitle = QLabel("AI Vision Command Center  /  Real-time Safety Monitoring")
        subtitle.setObjectName("appSubtitle")

        brand.addWidget(eyebrow)
        brand.addWidget(title)
        brand.addWidget(subtitle)

        header.addLayout(brand)
        header.addStretch()

        clock_box = QVBoxLayout()
        clock_box.setSpacing(0)

        self.clock_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.clock_label.setObjectName("clockLabel")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.date_label = QLabel(datetime.now().strftime("%d %b %Y").upper())
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        clock_box.addWidget(self.clock_label)
        clock_box.addWidget(self.date_label)
        header.addLayout(clock_box)

        self.system_badge = QLabel("● SYSTEM READY")
        self.system_badge.setObjectName("systemBadge")
        self.system_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.system_badge)

        root.addLayout(header)

        # -----------------------------------------------------
        # Status strip
        # -----------------------------------------------------
        status_strip = QFrame()
        status_strip.setObjectName("statusStrip")
        strip = QHBoxLayout(status_strip)
        strip.setContentsMargins(14, 9, 14, 9)
        strip.setSpacing(18)

        self.camera_status_strip = QLabel("CAMERA  •  STANDBY")
        self.camera_status_strip.setObjectName("stripItem")

        engine_status = QLabel("AI ENGINE  •  YOLO TRACKING")
        engine_status.setObjectName("stripItem")

        zone_status_strip = QLabel("SAFETY ZONE  •  ARMED")
        zone_status_strip.setObjectName("stripItem")

        strip.addWidget(self.camera_status_strip)
        strip.addWidget(engine_status)
        strip.addWidget(zone_status_strip)
        strip.addStretch()
        root.addWidget(status_strip)

        # -----------------------------------------------------
        # Main content
        # -----------------------------------------------------
        main_row = QHBoxLayout()
        main_row.setSpacing(14)

        # -----------------------------------------------------
        # Live monitor
        # -----------------------------------------------------
        camera_card = QFrame()
        camera_card.setObjectName("card")

        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setContentsMargins(14, 14, 14, 14)
        camera_layout.setSpacing(10)

        camera_header = QHBoxLayout()
        camera_header.setSpacing(10)

        live_dot = QLabel("● LIVE MONITOR")
        live_dot.setObjectName("liveTitle")

        self.stream_info = QLabel("640 × 480  •  YOLO Tracking")
        self.stream_info.setObjectName("mutedText")
        self.stream_info.setAlignment(Qt.AlignmentFlag.AlignRight)

        camera_header.addWidget(live_dot)
        camera_header.addStretch()
        camera_header.addWidget(self.stream_info)
        camera_layout.addLayout(camera_header)

        video_frame = QFrame()
        video_frame.setObjectName("videoFrame")
        video_layout = QVBoxLayout(video_frame)
        video_layout.setContentsMargins(2, 2, 2, 2)

        self.image_label = QLabel(
            "CAMERA OFFLINE\n\nPress  Start Camera  to begin monitoring"
        )
        self.image_label.setObjectName("imagePreview")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(700, 440)

        video_layout.addWidget(self.image_label)
        camera_layout.addWidget(video_frame, 1)

        video_meta = QHBoxLayout()
        video_meta.setSpacing(8)

        self.video_state_label = QLabel("● STANDBY")
        self.video_state_label.setObjectName("videoState")

        hint = QLabel("Mirrored preview  •  640 × 480  •  Safety monitoring enabled")
        hint.setObjectName("mutedText")

        video_meta.addWidget(self.video_state_label)
        video_meta.addWidget(hint)
        video_meta.addStretch()
        camera_layout.addLayout(video_meta)

        main_row.addWidget(camera_card, 3)

        # -----------------------------------------------------
        # Detection dashboard
        # -----------------------------------------------------
        dashboard = QFrame()
        dashboard.setObjectName("card")

        dash = QVBoxLayout(dashboard)
        dash.setContentsMargins(16, 16, 16, 16)
        dash.setSpacing(10)

        dashboard_title = QLabel("Detection Dashboard")
        dashboard_title.setObjectName("cardTitleLarge")
        dash.addWidget(dashboard_title)

        dashboard_subtitle = QLabel("REAL-TIME SYSTEM TELEMETRY")
        dashboard_subtitle.setObjectName("eyebrow")
        dash.addWidget(dashboard_subtitle)

        self.camera_status = QLabel("● Camera Offline")
        self.camera_status.setObjectName("statusOffline")
        dash.addWidget(self.camera_status)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)

        fps_box = QFrame()
        fps_box.setObjectName("metricCard")
        fps_layout = QVBoxLayout(fps_box)
        fps_layout.setContentsMargins(12, 10, 12, 10)
        fps_layout.setSpacing(2)
        fps_layout.addWidget(self.make_section_label("FPS"))
        self.fps_label = self.make_value_label("0.0")
        fps_layout.addWidget(self.fps_label)
        fps_hint = QLabel("STREAM RATE")
        fps_hint.setObjectName("metricHint")
        fps_layout.addWidget(fps_hint)
        metrics.addWidget(fps_box)

        objects_box = QFrame()
        objects_box.setObjectName("metricCard")
        objects_layout = QVBoxLayout(objects_box)
        objects_layout.setContentsMargins(12, 10, 12, 10)
        objects_layout.setSpacing(2)
        objects_layout.addWidget(self.make_section_label("TRACKED"))
        self.count_label = self.make_value_label("0")
        objects_layout.addWidget(self.count_label)
        objects_hint = QLabel("ACTIVE OBJECTS")
        objects_hint.setObjectName("metricHint")
        objects_layout.addWidget(objects_hint)
        metrics.addWidget(objects_box)

        dash.addLayout(metrics)

        zone_box = QFrame()
        zone_box.setObjectName("zoneCard")
        zone_layout = QVBoxLayout(zone_box)
        zone_layout.setContentsMargins(14, 12, 14, 12)
        zone_layout.setSpacing(2)

        zone_title = QLabel("SAFETY ZONE")
        zone_title.setObjectName("sectionLabel")
        zone_layout.addWidget(zone_title)

        self.zone_status = QLabel("● CLEAR")
        self.zone_status.setObjectName("zoneClear")
        zone_layout.addWidget(self.zone_status)

        self.zone_hint = QLabel("Monitored area is currently clear")
        self.zone_hint.setObjectName("zoneHint")
        zone_layout.addWidget(self.zone_hint)

        dash.addWidget(zone_box)

        alerts_box = QFrame()
        alerts_box.setObjectName("alertCard")
        alerts_layout = QVBoxLayout(alerts_box)
        alerts_layout.setContentsMargins(14, 12, 14, 12)
        alerts_layout.setSpacing(1)

        alerts_layout.addWidget(self.make_section_label("SECURITY EVENTS"))

        self.alert_label = QLabel("0")
        self.alert_label.setObjectName("alertNumber")
        alerts_layout.addWidget(self.alert_label)

        self.intruder_label = QLabel("No active intruders")
        self.intruder_label.setObjectName("mutedText")
        alerts_layout.addWidget(self.intruder_label)

        dash.addWidget(alerts_box)

        objects_header = QHBoxLayout()
        objects_header.addWidget(self.make_section_label("DETECTED OBJECTS"))
        objects_header.addStretch()
        live_objects = QLabel("LIVE")
        live_objects.setObjectName("miniBadge")
        objects_header.addWidget(live_objects)
        dash.addLayout(objects_header)

        self.objects_label = QLabel("No objects detected")
        self.objects_label.setObjectName("objectsPanel")
        self.objects_label.setWordWrap(True)
        self.objects_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        dash.addWidget(self.objects_label, 1)

        self.status_label = QLabel("System ready — awaiting camera input.")
        self.status_label.setObjectName("statusText")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dash.addWidget(self.status_label)

        main_row.addWidget(dashboard, 1)
        root.addLayout(main_row, 6)

        # -----------------------------------------------------
        # Control bar
        # -----------------------------------------------------
        controls_card = QFrame()
        controls_card.setObjectName("controlBar")
        controls = QHBoxLayout(controls_card)
        controls.setContentsMargins(10, 10, 10, 10)
        controls.setSpacing(8)

        control_title = QLabel("CONTROL")
        control_title.setObjectName("controlLabel")
        controls.addWidget(control_title)

        self.open_button = QPushButton("Open Image")
        self.detect_button = QPushButton("Detect Objects")
        self.camera_button = QPushButton("Start Camera")
        self.clear_events_button = QPushButton("Clear Event Log")

        self.open_button.setObjectName("secondaryButton")
        self.detect_button.setObjectName("secondaryButton")
        self.camera_button.setObjectName("primaryButton")
        self.clear_events_button.setObjectName("dangerButton")

        for button in (
            self.open_button,
            self.detect_button,
            self.camera_button,
            self.clear_events_button,
        ):
            button.setMinimumHeight(42)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.open_button.clicked.connect(self.open_image)
        self.detect_button.clicked.connect(self.detect_objects)
        self.camera_button.clicked.connect(self.toggle_camera)
        self.clear_events_button.clicked.connect(self.clear_event_log)

        controls.addWidget(self.open_button)
        controls.addWidget(self.detect_button)
        controls.addWidget(self.camera_button)
        controls.addStretch()
        controls.addWidget(self.clear_events_button)

        root.addWidget(controls_card)

        # -----------------------------------------------------
        # Event log
        # -----------------------------------------------------
        log_card = QFrame()
        log_card.setObjectName("card")

        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 14, 16, 14)
        log_layout.setSpacing(8)

        log_header = QHBoxLayout()

        log_title_box = QVBoxLayout()
        log_title_box.setSpacing(1)

        log_title = QLabel("Security Event Log")
        log_title.setObjectName("cardTitle")

        log_subtitle = QLabel(
            "Stable zone entries and exits  •  newest events first"
        )
        log_subtitle.setObjectName("mutedText")

        log_title_box.addWidget(log_title)
        log_title_box.addWidget(log_subtitle)

        log_header.addLayout(log_title_box)
        log_header.addStretch()

        event_status = QLabel("EVENT STREAM")
        event_status.setObjectName("miniBadge")
        log_header.addWidget(event_status)

        self.event_count_label = QLabel("0 events")
        self.event_count_label.setObjectName("eventCount")
        log_header.addWidget(self.event_count_label)

        log_layout.addLayout(log_header)

        self.event_table = QTableWidget(0, 6)
        self.event_table.setObjectName("eventTable")
        self.event_table.setHorizontalHeaderLabels(
            ["TIME", "EVENT", "OBJECT", "TRACK ID", "CONFIDENCE", "ZONE"]
        )

        self.event_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.event_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.event_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.event_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.event_table.verticalHeader().setVisible(False)
        self.event_table.setAlternatingRowColors(True)
        self.event_table.setMinimumHeight(165)
        self.event_table.setMaximumHeight(215)

        table_header = self.event_table.horizontalHeader()
        table_header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        table_header.setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        table_header.setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        table_header.setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        table_header.setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        table_header.setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )

        log_layout.addWidget(self.event_table)
        root.addWidget(log_card, 2)

        self.update_event_count()

    def update_clock(self):
        if hasattr(self, "clock_label"):
            self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))
            self.date_label.setText(datetime.now().strftime("%d %b %Y").upper())

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#central {
                background-color: #07101d;
                color: #e8f0fa;
            }
            QLabel { color: #e8f0fa; }
            QLabel#eyebrow {
                color: #4fd1c5;
                font-size: 9px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QLabel#appTitle {
                color: #f8fbff;
                font-size: 32px;
                font-weight: 900;
            }
            QLabel#appSubtitle {
                color: #8295ad;
                font-size: 12px;
            }
            QLabel#clockLabel {
                color: #dcecff;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#dateLabel {
                color: #6f829b;
                font-size: 9px;
                font-weight: 800;
                letter-spacing: 1px;
            }
            QLabel#systemBadge {
                background-color: #0c201d;
                color: #49e1b2;
                border: 1px solid #1c5d50;
                border-radius: 15px;
                padding: 8px 14px;
                font-size: 11px;
                font-weight: 900;
                min-width: 118px;
            }
            QFrame#statusStrip {
                background-color: #0b1727;
                border: 1px solid #1b3048;
                border-radius: 9px;
            }
            QLabel#stripItem {
                color: #7890aa;
                font-size: 9px;
                font-weight: 900;
                padding: 2px 6px;
            }
            QFrame#card {
                background-color: #101c2d;
                border: 1px solid #21364e;
                border-radius: 15px;
            }
            QLabel#liveTitle {
                color: #52e0bd;
                font-size: 12px;
                font-weight: 900;
            }
            QLabel#cardTitle {
                color: #f6f9fd;
                font-size: 15px;
                font-weight: 900;
            }
            QLabel#cardTitleLarge {
                color: #f6f9fd;
                font-size: 19px;
                font-weight: 900;
            }
            QLabel#mutedText {
                color: #71869f;
                font-size: 10px;
                font-weight: 700;
            }
            QLabel#imagePreview {
                background-color: #050b13;
                color: #4f647c;
                border: 1px solid #1b3148;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }
            QFrame#videoFrame {
                background-color: #050b13;
                border: 1px solid #29445f;
                border-radius: 11px;
            }
            QLabel#videoState {
                color: #6f849d;
                font-size: 9px;
                font-weight: 900;
            }
            QLabel#statusOffline {
                color: #f08b8b;
                font-size: 13px;
                font-weight: 900;
            }
            QLabel#statusOnline {
                color: #4fe0ad;
                font-size: 13px;
                font-weight: 900;
            }
            QFrame#metricCard {
                background-color: #0b1625;
                border: 1px solid #20364d;
                border-radius: 10px;
            }
            QLabel#metricValue {
                color: #66a8ff;
                font-size: 27px;
                font-weight: 900;
            }
            QLabel#metricHint {
                color: #536a84;
                font-size: 8px;
                font-weight: 900;
            }
            QLabel#sectionLabel {
                color: #71869f;
                font-size: 9px;
                font-weight: 900;
                letter-spacing: 1px;
            }
            QFrame#zoneCard {
                background-color: #09221b;
                border: 1px solid #1b5b47;
                border-radius: 10px;
            }
            QLabel#zoneClear {
                color: #42e2ae;
                font-size: 17px;
                font-weight: 900;
            }
            QLabel#zoneAlert {
                color: #ff6670;
                font-size: 17px;
                font-weight: 900;
            }
            QLabel#zoneHint {
                color: #658875;
                font-size: 9px;
            }
            QFrame#alertCard {
                background-color: #1c1119;
                border: 1px solid #563047;
                border-radius: 10px;
            }
            QLabel#alertNumber {
                color: #ff6f87;
                font-size: 28px;
                font-weight: 900;
            }
            QLabel#objectsPanel {
                background-color: #091523;
                border: 1px solid #1d334a;
                border-radius: 9px;
                color: #d9e6f4;
                padding: 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#statusText {
                color: #6f849d;
                font-size: 9px;
                padding: 4px;
            }
            QLabel#eventCount {
                color: #8296ae;
                font-size: 10px;
                font-weight: 800;
                padding-left: 8px;
            }
            QLabel#miniBadge {
                background-color: #102d2a;
                color: #4fd5b3;
                border: 1px solid #1c594f;
                border-radius: 8px;
                padding: 4px 7px;
                font-size: 8px;
                font-weight: 900;
            }
            QFrame#controlBar {
                background-color: #0d1928;
                border: 1px solid #20364d;
                border-radius: 11px;
            }
            QLabel#controlLabel {
                color: #5f7690;
                font-size: 9px;
                font-weight: 900;
                padding: 0 8px 0 4px;
            }
            QPushButton {
                border: none;
                border-radius: 8px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 900;
                padding: 8px 15px;
            }
            QPushButton#primaryButton { background-color: #087f70; }
            QPushButton#primaryButton:hover { background-color: #0aa58f; }
            QPushButton#primaryButton:pressed { background-color: #06685d; }
            QPushButton#secondaryButton { background-color: #17365d; }
            QPushButton#secondaryButton:hover { background-color: #215083; }
            QPushButton#secondaryButton:pressed { background-color: #122a49; }
            QPushButton#dangerButton {
                background-color: #4b202d;
                color: #ffc4cf;
            }
            QPushButton#dangerButton:hover { background-color: #6a293c; }
            QTableWidget#eventTable {
                background-color: #081421;
                alternate-background-color: #0c1928;
                border: 1px solid #1c3147;
                border-radius: 8px;
                gridline-color: #15283b;
                color: #dbe8f5;
                font-size: 10px;
                selection-background-color: #173f68;
                selection-color: #ffffff;
                outline: none;
            }
            QTableWidget#eventTable::item {
                padding: 5px;
                border-bottom: 1px solid #122337;
            }
            QHeaderView::section {
                background-color: #0c1b2b;
                color: #71869f;
                border: none;
                border-bottom: 1px solid #21364e;
                padding: 7px 6px;
                font-size: 8px;
                font-weight: 900;
            }
            QScrollBar:vertical {
                background: #07111e;
                width: 8px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #2b425b;
                border-radius: 4px;
                min-height: 25px;
            }
            QScrollBar::handle:vertical:hover { background: #3c5d7d; }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)

    # =========================================================
    # DASHBOARD
    # =========================================================

    def update_dashboard(self, detections):
        self.detected_objects = detections
        self.detected_count = len(detections)

        self.count_label.setText(str(self.detected_count))

        if detections:
            self.objects_label.setText("\n".join(detections))
        else:
            self.objects_label.setText("No objects detected")

    def update_zone_visuals(self, alarm, intruders):
        if alarm:
            self.zone_status.setText("● INTRUSION ALERT")
            self.zone_status.setObjectName("zoneAlert")
            self.zone_status.setStyleSheet("""
                color: #ff5b5b;
                font-size: 16px;
                font-weight: 800;
            """)

            self.alert_label.setText(str(self.zone_alert_count))
            self.intruder_label.setText(
                f"{len(intruders)} active intruder(s)"
            )
            if hasattr(self, "zone_hint"):
                self.zone_hint.setText("Immediate attention required")
                self.zone_hint.setStyleSheet(
                    "color: #ff777f; font-size: 9px; font-weight: 800;"
                )
            self.intruder_label.setStyleSheet(
                "color: #ff8a8a; font-size: 12px; font-weight: 700;"
            )
        else:
            self.zone_status.setText("● CLEAR")
            self.zone_status.setObjectName("zoneClear")
            self.zone_status.setStyleSheet("""
                color: #34d399;
                font-size: 16px;
                font-weight: 800;
            """)

            self.alert_label.setText(str(self.zone_alert_count))
            self.intruder_label.setText("No active intruders")
            if hasattr(self, "zone_hint"):
                self.zone_hint.setText("Monitored area is currently clear")
                self.zone_hint.setStyleSheet("")
            self.intruder_label.setStyleSheet(
                "color: #8494aa; font-size: 12px;"
            )

    # =========================================================
    # EVENT LOG
    # =========================================================

    def add_event(self, event_type, class_name, track_id, confidence):
        timestamp = datetime.now().strftime("%H:%M:%S")

        event = {
            "time": timestamp,
            "event": event_type,
            "object": class_name,
            "track_id": track_id,
            "confidence": confidence,
            "zone": "ENTERED" if event_type == "INTRUSION" else "EXITED",
        }

        self.event_log.insert(0, event)
        self.event_log = self.event_log[: self.max_events]

        self.refresh_event_table()

    def refresh_event_table(self):
        self.event_table.setRowCount(len(self.event_log))

        for row, event in enumerate(self.event_log):
            values = [
                event["time"],
                event["event"],
                event["object"],
                str(event["track_id"]),
                f'{event["confidence"] * 100:.1f}%',
                event["zone"],
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter
                    | Qt.AlignmentFlag.AlignLeft
                )

                if column == 1:
                    if event["event"] == "INTRUSION":
                        item.setForeground(QColor("#ff6b6b"))
                        item.setFont(
                            QFont("Sans", 9, QFont.Weight.Bold)
                        )
                    else:
                        item.setForeground(QColor("#34d399"))
                        item.setFont(
                            QFont("Sans", 9, QFont.Weight.Bold)
                        )

                elif column == 4:
                    item.setForeground(QColor("#60a5fa"))

                self.event_table.setItem(row, column, item)

        self.update_event_count()

    def update_event_count(self):
        count = len(self.event_log)
        suffix = "event" if count == 1 else "events"
        self.event_count_label.setText(f"{count} {suffix}")

    def clear_event_log(self):
        self.event_log.clear()
        self.zone_alert_count = 0
        self.refresh_event_table()
        self.alert_label.setText("0")
        self.status_label.setText("Event log cleared.")

    # =========================================================
    # SAFETY ZONE
    # =========================================================

    def point_inside_zone(self, center_x, center_y):
        return (
            self.zone_x1 <= center_x <= self.zone_x2
            and self.zone_y1 <= center_y <= self.zone_y2
        )

    def get_people_in_zone(self, result):
        """
        Returns:
            {
                track_id: {
                    "class_name": "person",
                    "confidence": float
                }
            }
        """

        inside = {}

        if result.boxes is None or len(result.boxes) == 0:
            return inside

        boxes = result.boxes
        has_ids = boxes.id is not None

        for index, box in enumerate(boxes):
            class_id = int(box.cls[0])
            class_name = self.model.names[class_id]

            if class_name.lower() != "person":
                continue

            confidence = float(box.conf[0])

            # Safety events must be based on a reasonably confident
            # person detection, not a transient low-confidence box.
            if confidence < self.person_confidence_threshold:
                continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)

            if not self.point_inside_zone(center_x, center_y):
                continue

            if has_ids:
                track_id = int(boxes.id[index])
            else:
                track_id = 100000 + index

            inside[track_id] = {
                "class_name": class_name,
                "confidence": confidence,
            }

        return inside

    def update_zone_state(self, people_in_zone):
        """
        Stable per-track state machine.

        ENTER:
            10 consecutive inside frames -> one INTRUSION event.

        EXIT:
            15 consecutive frames outside the zone -> one EXIT event.

        This prevents tracker flicker from generating repeated alerts.
        """

        # Current inside tracks.
        for track_id, info in people_in_zone.items():
            state = self.track_zone_state.setdefault(
                track_id,
                {
                    "inside_frames": 0,
                    "outside_frames": 0,
                    "active": False,
                    "class_name": info["class_name"],
                    "confidence": info["confidence"],
                },
            )

            state["class_name"] = info["class_name"]
            state["confidence"] = info["confidence"]
            state["inside_frames"] += 1
            state["outside_frames"] = 0

            if (
                not state["active"]
                and state["inside_frames"] >= self.zone_enter_threshold
            ):
                state["active"] = True
                self.zone_alert_count += 1

                self.add_event(
                    "INTRUSION",
                    state["class_name"],
                    track_id,
                    state["confidence"],
                )

        # Tracks no longer inside.
        for track_id, state in list(self.track_zone_state.items()):
            if track_id in people_in_zone:
                continue

            state["outside_frames"] += 1
            state["inside_frames"] = 0

            if (
                state["active"]
                and state["outside_frames"] >= self.zone_exit_threshold
            ):
                state["active"] = False

                self.add_event(
                    "EXIT",
                    state["class_name"],
                    track_id,
                    state["confidence"],
                )

                state["outside_frames"] = self.zone_exit_threshold

        self.current_intruders = {
            track_id
            for track_id, state in self.track_zone_state.items()
            if state["active"]
        }

        # Clean up long-gone inactive tracks.
        for track_id, state in list(self.track_zone_state.items()):
            if (
                not state["active"]
                and state["outside_frames"] > 60
            ):
                del self.track_zone_state[track_id]

        return self.current_intruders

    def draw_safety_zone(self, frame):
        alarm = bool(self.current_intruders)

        if alarm:
            color = (0, 0, 255)
            thickness = 3
            label = "!! SAFETY ALERT !!"
            label_y = max(35, self.zone_y1 - 12)
        else:
            color = (0, 210, 0)
            thickness = 2
            label = "SAFETY ZONE"
            label_y = max(30, self.zone_y1 - 10)

        cv2.rectangle(
            frame,
            (self.zone_x1, self.zone_y1),
            (self.zone_x2, self.zone_y2),
            color,
            thickness,
        )

        cv2.putText(
            frame,
            label,
            (self.zone_x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.68,
            color,
            2,
            cv2.LINE_AA,
        )

        return frame

    # =========================================================
    # OPEN IMAGE
    # =========================================================

    def open_image(self):
        self.stop_camera()

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp)",
        )

        if not file_path:
            return

        self.current_image_path = file_path
        pixmap = QPixmap(file_path)

        if pixmap.isNull():
            self.image_label.setText("Unable to load image")
            return

        self.status_label.setText(
            "Image loaded. Ready for detection."
        )

        self.show_pixmap(pixmap)
        self.update_dashboard([])

    # =========================================================
    # IMAGE DETECTION
    # =========================================================

    def detect_objects(self):
        if not self.current_image_path:
            self.image_label.setText("Please open an image first.")
            self.status_label.setText("Please open an image first.")
            return

        try:
            self.status_label.setText("Running YOLO detection...")

            results = self.model(
                self.current_image_path,
                verbose=False,
            )

            result = results[0]
            detections = []

            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = self.model.names[class_id]

                    detections.append(
                        f"{class_name} — {confidence * 100:.1f}%"
                    )

            self.update_dashboard(detections)

            if detections:
                self.status_label.setText("Detection completed.")
            else:
                self.status_label.setText("No objects detected.")

            result_image = result.plot()
            self.display_frame(result_image)

        except Exception as error:
            self.status_label.setText(
                f"Detection error: {error}"
            )

    # =========================================================
    # CAMERA CONTROL
    # =========================================================

    def toggle_camera(self):
        if self.camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        try:
            self.camera = cv2.VideoCapture(
                "/dev/video0",
                cv2.CAP_V4L2,
            )

            if not self.camera.isOpened():
                self.camera.release()
                self.camera = None
                self.camera_status.setText("● Camera Offline")
                self.status_label.setText(
                    "Unable to open camera."
                )
                return

            # Verified camera mode: MJPG 640x480 @ 30 FPS.
            self.camera.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(*"MJPG"),
            )
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)

            actual_width = int(
                self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            )
            actual_height = int(
                self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            )
            actual_fps = self.camera.get(cv2.CAP_PROP_FPS)

            self.camera_running = True

            self.camera_button.setText("Stop Camera")
            self.camera_button.setObjectName("dangerButton")

            self.camera_status.setText("● Camera Online")
            self.camera_status.setObjectName("statusOnline")
            self.camera_status_strip.setText("CAMERA  •  ONLINE")
            self.camera_status_strip.setStyleSheet(
                "color: #49e1b2; font-weight: 900;"
            )
            self.video_state_label.setText("● LIVE")
            self.video_state_label.setStyleSheet(
                "color: #49e1b2; font-weight: 900;"
            )

            self.system_badge.setText("● SYSTEM ONLINE")
            self.system_badge.setStyleSheet("""
                background-color: #102a20;
                color: #34d399;
                border: 1px solid #1f5d46;
                border-radius: 16px;
                padding: 7px 13px;
                font-size: 12px;
                font-weight: 700;
            """)

            self.stream_info.setText(
                f"{actual_width} × {actual_height}  •  "
                f"Tracking @ {actual_fps:.0f} FPS"
            )

            self.status_label.setText(
                "Tracking active — Safety zone monitoring."
            )

            # Reset runtime tracking state, not the event history.
            self.fps = 0.0
            self.fps_frame_count = 0
            self.fps_start_time = time.perf_counter()

            self.track_zone_state.clear()
            self.current_intruders.clear()
            self.zone_alert_count = 0
            self.alert_label.setText("0")

            self.update_zone_visuals(False, set())

            self.fps_label.setText("0.0")
            self.timer.start(30)

            self.camera_status.style().unpolish(self.camera_status)
            self.camera_status.style().polish(self.camera_status)
            self.camera_button.style().unpolish(self.camera_button)
            self.camera_button.style().polish(self.camera_button)

        except Exception as error:
            if self.camera is not None:
                self.camera.release()

            self.camera = None
            self.camera_running = False
            self.camera_status.setText("● Camera Offline")
            self.camera_status.setObjectName("statusOffline")
            self.camera_status_strip.setText("CAMERA  •  ERROR")
            self.camera_status_strip.setStyleSheet(
                "color: #ff747e; font-weight: 900;"
            )
            self.video_state_label.setText("● ERROR")
            self.video_state_label.setStyleSheet(
                "color: #ff747e; font-weight: 900;"
            )
            self.status_label.setText(
                f"Camera error: {error}"
            )

    # =========================================================
    # CAMERA UPDATE
    # =========================================================

    def update_camera(self):
        if self.camera is None:
            return

        ret, frame = self.camera.read()

        if not ret or frame is None or frame.size == 0:
            self.status_label.setText(
                "Unable to read camera frame."
            )
            return

        frame = cv2.flip(frame, 1)

        # FPS
        self.fps_frame_count += 1
        current_time = time.perf_counter()
        elapsed = current_time - self.fps_start_time

        if elapsed >= 0.5:
            self.fps = self.fps_frame_count / elapsed
            self.fps_frame_count = 0
            self.fps_start_time = current_time
            self.fps_label.setText(f"{self.fps:.1f}")

        try:
            # YOLO tracking
            results = self.model.track(
                frame,
                persist=True,
                verbose=False,
                conf=self.person_confidence_threshold,
            )

            result = results[0]
            detections = []

            if result.boxes is not None and len(result.boxes) > 0:
                boxes = result.boxes
                has_ids = boxes.id is not None

                for index, box in enumerate(boxes):
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = self.model.names[class_id]

                    # Do not show weak detections in the dashboard.
                    # This keeps the UI and safety logic consistent.
                    if confidence < self.person_confidence_threshold:
                        continue

                    if has_ids:
                        track_id = int(boxes.id[index])
                        detections.append(
                            f"{class_name} #{track_id} — "
                            f"{confidence * 100:.1f}%"
                        )
                    else:
                        detections.append(
                            f"{class_name} — "
                            f"{confidence * 100:.1f}%"
                        )

            self.update_dashboard(detections)

            # Safety-zone state machine.
            people_in_zone = self.get_people_in_zone(result)
            intruders = self.update_zone_state(people_in_zone)

            alarm = bool(intruders)
            self.update_zone_visuals(alarm, intruders)

            if alarm:
                self.status_label.setText(
                    "⚠ SAFETY ALERT — Person inside safety zone."
                )
            else:
                self.status_label.setText(
                    "Tracking active — Safety zone clear."
                )

            # Draw YOLO + safety zone.
            annotated_frame = result.plot()
            annotated_frame = self.draw_safety_zone(
                annotated_frame
            )

            self.display_frame(annotated_frame)

        except Exception as error:
            self.status_label.setText(
                f"Tracking error: {error}"
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

        self.camera_button.setText("Start Camera")
        self.camera_button.setObjectName("primaryButton")

        self.camera_status.setText("● Camera Offline")
        self.camera_status.setObjectName("statusOffline")
        if hasattr(self, "camera_status_strip"):
            self.camera_status_strip.setText("CAMERA  •  STANDBY")
            self.camera_status_strip.setStyleSheet("")
        if hasattr(self, "video_state_label"):
            self.video_state_label.setText("● STANDBY")
            self.video_state_label.setStyleSheet("")

        self.system_badge.setText("● SYSTEM READY")
        self.system_badge.setStyleSheet("""
            background-color: #172235;
            color: #9fb0c5;
            border: 1px solid #304158;
            border-radius: 16px;
            padding: 7px 13px;
            font-size: 12px;
            font-weight: 700;
        """)

        self.fps = 0.0
        self.fps_frame_count = 0
        self.fps_start_time = time.perf_counter()

        self.fps_label.setText("0.0")
        self.update_dashboard([])

        self.track_zone_state.clear()
        self.current_intruders.clear()
        self.update_zone_visuals(False, set())

        self.stream_info.setText("640 × 480  •  YOLO Tracking")
        self.status_label.setText(
            "Camera stopped — press Start Camera to resume monitoring."
        )

        self.camera_status.style().unpolish(self.camera_status)
        self.camera_status.style().polish(self.camera_status)
        self.camera_button.style().unpolish(self.camera_button)
        self.camera_button.style().polish(self.camera_button)

    # =========================================================
    # DISPLAY
    # =========================================================

    def display_frame(self, frame):
        if frame is None or frame.size == 0:
            return

        try:
            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )
        except Exception as error:
            self.status_label.setText(
                f"Frame conversion error: {error}"
            )
            return

        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width

        q_image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888,
        ).copy()

        self.show_pixmap(QPixmap.fromImage(q_image))

    def show_pixmap(self, pixmap):
        if pixmap.isNull():
            return

        scaled_pixmap = pixmap.scaled(
            self.image_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setPixmap(scaled_pixmap)

    # =========================================================
    # RESIZE
    # =========================================================

    def resizeEvent(self, event):
        super().resizeEvent(event)

        current_pixmap = self.image_label.pixmap()

        if current_pixmap is not None and not current_pixmap.isNull():
            self.show_pixmap(current_pixmap)

    # =========================================================
    # CLOSE
    # =========================================================

    def closeEvent(self, event):
        self.stop_camera()
        if hasattr(self, "clock_timer"):
            self.clock_timer.stop()
        event.accept()


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("NVS Port Safety")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
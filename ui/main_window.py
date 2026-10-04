"""Main window: UI layout and wiring between camera, zone logic and log."""

from datetime import datetime

from pathlib import Path

import cv2

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from camera.worker import TrackerWorker
from config.app_config import (
    DEFAULT_ZONE,
    FRAME_H,
    FRAME_W,
    INFERENCE_SIZE,
    MAX_EVENTS,
    PERSON_CONFIDENCE,
    SNAPSHOT_DIR,
    SNAPSHOT_ENABLED,
    SNAPSHOT_JPEG_QUALITY,
    ZONE_ENTER_FRAMES,
    ZONE_EXIT_FRAMES,
)
from core.detector import ObjectDetector
from core.event_log import EventLog
from core.snapshot import save_intrusion_snapshot
from core.zone_monitor import ZoneMonitor
from ui.styles import APP_STYLESHEET
from ui.video_widget import VideoWidget
from ui.widgets import StatCard, repolish, set_state


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NVS Port Safety")
        self.resize(1440, 940)
        self.setMinimumSize(1180, 800)

        self.model = ObjectDetector()
        self.worker = None

        # Detections / image
        self.current_image_path = None
        self.detected_count = 0

        # Safety zone + event log (the logic lives in core/)
        self.person_confidence_threshold = PERSON_CONFIDENCE
        self.zone = ZoneMonitor(
            DEFAULT_ZONE,
            ZONE_ENTER_FRAMES,
            ZONE_EXIT_FRAMES,
            self.person_confidence_threshold,
        )
        self.events = EventLog(MAX_EVENTS)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.build_ui()
        self.apply_styles()
        self.video.set_zone(*self.zone.rect)
        self.update_zone_label()

    # =========================================================
    # UI
    # =========================================================

    def make_button(self, text, variant):
        button = QPushButton(text)
        button.setProperty("variant", variant)
        button.setMinimumHeight(42)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 18, 24, 20)
        root.setSpacing(14)

        root.addLayout(self.build_header())
        root.addWidget(self.build_status_strip())

        body = QHBoxLayout()
        body.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(12)
        left.addWidget(self.build_video_card(), 1)
        left.addWidget(self.build_control_bar())
        body.addLayout(left, 1)

        body.addWidget(self.build_dashboard())
        root.addLayout(body, 1)

        root.addWidget(self.build_event_log())

    # ---- header ---------------------------------------------

    def build_header(self):
        header = QHBoxLayout()
        header.setSpacing(14)

        logo = QLabel("NVS")
        logo.setObjectName("logo")
        logo.setFixedSize(52, 52)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(logo)

        brand = QVBoxLayout()
        brand.setSpacing(0)

        eyebrow = QLabel("INTELLIGENT PORT SECURITY")
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
        self.clock_label.setObjectName("clock")
        self.clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.date_label = QLabel(datetime.now().strftime("%d %b %Y").upper())
        self.date_label.setObjectName("date")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        clock_box.addWidget(self.clock_label)
        clock_box.addWidget(self.date_label)
        header.addLayout(clock_box)

        self.system_badge = QLabel("●  SYSTEM READY")
        self.system_badge.setObjectName("pill")
        self.system_badge.setProperty("state", "ready")
        self.system_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.system_badge.setMinimumWidth(150)
        header.addWidget(self.system_badge)

        return header

    def build_status_strip(self):
        strip_frame = QFrame()
        strip_frame.setObjectName("strip")
        strip = QHBoxLayout(strip_frame)
        strip.setContentsMargins(16, 9, 16, 9)
        strip.setSpacing(28)

        self.camera_status_strip = QLabel("CAMERA  •  STANDBY")
        self.camera_status_strip.setObjectName("stripItem")
        self.camera_status_strip.setProperty("state", "off")

        engine = QLabel("AI ENGINE  •  YOLO TRACKING")
        engine.setObjectName("stripItem")
        engine.setProperty("state", "on")

        zone = QLabel("SAFETY ZONE  •  ARMED")
        zone.setObjectName("stripItem")
        zone.setProperty("state", "on")

        strip.addWidget(self.camera_status_strip)
        strip.addWidget(engine)
        strip.addWidget(zone)
        strip.addStretch()
        return strip_frame

    # ---- video ----------------------------------------------

    def build_video_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        live_title = QLabel("●  LIVE MONITOR")
        live_title.setObjectName("liveTitle")

        self.stream_info = QLabel(f"{FRAME_W} × {FRAME_H}  •  YOLO Tracking")
        self.stream_info.setObjectName("muted")

        top.addWidget(live_title)
        top.addStretch()
        top.addWidget(self.stream_info)
        layout.addLayout(top)

        self.video = VideoWidget()
        self.video.zone_edited.connect(self.on_zone_edited)
        layout.addWidget(self.video, 1)

        meta = QHBoxLayout()
        self.video_state_label = QLabel("●  STANDBY")
        self.video_state_label.setObjectName("videoState")
        self.video_state_label.setProperty("state", "off")

        hint = QLabel("Mirrored preview  •  Safety monitoring enabled")
        hint.setObjectName("muted")

        meta.addWidget(self.video_state_label)
        meta.addWidget(hint)
        meta.addStretch()
        layout.addLayout(meta)

        return card

    def build_control_bar(self):
        bar = QFrame()
        bar.setObjectName("controlBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        label = QLabel("CONTROL")
        label.setObjectName("controlLabel")
        layout.addWidget(label)

        self.camera_button = self.make_button("▶  Start Camera", "primary")
        self.open_button = self.make_button("Open Image", "secondary")
        self.detect_button = self.make_button("Detect Objects", "secondary")
        self.edit_zone_button = self.make_button("Edit Zone", "ghost")
        self.edit_zone_button.setCheckable(True)
        self.export_button = self.make_button("Export CSV", "ghost")
        self.clear_events_button = self.make_button("Clear Event Log", "danger")

        self.camera_button.clicked.connect(self.toggle_camera)
        self.open_button.clicked.connect(self.open_image)
        self.detect_button.clicked.connect(self.detect_objects)
        self.edit_zone_button.toggled.connect(self.toggle_zone_edit)
        self.export_button.clicked.connect(self.export_events)
        self.clear_events_button.clicked.connect(self.clear_event_log)

        layout.addWidget(self.camera_button)
        layout.addWidget(self.open_button)
        layout.addWidget(self.detect_button)
        layout.addWidget(self.edit_zone_button)
        layout.addStretch()
        layout.addWidget(self.export_button)
        layout.addWidget(self.clear_events_button)
        return bar

    # ---- dashboard ------------------------------------------

    def build_dashboard(self):
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(390)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 12)
        layout.setSpacing(8)

        title = QLabel("Detection Dashboard")
        title.setObjectName("cardTitleLarge")
        sub = QLabel("REAL-TIME SYSTEM TELEMETRY")
        sub.setObjectName("eyebrow")
        layout.addWidget(title)
        layout.addWidget(sub)

        self.camera_status = QLabel("●  Camera Offline")
        self.camera_status.setObjectName("camStatus")
        self.camera_status.setProperty("state", "off")
        layout.addWidget(self.camera_status)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.fps_card = StatCard("FPS", "0.0", "STREAM RATE")
        self.latency_card = StatCard("LATENCY", "0", "MS / FRAME")
        self.tracked_card = StatCard("TRACKED", "0", "ACTIVE OBJECTS")
        self.alerts_card = StatCard("ALERTS", "0", "NO ACTIVE INTRUDERS")
        self.alerts_card.set_state("idle")

        grid.addWidget(self.fps_card, 0, 0)
        grid.addWidget(self.latency_card, 0, 1)
        grid.addWidget(self.tracked_card, 1, 0)
        grid.addWidget(self.alerts_card, 1, 1)
        layout.addLayout(grid)

        # Zone card
        self.zone_card = QFrame()
        self.zone_card.setObjectName("zoneCard")
        self.zone_card.setProperty("state", "clear")
        zl = QVBoxLayout(self.zone_card)
        zl.setContentsMargins(16, 12, 16, 12)
        zl.setSpacing(2)

        zt = QLabel("SAFETY ZONE")
        zt.setObjectName("statTitle")
        self.zone_status = QLabel("●  CLEAR")
        self.zone_status.setObjectName("zoneStatus")
        self.zone_hint = QLabel("Monitored area is currently clear")
        self.zone_hint.setObjectName("zoneHint")
        self.zone_coords = QLabel("")
        self.zone_coords.setObjectName("statHint")

        zl.addWidget(zt)
        zl.addWidget(self.zone_status)
        zl.addWidget(self.zone_hint)
        zl.addWidget(self.zone_coords)
        layout.addWidget(self.zone_card)

        # Confidence slider
        conf_row = QHBoxLayout()
        conf_title = QLabel("CONFIDENCE THRESHOLD")
        conf_title.setObjectName("statTitle")
        self.conf_value = QLabel(f"{self.person_confidence_threshold:.2f}")
        self.conf_value.setObjectName("confValue")
        conf_row.addWidget(conf_title)
        conf_row.addStretch()
        conf_row.addWidget(self.conf_value)
        layout.addLayout(conf_row)

        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(30, 95)
        self.conf_slider.setValue(int(self.person_confidence_threshold * 100))
        self.conf_slider.valueChanged.connect(self.on_conf_changed)
        layout.addWidget(self.conf_slider)

        # Objects list
        oh = QHBoxLayout()
        ot = QLabel("DETECTED OBJECTS")
        ot.setObjectName("statTitle")
        live = QLabel("LIVE")
        live.setObjectName("miniBadge")
        oh.addWidget(ot)
        oh.addStretch()
        oh.addWidget(live)
        layout.addLayout(oh)

        self.objects_list = QListWidget()
        self.objects_list.setObjectName("objectsList")
        self.objects_list.setSelectionMode(
            QListWidget.SelectionMode.NoSelection
        )
        self.objects_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.objects_list.setMinimumHeight(60)
        layout.addWidget(self.objects_list, 1)
        self.show_empty_objects()

        self.status_label = QLabel("System ready — awaiting camera input.")
        self.status_label.setObjectName("statusText")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        return card

    # ---- event log ------------------------------------------

    def build_event_log(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        head = QHBoxLayout()
        tb = QVBoxLayout()
        tb.setSpacing(1)
        title = QLabel("Security Event Log")
        title.setObjectName("cardTitle")
        sub = QLabel(
            "Stable zone entries and exits  •  newest first  •  "
            "double-click an event to view its snapshot"
        )
        sub.setObjectName("muted")
        tb.addWidget(title)
        tb.addWidget(sub)
        head.addLayout(tb)
        head.addStretch()

        badge = QLabel("EVENT STREAM")
        badge.setObjectName("miniBadge")
        self.event_count_label = QLabel("0 events")
        self.event_count_label.setObjectName("eventCount")
        head.addWidget(badge)
        head.addWidget(self.event_count_label)
        layout.addLayout(head)

        self.event_table = QTableWidget(0, 7)
        self.event_table.setObjectName("eventTable")
        self.event_table.cellDoubleClicked.connect(self.show_snapshot)
        self.event_table.setHorizontalHeaderLabels(
            ["TIME", "EVENT", "OBJECT", "TRACK ID", "CONFIDENCE", "ZONE",
             "SNAPSHOT"]
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
        self.event_table.setShowGrid(False)
        self.event_table.verticalHeader().setVisible(False)
        self.event_table.verticalHeader().setDefaultSectionSize(30)
        self.event_table.setAlternatingRowColors(True)
        self.event_table.setMinimumHeight(120)
        self.event_table.setMaximumHeight(150)

        header = self.event_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(90)

        layout.addWidget(self.event_table)
        self.update_event_count()
        return card

    # =========================================================
    # STYLES
    # =========================================================

    def apply_styles(self):
        self.setStyleSheet(APP_STYLESHEET)

    # =========================================================
    # SMALL HELPERS
    # =========================================================

    def update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%H:%M:%S"))
        self.date_label.setText(datetime.now().strftime("%d %b %Y").upper())

    def set_badge(self, text, state):
        self.system_badge.setText(text)
        set_state(self.system_badge, state)

    def update_zone_label(self):
        self.zone_coords.setText(
            f"ZONE  ({self.zone.x1}, {self.zone.y1})  →  "
            f"({self.zone.x2}, {self.zone.y2})"
        )

    def show_empty_objects(self):
        self.objects_list.clear()
        item = QListWidgetItem("No objects detected")
        item.setForeground(QColor("#5f7390"))
        self.objects_list.addItem(item)

    # =========================================================
    # DASHBOARD
    # =========================================================

    def update_dashboard(self, detections):
        self.detected_count = len(detections)
        self.tracked_card.set_value(str(self.detected_count))

        signature = tuple(
            (d["class_name"], d.get("track_id"), round(d["confidence"], 2))
            for d in detections
        )
        if signature == getattr(self, "_last_signature", None):
            return
        self._last_signature = signature

        self.objects_list.clear()

        if not detections:
            self.show_empty_objects()
            return

        for d in detections:
            label = d["class_name"]
            if d.get("track_id") is not None:
                label += f"  #{d['track_id']}"
            label += f"   •   {d['confidence'] * 100:.0f}%"
            self.objects_list.addItem(label)

    def update_zone_visuals(self, alarm, intruders):
        self.alerts_card.set_value(str(self.zone.alert_count))

        if alarm:
            self.zone_status.setText("●  INTRUSION ALERT")
            self.zone_hint.setText("Immediate attention required")
            set_state(self.zone_card, "alert")
            self.alerts_card.set_state("alert")
            self.alerts_card.set_hint(f"{len(intruders)} ACTIVE INTRUDER(S)")
        else:
            self.zone_status.setText("●  CLEAR")
            self.zone_hint.setText("Monitored area is currently clear")
            set_state(self.zone_card, "clear")
            self.alerts_card.set_state("idle")
            self.alerts_card.set_hint("NO ACTIVE INTRUDERS")

        self.video.set_alarm(alarm)

        if self.worker is not None:
            self.set_badge(
                "●  SYSTEM ALERT" if alarm else "●  SYSTEM ONLINE",
                "alert" if alarm else "online",
            )

    def on_conf_changed(self, value):
        self.person_confidence_threshold = value / 100.0
        self.zone.min_confidence = self.person_confidence_threshold
        self.conf_value.setText(f"{self.person_confidence_threshold:.2f}")
        if self.worker is not None:
            self.worker.conf = self.person_confidence_threshold

    # =========================================================
    # EVENT LOG
    # =========================================================

    def refresh_event_table(self):
        bold = QFont(self.font())
        bold.setBold(True)

        self.event_table.setRowCount(len(self.events.items))

        for row, event in enumerate(self.events.items):
            is_intrusion = event["event"] == "INTRUSION"
            values = [
                event["time"],
                ("▲  " if is_intrusion else "▼  ") + event["event"],
                event["object"],
                str(event["track_id"]),
                f'{event["confidence"] * 100:.1f}%',
                event["zone"],
                (
                    Path(event["snapshot"]).name
                    if event.get("snapshot")
                    else "—"
                ),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                if column == 1:
                    item.setForeground(
                        QColor("#f87171" if is_intrusion else "#34d399")
                    )
                    item.setFont(bold)
                elif column == 4:
                    item.setForeground(QColor("#60a5fa"))
                elif column == 5:
                    item.setForeground(
                        QColor("#fca5a5" if is_intrusion else "#86efac")
                    )
                elif column == 6:
                    item.setForeground(
                        QColor("#22d3ee" if event.get("snapshot") else "#5f7390")
                    )
                self.event_table.setItem(row, column, item)

        self.update_event_count()

    def update_event_count(self):
        count = len(self.events.items)
        self.event_count_label.setText(
            f"{count} {'event' if count == 1 else 'events'}"
        )

    def clear_event_log(self):
        self.events.clear()
        self.zone.alert_count = 0
        self.refresh_event_table()
        self.alerts_card.set_value("0")
        self.status_label.setText("Event log cleared.")

    def export_events(self):
        if not self.events.items:
            self.status_label.setText("No events to export.")
            return

        default = f"security_events_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Event Log", default, "CSV (*.csv)"
        )
        if not path:
            return

        try:
            self.events.export_csv(path)
            self.status_label.setText(
                f"Exported {len(self.events.items)} events."
            )
        except OSError as error:
            self.status_label.setText(f"Export failed: {error}")

    # =========================================================
    # SAFETY ZONE
    # =========================================================

    def toggle_zone_edit(self, checked):
        if checked and not self.video.has_image():
            self.edit_zone_button.blockSignals(True)
            self.edit_zone_button.setChecked(False)
            self.edit_zone_button.blockSignals(False)
            self.status_label.setText("Start the camera first to edit the zone.")
            return
        self.video.set_edit_mode(checked)

    def on_zone_edited(self, x1, y1, x2, y2):
        self.zone.set_rect(x1, y1, x2, y2)
        self.video.set_zone(x1, y1, x2, y2)
        self.update_zone_label()

        self.zone.reset_tracks()
        self.update_zone_visuals(False, set())

        self.edit_zone_button.setChecked(False)
        self.status_label.setText("Safety zone updated.")

    def process_zone(self, detections, frame=None):
        intruders, new_events = self.zone.update(detections)

        for event_type, class_name, track_id, confidence in new_events:
            snapshot = None

            if (
                SNAPSHOT_ENABLED
                and frame is not None
                and event_type == "INTRUSION"
            ):
                snapshot = save_intrusion_snapshot(
                    frame,
                    self.zone.rect,
                    class_name,
                    track_id,
                    confidence,
                    SNAPSHOT_DIR,
                    SNAPSHOT_JPEG_QUALITY,
                )

            self.events.add(
                event_type, class_name, track_id, confidence, snapshot
            )

        if new_events:
            self.refresh_event_table()

        return intruders

    def show_snapshot(self, row, _column):
        if row >= len(self.events.items):
            return

        path = self.events.items[row].get("snapshot")
        if not path or not Path(path).exists():
            self.status_label.setText("No snapshot for this event.")
            return

        pixmap = QPixmap(path)
        if pixmap.isNull():
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(Path(path).name)
        layout = QVBoxLayout(dialog)
        label = QLabel()
        label.setPixmap(
            pixmap.scaled(
                900,
                680,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(label)
        dialog.exec()

    # =========================================================
    # IMAGE MODE
    # =========================================================

    def open_image(self):
        self.stop_camera()

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "", "Images (*.jpg *.jpeg *.png *.bmp)"
        )
        if not file_path:
            return

        image = QImage(file_path)
        if image.isNull():
            self.status_label.setText("Unable to load image.")
            return

        self.current_image_path = file_path
        self.video.set_show_zone(False)
        self.video.set_image(image, live=False)
        self.update_dashboard([])
        self.status_label.setText("Image loaded. Ready for detection.")

    def detect_objects(self):
        if not self.current_image_path:
            self.status_label.setText("Please open an image first.")
            return

        try:
            self.status_label.setText("Running YOLO detection...")
            QApplication.processEvents()

            result = self.model(self.current_image_path, verbose=False)[0]
            detections = []

            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    detections.append(
                        {
                            "class_name": self.model.names[int(box.cls[0])],
                            "confidence": float(box.conf[0]),
                            "track_id": None,
                        }
                    )

            self.update_dashboard(detections)
            self.display_frame(result.plot())
            self.status_label.setText(
                "Detection completed." if detections else "No objects detected."
            )
        except Exception as error:
            self.status_label.setText(f"Detection error: {error}")

    # =========================================================
    # CAMERA
    # =========================================================

    def toggle_camera(self):
        if self.worker is not None:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        if self.worker is not None:
            return

        self.status_label.setText("Opening camera...")

        self.worker = TrackerWorker(
            self.model, self.person_confidence_threshold, INFERENCE_SIZE, self
        )
        self.worker.opened.connect(self.on_camera_opened)
        self.worker.failed.connect(self.on_camera_failed)
        self.worker.result_ready.connect(self.on_result)
        self.worker.start()

    def on_camera_opened(self, width, height, fps):
        if self.worker is None:
            return

        self.camera_button.setText("■  Stop Camera")
        self.camera_button.setProperty("variant", "stop")
        repolish(self.camera_button)

        self.camera_status.setText("●  Camera Online")
        set_state(self.camera_status, "live")

        self.camera_status_strip.setText("CAMERA  •  ONLINE")
        set_state(self.camera_status_strip, "on")
        self.video_state_label.setText("●  LIVE")
        set_state(self.video_state_label, "live")

        self.set_badge("●  SYSTEM ONLINE", "online")
        self.stream_info.setText(
            f"{width} × {height}  •  Tracking @ {fps:.0f} FPS"
        )
        self.status_label.setText("Tracking active — Safety zone monitoring.")

        self.zone.reset()
        self.update_zone_visuals(False, set())

        self.video.set_show_zone(True)

    def on_camera_failed(self, message):
        self.stop_camera(message)
        self.camera_status_strip.setText("CAMERA  •  ERROR")
        set_state(self.camera_status_strip, "err")
        self.video_state_label.setText("●  ERROR")
        set_state(self.video_state_label, "err")

    def on_result(self, frame, detections, fps, latency):
        if self.worker is None:
            return

        self.fps_card.set_value(f"{fps:.1f}")
        self.latency_card.set_value(f"{latency:.0f}")

        self.update_dashboard(detections)

        intruders = self.process_zone(detections, frame)
        alarm = bool(intruders)
        self.update_zone_visuals(alarm, intruders)

        self.status_label.setText(
            "SAFETY ALERT — Person inside safety zone."
            if alarm
            else "Tracking active — Safety zone clear."
        )

        self.display_frame(frame, live=True)

    def stop_camera(self, message=None):
        worker, self.worker = self.worker, None
        if worker is not None:
            worker.stop()
            worker.deleteLater()

        self.camera_button.setText("▶  Start Camera")
        self.camera_button.setProperty("variant", "primary")
        repolish(self.camera_button)

        self.camera_status.setText("●  Camera Offline")
        set_state(self.camera_status, "off")
        self.camera_status_strip.setText("CAMERA  •  STANDBY")
        set_state(self.camera_status_strip, "off")
        self.video_state_label.setText("●  STANDBY")
        set_state(self.video_state_label, "off")

        self.set_badge("●  SYSTEM READY", "ready")

        self.fps_card.set_value("0.0")
        self.latency_card.set_value("0")
        self.update_dashboard([])

        self.zone.reset_tracks()
        self.update_zone_visuals(False, set())

        if self.edit_zone_button.isChecked():
            self.edit_zone_button.setChecked(False)

        if worker is not None:
            self.video.clear()

        self.stream_info.setText(f"{FRAME_W} × {FRAME_H}  •  YOLO Tracking")
        self.status_label.setText(
            message
            or "Camera stopped — press Start Camera to resume monitoring."
        )

    # =========================================================
    # DISPLAY
    # =========================================================

    def display_frame(self, frame, live=False):
        if frame is None or frame.size == 0:
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(
            rgb.data, w, h, ch * w, QImage.Format.Format_RGB888
        ).copy()

        self.video.set_image(image, live=live)

    def closeEvent(self, event):
        self.stop_camera()
        self.clock_timer.stop()
        event.accept()

"""Application stylesheet (QSS)."""

APP_STYLESHEET = """
            QMainWindow, QWidget#central { background-color: #070c15; }
            QDialog { background-color: #070c15; }
            QWidget { color: #e6edf7; }
            QLabel { background: transparent; }

            QLabel#logo {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #22d3ee, stop:1 #3b82f6);
                color: #04121c;
                border-radius: 14px;
                font-size: 15px;
                font-weight: 900;
            }
            QLabel#eyebrow {
                color: #22d3ee; font-size: 10px; font-weight: 800;
            }
            QLabel#appTitle {
                color: #f8fbff; font-size: 27px; font-weight: 800;
            }
            QLabel#appSubtitle { color: #7b8aa3; font-size: 12px; }
            QLabel#clock {
                color: #e6edf7; font-size: 25px; font-weight: 700;
            }
            QLabel#date {
                color: #7b8aa3; font-size: 10px; font-weight: 700;
            }

            QLabel#pill {
                border-radius: 16px; padding: 9px 18px;
                font-size: 11px; font-weight: 800;
            }
            QLabel#pill[state="ready"] {
                background: #131b2b; color: #9fb0c8;
                border: 1px solid #2a3850;
            }
            QLabel#pill[state="online"] {
                background: #0d2a23; color: #34d399;
                border: 1px solid #1d6b55;
            }
            QLabel#pill[state="alert"] {
                background: #34131a; color: #f87171;
                border: 1px solid #8a2c38;
            }

            QFrame#strip {
                background: #0b1220; border: 1px solid #1b2740;
                border-radius: 10px;
            }
            QLabel#stripItem { font-size: 10px; font-weight: 800; }
            QLabel#stripItem[state="on"]  { color: #49b6a6; }
            QLabel#stripItem[state="off"] { color: #7b8aa3; }
            QLabel#stripItem[state="err"] { color: #f87171; }

            QFrame#card {
                background: #0e1525; border: 1px solid #1d2840;
                border-radius: 16px;
            }
            QLabel#liveTitle {
                color: #34d399; font-size: 12px; font-weight: 800;
            }
            QLabel#cardTitle {
                color: #f6f9fd; font-size: 16px; font-weight: 800;
            }
            QLabel#cardTitleLarge {
                color: #f6f9fd; font-size: 20px; font-weight: 800;
            }
            QLabel#muted {
                color: #71819b; font-size: 11px; font-weight: 600;
            }
            QLabel#videoState { font-size: 10px; font-weight: 800; }
            QLabel#videoState[state="off"]  { color: #71819b; }
            QLabel#videoState[state="live"] { color: #34d399; }
            QLabel#videoState[state="err"]  { color: #f87171; }

            QLabel#camStatus { font-size: 13px; font-weight: 800; }
            QLabel#camStatus[state="off"]  { color: #f08b8b; }
            QLabel#camStatus[state="live"] { color: #34d399; }

            QFrame#stat {
                background: #0a1120; border: 1px solid #1b2740;
                border-radius: 12px;
            }
            QLabel#statTitle {
                color: #71819b; font-size: 10px; font-weight: 800;
            }
            QLabel#statValue {
                color: #60a5fa; font-size: 25px; font-weight: 800;
            }
            QLabel#statHint {
                color: #4f5f79; font-size: 9px; font-weight: 700;
            }
            QFrame#stat[state="idle"] QLabel#statValue { color: #cbd5e1; }
            QFrame#stat[state="alert"] {
                background: #2a1219; border: 1px solid #7f2a35;
            }
            QFrame#stat[state="alert"] QLabel#statValue { color: #f87171; }
            QFrame#stat[state="alert"] QLabel#statHint  { color: #c98a92; }

            QFrame#zoneCard { border-radius: 12px; }
            QFrame#zoneCard[state="clear"] {
                background: #0b2720; border: 1px solid #1c6a52;
            }
            QFrame#zoneCard[state="alert"] {
                background: #2e1219; border: 1px solid #93303c;
            }
            QLabel#zoneStatus { font-size: 19px; font-weight: 800; }
            QFrame#zoneCard[state="clear"] QLabel#zoneStatus { color: #34d399; }
            QFrame#zoneCard[state="alert"] QLabel#zoneStatus { color: #f87171; }
            QLabel#zoneHint { font-size: 11px; font-weight: 600; }
            QFrame#zoneCard[state="clear"] QLabel#zoneHint { color: #6aa591; }
            QFrame#zoneCard[state="alert"] QLabel#zoneHint {
                color: #ff8d96; font-weight: 800;
            }

            QLabel#confValue {
                color: #22d3ee; font-size: 12px; font-weight: 800;
            }
            QSlider::groove:horizontal {
                height: 5px; background: #1b2740; border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #22d3ee; border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #e6edf7; width: 15px; height: 15px;
                margin: -6px 0; border-radius: 7px;
                border: 2px solid #22d3ee;
            }

            QLabel#miniBadge {
                background: #0f2c2a; color: #4fd5b3;
                border: 1px solid #1c594f; border-radius: 8px;
                padding: 3px 8px; font-size: 9px; font-weight: 800;
            }
            QListWidget#objectsList {
                background: #0a1120; border: 1px solid #1b2740;
                border-radius: 10px; padding: 4px; outline: none;
            }
            QListWidget#objectsList::item {
                padding: 7px 8px; border-radius: 6px;
                color: #d5e2f2; font-size: 12px; font-weight: 600;
            }
            QLabel#statusText { color: #71819b; font-size: 10px; padding: 2px; }

            QFrame#controlBar {
                background: #0c1322; border: 1px solid #1d2840;
                border-radius: 12px;
            }
            QLabel#controlLabel {
                color: #5f7390; font-size: 10px; font-weight: 800;
                padding: 0 8px 0 4px;
            }

            QPushButton {
                border: 1px solid transparent; border-radius: 9px;
                color: #ffffff; font-size: 12px; font-weight: 800;
                padding: 8px 18px;
            }
            QPushButton[variant="primary"] { background: #0a8f7c; }
            QPushButton[variant="primary"]:hover { background: #0cb199; }
            QPushButton[variant="primary"]:pressed { background: #077163; }
            QPushButton[variant="stop"] { background: #b4343f; }
            QPushButton[variant="stop"]:hover { background: #d1424e; }
            QPushButton[variant="secondary"] { background: #17335a; }
            QPushButton[variant="secondary"]:hover { background: #21487d; }
            QPushButton[variant="secondary"]:pressed { background: #122a49; }
            QPushButton[variant="ghost"] {
                background: transparent; border: 1px solid #2a3b57;
                color: #b4c4dc;
            }
            QPushButton[variant="ghost"]:hover { background: #15203a; }
            QPushButton[variant="ghost"]:checked {
                background: #083344; border: 1px solid #22d3ee;
                color: #67e8f9;
            }
            QPushButton[variant="danger"] {
                background: #3f1a25; color: #ffc4cf;
            }
            QPushButton[variant="danger"]:hover { background: #5e2536; }
            QPushButton:disabled { background: #162033; color: #5b6b85; }

            QLabel#eventCount {
                color: #8ea0ba; font-size: 11px; font-weight: 800;
                padding-left: 6px;
            }
            QTableWidget#eventTable {
                background: #0a1120; alternate-background-color: #0d1527;
                border: 1px solid #1b2740; border-radius: 10px;
                color: #dbe8f5; font-size: 11px; outline: none;
                selection-background-color: #173a63;
                selection-color: #ffffff;
            }
            QTableWidget#eventTable::item {
                padding: 4px 8px; border-bottom: 1px solid #111b2f;
            }
            QHeaderView::section {
                background: #0c1527; color: #71819b; border: none;
                border-bottom: 1px solid #1d2840;
                padding: 8px 8px; font-size: 9px; font-weight: 800;
            }
            QScrollBar:vertical {
                background: transparent; width: 9px; margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #2b3f5e; border-radius: 4px; min-height: 28px;
            }
            QScrollBar::handle:vertical:hover { background: #3d5a85; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """

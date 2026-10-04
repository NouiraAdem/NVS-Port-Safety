import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NVS Port Safety")
    app.setStyle("Fusion")

    font = QFont()
    font.setFamilies(["Inter", "Segoe UI", "Noto Sans", "DejaVu Sans"])
    font.setPointSize(10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
"""Small reusable widgets and style helpers."""

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def repolish(widget):
    """Re-apply the stylesheet after a dynamic property changed."""
    for w in [widget] + widget.findChildren(QWidget):
        w.style().unpolish(w)
        w.style().polish(w)
        w.update()


def set_state(widget, state):
    if widget.property("state") == state:
        return
    widget.setProperty("state", state)
    repolish(widget)


class StatCard(QFrame):
    def __init__(self, title, value="0", hint="", parent=None):
        super().__init__(parent)
        self.setObjectName("stat")
        self.setMinimumHeight(84)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(0)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")

        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("statHint")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.hint_label)

    def set_value(self, text):
        self.value_label.setText(text)

    def set_hint(self, text):
        self.hint_label.setText(text)

    def set_state(self, state):
        set_state(self, state)

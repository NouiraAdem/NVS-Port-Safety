"""Video display with zone overlay, HUD and alarm pulse."""

import math
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from config.app_config import DEFAULT_ZONE, FRAME_H, FRAME_W


class VideoWidget(QWidget):
    zone_edited = Signal(int, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 380)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._image = None
        self._frame_size = (FRAME_W, FRAME_H)
        self._zone = DEFAULT_ZONE
        self._show_zone = False
        self._alarm = False
        self._edit_mode = False
        self._drag_start = None
        self._drag_cur = None
        self._phase = 0.0
        self._live = False

        self._pulse = QTimer(self)
        self._pulse.setInterval(50)
        self._pulse.timeout.connect(self._tick)

    # ---- public API ------------------------------------------

    def has_image(self):
        return self._image is not None

    def set_image(self, image, live=False):
        self._image = image
        self._live = live
        if image is not None and not image.isNull():
            self._frame_size = (image.width(), image.height())
        self.update()

    def clear(self):
        self._image = None
        self._live = False
        self._alarm = False
        self._pulse.stop()
        self.update()

    def set_zone(self, x1, y1, x2, y2):
        self._zone = (x1, y1, x2, y2)
        self.update()

    def set_show_zone(self, value):
        self._show_zone = value
        self.update()

    def set_alarm(self, value):
        if value == self._alarm:
            return
        self._alarm = value
        if value:
            self._pulse.start()
        else:
            self._pulse.stop()
        self.update()

    def set_edit_mode(self, value):
        self._edit_mode = value
        self._drag_start = None
        self._drag_cur = None
        self.setCursor(
            Qt.CursorShape.CrossCursor if value else Qt.CursorShape.ArrowCursor
        )
        self.update()

    # ---- geometry --------------------------------------------

    def _tick(self):
        self._phase += 0.35
        self.update()

    def _target_rect(self):
        fw, fh = self._frame_size
        scale = min(self.width() / fw, self.height() / fh)
        tw, th = fw * scale, fh * scale
        return QRectF(
            (self.width() - tw) / 2, (self.height() - th) / 2, tw, th
        )

    def _to_frame(self, point):
        target = self._target_rect()
        fw, fh = self._frame_size
        scale = target.width() / fw
        x = (point.x() - target.x()) / scale
        y = (point.y() - target.y()) / scale
        return (
            max(0, min(fw, int(x))),
            max(0, min(fh, int(y))),
        )

    # ---- mouse (zone editing) --------------------------------

    def mousePressEvent(self, event):
        if self._edit_mode and self._image is not None:
            self._drag_start = event.position()
            self._drag_cur = event.position()
            self.update()

    def mouseMoveEvent(self, event):
        if self._edit_mode and self._drag_start is not None:
            self._drag_cur = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if not (self._edit_mode and self._drag_start is not None):
            return

        ax, ay = self._to_frame(self._drag_start)
        bx, by = self._to_frame(event.position())
        self._drag_start = None
        self._drag_cur = None

        x1, x2 = sorted((ax, bx))
        y1, y2 = sorted((ay, by))

        if (x2 - x1) >= 40 and (y2 - y1) >= 40:
            self.zone_edited.emit(x1, y1, x2, y2)

        self.update()

    # ---- painting --------------------------------------------

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = QRectF(self.rect())

        clip = QPainterPath()
        clip.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        p.setClipPath(clip)
        p.fillRect(rect, QColor("#050a13"))

        if self._image is None or self._image.isNull():
            self._paint_placeholder(p, rect)
        else:
            target = self._target_rect()
            p.drawImage(target, self._image)

            if self._show_zone:
                self._paint_zone(p, target)

            self._paint_hud(p, rect)

        if self._alarm:
            self._paint_alarm(p, rect)

        if self._edit_mode:
            self._paint_edit(p, rect)

        p.setClipping(False)
        p.setPen(QPen(QColor("#22314d"), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        p.end()

    def _font(self, size, bold=True):
        font = QFont(self.font())
        font.setPointSizeF(size)
        font.setBold(bold)
        return font

    def _chip(self, p, x, y, text, bg, fg, dot=None, right=False):
        p.setFont(self._font(8.5))
        fm = p.fontMetrics()
        width = fm.horizontalAdvance(text) + 22 + (14 if dot else 0)
        height = 24
        if right:
            x = x - width

        chip = QRectF(x, y, width, height)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(chip, 8, 8)

        text_x = chip.x() + 11
        if dot:
            p.setBrush(dot)
            p.drawEllipse(QPointF(chip.x() + 15, chip.center().y()), 3.5, 3.5)
            text_x += 14

        p.setPen(fg)
        p.drawText(
            QRectF(text_x, chip.y(), width, height),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            text,
        )

    def _paint_placeholder(self, p, rect):
        cx, cy = rect.center().x(), rect.center().y() - 26

        p.setPen(QPen(QColor("#2b3c58"), 2.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(cx - 30, cy - 20, 60, 40), 9, 9)
        p.drawEllipse(QPointF(cx, cy), 11, 11)
        p.drawLine(QPointF(cx - 12, cy - 20), QPointF(cx - 6, cy - 27))
        p.drawLine(QPointF(cx - 6, cy - 27), QPointF(cx + 6, cy - 27))
        p.drawLine(QPointF(cx + 6, cy - 27), QPointF(cx + 12, cy - 20))

        p.setPen(QColor("#6f82a0"))
        p.setFont(self._font(13))
        p.drawText(
            QRectF(rect.x(), cy + 38, rect.width(), 26),
            Qt.AlignmentFlag.AlignHCenter,
            "CAMERA OFFLINE",
        )
        p.setPen(QColor("#4a5b77"))
        p.setFont(self._font(10, bold=False))
        p.drawText(
            QRectF(rect.x(), cy + 66, rect.width(), 24),
            Qt.AlignmentFlag.AlignHCenter,
            "Press  Start Camera  to begin monitoring",
        )

    def _paint_zone(self, p, target):
        fw, _ = self._frame_size
        scale = target.width() / fw
        x1, y1, x2, y2 = self._zone

        zr = QRectF(
            target.x() + x1 * scale,
            target.y() + y1 * scale,
            (x2 - x1) * scale,
            (y2 - y1) * scale,
        )

        base = QColor("#f87171") if self._alarm else QColor("#34d399")

        fill = QColor(base)
        fill.setAlpha(55 if self._alarm else 32)
        p.setBrush(fill)

        pen = QPen(base, 2.4 if self._alarm else 2)
        if not self._alarm:
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawRoundedRect(zr, 6, 6)

        text = "INTRUSION" if self._alarm else "SAFETY ZONE"
        p.setFont(self._font(8.5))
        fm = p.fontMetrics()
        width = fm.horizontalAdvance(text) + 20
        lx, ly = zr.x(), zr.y() - 28
        if ly < target.y() + 4:
            ly = zr.y() + 6

        pill = QRectF(lx, ly, width, 22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(base)
        p.drawRoundedRect(pill, 7, 7)
        p.setPen(QColor("#04120d"))
        p.drawText(pill, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_hud(self, p, rect):
        if self._live:
            self._chip(
                p, 12, 12, "LIVE", QColor(5, 10, 19, 190),
                QColor("#e6edf7"), dot=QColor("#f87171"),
            )
        self._chip(
            p, rect.right() - 12, 12,
            datetime.now().strftime("%H:%M:%S"),
            QColor(5, 10, 19, 190), QColor("#cfe0f5"), right=True,
        )

    def _paint_alarm(self, p, rect):
        pulse = 0.5 + 0.5 * math.sin(self._phase)
        color = QColor("#f87171")
        color.setAlpha(int(90 + 150 * pulse))

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(color, 5))
        p.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 11, 11)

        p.setFont(self._font(9.5))
        text = "INTRUSION DETECTED"
        width = p.fontMetrics().horizontalAdvance(text) + 34
        banner = QRectF(rect.center().x() - width / 2, 12, width, 28)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(127, 29, 29, 235))
        p.drawRoundedRect(banner, 9, 9)
        p.setPen(QColor("#ffe4e6"))
        p.drawText(banner, Qt.AlignmentFlag.AlignCenter, text)

    def _paint_edit(self, p, rect):
        accent = QColor("#22d3ee")

        if self._drag_start is not None and self._drag_cur is not None:
            sel = QRectF(self._drag_start, self._drag_cur).normalized()
            fill = QColor(accent)
            fill.setAlpha(40)
            p.setBrush(fill)
            p.setPen(QPen(accent, 2, Qt.PenStyle.DashLine))
            p.drawRect(sel)

        text = "ZONE EDIT MODE  -  drag on the video to draw a new zone"
        p.setFont(self._font(9))
        width = p.fontMetrics().horizontalAdvance(text) + 30
        banner = QRectF(
            rect.center().x() - width / 2, rect.bottom() - 40, width, 28
        )
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(8, 51, 68, 235))
        p.drawRoundedRect(banner, 9, 9)
        p.setPen(QColor("#a5f3fc"))
        p.drawText(banner, Qt.AlignmentFlag.AlignCenter, text)

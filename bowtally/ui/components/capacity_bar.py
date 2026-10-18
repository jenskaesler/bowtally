# -*- coding: utf-8 -*-
"""Registration load: bar + text ("N von M Plätzen belegt | X noch frei").

Color: < 75 % secondary, 75-89 % orange, >= 90 % accent.
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from bowtally.ui import theme

BAR_HEIGHT = 8


def capacity_color(percentage: float) -> str:
    t = theme.current()
    if percentage >= 90:
        return t["accent"]
    if percentage >= 75:
        return t["warning"]
    return t["secondary"]


def capacity_text(cap) -> str:
    if cap.max is None:
        return f"{cap.active_count} Anmeldungen (keine Begrenzung)"
    return (f"{cap.active_count} von {cap.max} Plätzen belegt | "
            f"<b>{cap.free_slots} noch frei</b>")


class ProgressBar(QWidget):
    """Flat rounded bar; color chosen by the caller."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(BAR_HEIGHT)
        self._value, self._color = 0.0, None
        theme.notifier.changed.connect(self.update)

    def set_value(self, percentage: float, color: str | None = None) -> None:
        self._value = max(0.0, min(percentage, 100.0))
        self._color = color
        self.update()

    def paintEvent(self, _event):
        t = theme.current()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        r = QRectF(self.rect())
        p.setBrush(QColor(t["grid"]))
        p.drawRoundedRect(r, BAR_HEIGHT / 2, BAR_HEIGHT / 2)
        if self._value > 0:
            p.setBrush(QColor(self._color or t["secondary"]))
            p.drawRoundedRect(QRectF(r.x(), r.y(), r.width() * self._value / 100, r.height()),
                              BAR_HEIGHT / 2, BAR_HEIGHT / 2)


class CapacityBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bar = ProgressBar()
        self.label = QLabel(objectName="pageSubtitle")
        self.label.setTextFormat(Qt.TextFormat.RichText)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.bar)
        lay.addWidget(self.label)
        self._cap = None
        theme.notifier.changed.connect(lambda: self._cap and self.set_capacity(self._cap))

    def set_capacity(self, cap) -> None:
        self._cap = cap
        if cap.max is None:
            self.bar.set_value(0)
        else:
            self.bar.set_value(cap.percentage, capacity_color(cap.percentage))
        self.label.setText(capacity_text(cap))

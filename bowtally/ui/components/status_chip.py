# -*- coding: utf-8 -*-
"""Rounded status pill, as a widget (StatusChip) and as a table cell painter (ChipDelegate).

Kinds: 'neutral' (outline), 'primary' (brand), 'success' (green), 'muted' (grey filled).
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy, QStyle, QStyledItemDelegate

from bowtally.services.tournament_service import STATUS_LABELS
from bowtally.ui import repolish, theme

CHIP_ROLE = Qt.ItemDataRole.UserRole + 10      # item data: (text, kind)
TOURNAMENT_KINDS = {"draft": "neutral", "active": "primary", "closed": "muted"}


def tournament_chip(status: str) -> tuple[str, str]:
    return STATUS_LABELS.get(status, status), TOURNAMENT_KINDS.get(status, "neutral")


def _colors(kind: str) -> tuple[str, str, str]:
    """(background, foreground, border); background '' = transparent."""
    t = theme.current()
    return {
        "primary": (t["primary_soft"], t["primary"], t["primary"]),
        "success": (t["success_soft"], t["success"], t["success"]),
        "muted": (t["pressed"], t["text"], t["pressed"]),
    }.get(kind, ("", t["text2"], t["border"]))


class StatusChip(QLabel):
    def __init__(self, text: str = "", kind: str = "neutral", parent=None):
        super().__init__(parent)
        self.setObjectName("statusChip")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_chip(text, kind)

    def set_chip(self, text: str, kind: str = "neutral") -> None:
        self.setText(f"●  {text}")
        self.setProperty("kind", kind)
        repolish(self)

    def set_tournament_status(self, status: str) -> None:
        self.set_chip(*tournament_chip(status))


class ChipDelegate(QStyledItemDelegate):
    """Paints CHIP_ROLE data of a cell as a pill (keeps sorting/filtering on the item text)."""

    def paint(self, painter: QPainter, option, index):
        chip = index.data(CHIP_ROLE)
        if not chip:
            return super().paint(painter, option, index)
        # background / selection as usual, but without the text
        opt = option.__class__(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter, opt.widget)
        text, kind = chip
        bg, fg, border = _colors(kind)
        font = option.font
        font.setPointSizeF(font.pointSizeF() * 0.9)
        font.setBold(True)
        label = f"●  {text}"
        width = QFontMetrics(font).horizontalAdvance(label) + 24
        rect = QRectF(option.rect.x() + 8, option.rect.center().y() - 11, width, 22)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(border), 1))
        painter.setBrush(QColor(bg) if bg else Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 11, 11)
        painter.setFont(font)
        painter.setPen(QColor(fg))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

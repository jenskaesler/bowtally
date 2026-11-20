# -*- coding: utf-8 -*-
"""Non-blocking notifications, bottom right (or top right) of the window, stacked vertically."""
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from bowtally.ui import theme

MARGIN = 20
WIDTH = 320
SPACING = 8
FADE_IN_MS, VISIBLE_MS, FADE_OUT_MS = 200, 3500, 300


class Toast(QFrame):
    SUCCESS, INFO, WARNING, ERROR = "success", "info", "warning", "error"
    _ICONS = {SUCCESS: ("check-circle", "success"), INFO: ("info", "primary"),
              WARNING: ("alert", "warning"), ERROR: ("x-circle", "accent")}
    # (id(window), top) -> visible toasts, oldest first
    _stacks: dict[tuple[int, bool], list["Toast"]] = {}

    @classmethod
    def show(cls, parent: QWidget | None, text: str, kind: str = INFO,
             action: tuple[str, object] | None = None, top: bool = False) -> "Toast | None":
        """Toast.show(parent, "Text", Toast.SUCCESS, action=("Öffnen", callback)).
        top=True shows it top right (e.g. in dialogs whose buttons sit bottom right)."""
        window = parent.window() if parent is not None else None
        if window is None:
            return None
        toast = cls(window, text, kind, action)
        toast._top = top
        cls._stacks.setdefault((id(window), top), []).append(toast)
        cls._restack(window, top)
        QFrame.show(toast)
        toast.raise_()
        toast._fade(0.0, 1.0, FADE_IN_MS)
        QTimer.singleShot(FADE_IN_MS + VISIBLE_MS, toast.dismiss)
        return toast

    def __init__(self, window: QWidget, text: str, kind: str, action):
        super().__init__(window)
        self._window = window
        self._top = False
        self._closing = False
        self.setObjectName("toast")
        self.setProperty("kind", kind)
        self.setFixedWidth(WIDTH)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_name, color_key = self._ICONS.get(kind, self._ICONS[self.INFO])
        icon = QLabel()
        icon.setPixmap(theme.pixmap(icon_name, theme.current()[color_key], 20))
        icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        label = QLabel(text)
        label.setWordWrap(True)
        col = QVBoxLayout()
        col.setSpacing(4)
        col.addWidget(label)
        if action is not None:
            text_, callback = action
            btn = QPushButton(text_)
            btn.setObjectName("toastAction")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda: (callback(), self.dismiss()))
            row = QHBoxLayout()
            row.addWidget(btn)
            row.addStretch()
            col.addLayout(row)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(10)
        lay.addWidget(icon)
        lay.addLayout(col, 1)
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self.adjustSize()

    def _fade(self, start: float, end: float, ms: int, done=None):
        self._anim = QPropertyAnimation(self._effect, b"opacity", self)
        self._anim.setDuration(ms)
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if done is not None:
            self._anim.finished.connect(done)
        self._anim.start()

    def mousePressEvent(self, event):
        self.dismiss()

    def dismiss(self):
        if self._closing:
            return
        self._closing = True
        self._fade(self._effect.opacity(), 0.0, FADE_OUT_MS, self._remove)

    def _remove(self):
        stack = self._stacks.get((id(self._window), self._top), [])
        if self in stack:
            stack.remove(self)
        self.deleteLater()
        self._restack(self._window, self._top)

    @classmethod
    def _restack(cls, window: QWidget, top: bool = False):
        """Bottom: newest toast at the bottom, older ones move up.
        Top: newest toast at the top, older ones move down."""
        x = window.width() - WIDTH - MARGIN
        if top:
            y = MARGIN
            for toast in reversed(cls._stacks.get((id(window), True), [])):
                toast.adjustSize()
                toast.move(x, y)
                y += toast.height() + SPACING
            return
        y = window.height() - MARGIN
        for toast in reversed(cls._stacks.get((id(window), False), [])):
            toast.adjustSize()
            y -= toast.height()
            toast.move(x, y)
            y -= SPACING

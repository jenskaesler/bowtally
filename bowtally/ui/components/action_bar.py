# -*- coding: utf-8 -*-
"""Contextual actions for the current table selection, slides up below the table."""
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

from bowtally.ui import button

HEIGHT = 54
ANIM_MS = 150


@dataclass
class Action:
    text: str
    callback: Callable
    kind: str | None = None          # None | 'primary' | 'danger'
    enabled: bool = True
    tooltip: str = ""


class ActionBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("actionBar")
        self.setMaximumHeight(0)
        self.label = QLabel()
        self._lay = QHBoxLayout(self)
        self._lay.setContentsMargins(14, 8, 10, 8)
        self._lay.addWidget(self.label)
        self._lay.addStretch()
        self._buttons = []
        self._anim = QPropertyAnimation(self, b"maximumHeight", self)
        self._anim.setDuration(ANIM_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._shown = False

    def set_actions(self, info: str, actions: list[Action]) -> None:
        """Replace content; an empty action list hides the bar."""
        for b in self._buttons:
            self._lay.removeWidget(b)
            b.deleteLater()
        self._buttons = []
        self.label.setText(info)
        for a in actions:
            b = button(a.text, a.callback, a.kind, a.tooltip)
            b.setEnabled(a.enabled)
            self._lay.addWidget(b)
            self._buttons.append(b)
        self._reveal(bool(actions))

    def _reveal(self, show: bool) -> None:
        if show == self._shown:
            return
        self._shown = show
        self._anim.stop()
        self._anim.setStartValue(self.maximumHeight())
        self._anim.setEndValue(HEIGHT if show else 0)
        self._anim.start()

# -*- coding: utf-8 -*-
"""Placeholder shown instead of an empty table: icon, text and a call to action."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from bowtally.ui import button, theme

ICON_SIZE = 64


class EmptyState(QWidget):
    actionTriggered = Signal()

    def __init__(self, icon: str, title: str, text: str, cta_text: str | None = None,
                 parent=None):
        super().__init__(parent)
        self._icon_name, self._title, self._text = icon, title, text
        self.icon = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.title = QLabel(objectName="emptyTitle", alignment=Qt.AlignmentFlag.AlignCenter)
        self.text = QLabel(objectName="emptyText", alignment=Qt.AlignmentFlag.AlignCenter)
        self.text.setWordWrap(True)
        self.cta = button(cta_text or "", self.actionTriggered.emit, "primary")
        self.cta.setVisible(bool(cta_text))
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.cta)
        row.addStretch()
        lay = QVBoxLayout(self)
        lay.addStretch(2)
        lay.addWidget(self.icon)
        lay.addSpacing(8)
        lay.addWidget(self.title)
        lay.addWidget(self.text)
        lay.addSpacing(12)
        lay.addLayout(row)
        lay.addStretch(3)
        self._has_cta = bool(cta_text)
        theme.notifier.changed.connect(self._update_icon)
        self.show_empty()

    def _update_icon(self):
        self.icon.setPixmap(theme.pixmap(self._icon_name, theme.current()["text2"], ICON_SIZE))

    def show_empty(self):
        self._update_icon()
        self.title.setText(self._title)
        self.text.setText(self._text)
        self.cta.setVisible(self._has_cta)

    def show_no_results(self, term: str):
        self.icon.setPixmap(theme.pixmap("search", theme.current()["text2"], ICON_SIZE))
        self.title.setText(f"Keine Ergebnisse für '{term}'")
        self.text.setText("Suchbegriff ändern oder mit Esc die Suche leeren.")
        self.cta.setVisible(False)

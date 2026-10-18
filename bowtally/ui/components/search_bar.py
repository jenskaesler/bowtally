# -*- coding: utf-8 -*-
"""Search field with search icon, clear button, Escape-to-clear and debounce."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLineEdit

from bowtally.ui import theme

DEBOUNCE_MS = 250


class SearchBar(QLineEdit):
    searchChanged = Signal(str)     # emitted DEBOUNCE_MS after the last keystroke

    def __init__(self, placeholder: str = "Suchen …", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setToolTip(f"{placeholder} (Strg+F, Esc leert die Suche)")
        self.setClearButtonEnabled(True)
        self.setMinimumWidth(260)
        self._icon = self.addAction(QIcon(), QLineEdit.ActionPosition.LeadingPosition)
        self._timer = QTimer(self, singleShot=True, interval=DEBOUNCE_MS)
        self._timer.timeout.connect(lambda: self.searchChanged.emit(self.term()))
        self.textChanged.connect(lambda _t: self._timer.start())
        theme.notifier.changed.connect(self._update_icon)
        self._update_icon()

    def _update_icon(self):
        self._icon.setIcon(QIcon(theme.pixmap("search", theme.current()["text2"], 16)))

    def term(self) -> str:
        return self.text().strip()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.text():
            self.clear()
            return
        super().keyPressEvent(event)

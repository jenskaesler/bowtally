# -*- coding: utf-8 -*-
"""Context header of every view: page name, context subtitle, actions on the right."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class PageHeader(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.title = QLabel(title, objectName="pageTitle")
        self.subtitle = QLabel(subtitle, objectName="pageSubtitle")
        self.title_row = QHBoxLayout()
        self.title_row.setSpacing(12)
        self.title_row.addWidget(self.title)
        self.title_row.addStretch()
        col = QVBoxLayout()
        col.setSpacing(0)
        col.addLayout(self.title_row)
        col.addWidget(self.subtitle)
        self.actions = QHBoxLayout()
        self.actions.setSpacing(8)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 8)
        lay.addLayout(col, 1)
        lay.addLayout(self.actions)

    def add(self, *widgets: QWidget) -> None:
        """Actions on the right (put the single primary action last)."""
        for w in widgets:
            self.actions.addWidget(w)

    def add_title_widget(self, widget: QWidget) -> None:
        """Element right next to the title, e.g. a status chip."""
        self.title_row.insertWidget(self.title_row.count() - 1, widget, 0,
                                    Qt.AlignmentFlag.AlignVCenter)

    def set_subtitle(self, text: str) -> None:
        self.subtitle.setText(text)

    def set_title(self, text: str) -> None:
        self.title.setText(text)

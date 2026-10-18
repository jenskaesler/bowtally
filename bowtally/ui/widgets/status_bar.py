# -*- coding: utf-8 -*-
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QStatusBar, QToolButton

from bowtally import config
from bowtally.__version__ import __version__
from bowtally.ui import theme


class StatusBar(QStatusBar):
    helpRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeGripEnabled(False)
        self.addWidget(QLabel(f"Datenbank: {config.DB_PATH}"))
        self.info = QLabel()
        self.addPermanentWidget(self.info)
        self.addPermanentWidget(QLabel(f"BowTally v{__version__}"))
        self.help = QToolButton(objectName="iconButton")
        self.help.setToolTip("Tastenkürzel anzeigen (F1)")
        self.help.clicked.connect(self.helpRequested)
        self.addPermanentWidget(self.help)
        theme.notifier.changed.connect(self._update_icon)
        self._update_icon()

    def _update_icon(self):
        self.help.setIcon(QIcon(theme.pixmap("help", theme.current()["text2"], 16)))

    def set_info(self, text: str) -> None:
        self.info.setText(text)

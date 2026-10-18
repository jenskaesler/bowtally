# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QLabel, QStatusBar

from bowtally import config
from bowtally.__version__ import __version__


class StatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.addWidget(QLabel(f"Datenbank: {config.DB_PATH}"))
        self.addPermanentWidget(QLabel(f"BowTally v{__version__}"))

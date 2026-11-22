# -*- coding: utf-8 -*-
from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QStatusBar, QToolButton

from bowtally import config
from bowtally.__version__ import __version__
from bowtally.database import engine
from bowtally.ui import theme


class StatusBar(QStatusBar):
    helpRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeGripEnabled(False)
        db_label = QLabel(f"Datenbank: {config.DB_PATH}  ·  Schema {engine.schema_number()}")
        db_label.setToolTip("Datenbankschema (Alembic-Revision): "
                            f"{engine.schema_version() or 'unbekannt'}")
        self.addWidget(db_label)
        self.info = QLabel()
        self.addPermanentWidget(self.info)
        self.addPermanentWidget(QLabel(f"BowTally v{__version__}"))
        self.help = QToolButton(objectName="iconButton")
        self.help.setToolTip("App-Hilfe öffnen (F1)")
        self.help.clicked.connect(self.helpRequested)
        self.addPermanentWidget(self.help)
        theme.notifier.changed.connect(self._update_icon)
        self._update_icon()

    def _update_icon(self):
        self.help.setIcon(QIcon(theme.pixmap("help", theme.current()["text2"], 16)))

    def set_info(self, text: str) -> None:
        self.info.setText(text)

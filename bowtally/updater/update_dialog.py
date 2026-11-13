# -*- coding: utf-8 -*-
"""Modal dialog offering the update, skip or postpone."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
                               QVBoxLayout)

from bowtally import __version__
from bowtally.ui import button, restore_geom, save_geom, theme

CHANGELOG_URL = "https://github.com/jenskaesler/bowtally/releases/tag/v{version}"
MAX_LINES = 20


class UpdateDialog(QDialog):
    def __init__(self, info, service, parent=None):
        super().__init__(parent)
        self.info = info
        self.service = service
        self.setWindowTitle("Update verfügbar")
        self.setModal(True)
        self.setMinimumWidth(520)
        restore_geom(self, "update")
        self.finished.connect(lambda: save_geom(self, "update"))

        t = theme.current()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        title = QLabel(f"Version {info.version} verfügbar (aktuell: {__version__})")
        title.setProperty("pageTitle", True)
        lay.addWidget(title)

        body = QPlainTextEdit(_clip(info.body))
        body.setReadOnly(True)
        body.setMinimumHeight(200)
        lay.addWidget(body, 1)

        link = QLabel('<a href="{url}">Vollständiges Changelog anzeigen</a>'.format(
            url=CHANGELOG_URL.format(version=info.version)))
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        lay.addWidget(link)

        row = QHBoxLayout()
        row.addStretch()
        later = button("Später erinnern", self.reject)
        skip = button("Diese Version überspringen", self._skip)
        now = button("Jetzt aktualisieren", self._update, "primary")
        row.addWidget(later)
        row.addWidget(skip)
        row.addWidget(now)
        lay.addLayout(row)

    def _skip(self):
        self.service.set_skipped_version(self.info.version)
        self.accept()

    def _update(self):
        from bowtally.updater.download_dialog import DownloadDialog
        DownloadDialog(self.info, self).exec()


def _clip(text: str) -> str:
    lines = (text or "").splitlines()
    return "\n".join(lines[:MAX_LINES])
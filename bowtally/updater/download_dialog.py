# -*- coding: utf-8 -*-
"""Modal dialog that downloads the installer, verifies it and starts the silent install."""
import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar,
                               QVBoxLayout)

from bowtally.ui import button
from bowtally.updater.update_service import download_asset, sha256_of

CANCEL_FLAG = "--cleanup-after"


class _Worker(QObject):
    progress = Signal(int, int)
    finished = Signal(bool)

    def __init__(self, url: str, dest: Path):
        super().__init__()
        self.url = url
        self.dest = dest
        self._cancel = None

    def cancel(self):
        if self._cancel is not None:
            self._cancel.set()

    def run(self):
        import threading
        self._cancel = threading.Event()
        ok = download_asset(self.url, self.dest, self._cancel, self._on_progress)
        self.finished.emit(ok)

    def _on_progress(self, done: int, total: int):
        self.progress.emit(done, total)


class DownloadDialog(QDialog):
    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.info = info
        self.dest = Path(tempfile.gettempdir()) / f"BowTally-setup-{info.version}.exe"
        self._thread = None
        self._worker = None

        self.setWindowTitle("Update wird geladen")
        self.setModal(True)
        self.setMinimumWidth(460)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        self.label = QLabel(f"Version {info.version} wird heruntergeladen …")
        lay.addWidget(self.label)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        lay.addWidget(self.bar)

        row = QHBoxLayout()
        row.addStretch()
        self.cancel_btn = button("Abbrechen", self._cancel)
        row.addWidget(self.cancel_btn)
        lay.addLayout(row)

        self._start()

    def _start(self):
        self._thread = QThread(self)
        self._worker = _Worker(self.info.asset_url, self.dest)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._thread.start()

    def _on_progress(self, done: int, total: int):
        if total > 0:
            self.bar.setRange(0, total)
            self.bar.setValue(done)
        else:
            self.bar.setRange(0, 0)

    def _cancel(self):
        if self._worker is not None:
            self._worker.cancel()
        self.label.setText("Download wird abgebrochen …")

    def _on_finished(self, ok: bool):
        if self._thread is not None:
            self._thread.quit()
        if not ok:
            self._fail("Download fehlgeschlagen oder abgebrochen.")
            return
        self._verify()

    def _verify(self):
        if self.info.checksum_available:
            actual = sha256_of(self.dest)
            if actual != (self.info.checksum or ""):
                self._fail("Prüfsumme stimmt nicht überein – die Datei wurde manipuliert "
                           "oder ist beschädigt.")
                return
            self._install()
            return
        res = QMessageBox.warning(
            self, "Keine Prüfsumme",
            "Integritätsprüfung nicht möglich — keine Prüfsumme im Release hinterlegt.\n"
            "Trotzdem installieren?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if res != QMessageBox.StandardButton.Yes:
            self._fail("Installation abgebrochen.")
            return
        self._install()

    def _install(self):
        try:
            subprocess.Popen([str(self.dest), "/S", f"{CANCEL_FLAG}={self.dest}"])
        except OSError as exc:
            self._fail(f"Installer konnte nicht gestartet werden: {exc}")
            return
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def _fail(self, message: str):
        QMessageBox.critical(self, "Update fehlgeschlagen", message)
        try:
            self.dest.unlink(missing_ok=True)
        except OSError:
            pass
        self.reject()

    def reject(self):
        if self._worker is not None:
            self._worker.cancel()
        super().reject()
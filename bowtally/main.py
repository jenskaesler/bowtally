# -*- coding: utf-8 -*-
"""Application entry point."""
import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressBar, QSplashScreen

from bowtally import config
from bowtally.__version__ import __version__

log = logging.getLogger("bowtally")


def setup_logging() -> None:
    config.APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(config.LOG_PATH, maxBytes=config.LOG_MAX_BYTES,
                                  backupCount=config.LOG_BACKUP_COUNT, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    logging.getLogger("alembic").setLevel(logging.WARNING)


def _excepthook(exc_type, exc, tb):
    """Last line of defence: every unhandled exception is logged and shown."""
    from bowtally.ui import show_error
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    exc.__traceback__ = tb
    show_error(QApplication.activeWindow(), exc)


class _Splash(QSplashScreen):
    def __init__(self):
        pix = self._build_pixmap()
        super().__init__(pix)
        self._bar = QProgressBar(self)
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(5)
        self._bar.setGeometry(0, pix.height() - 5, pix.width(), 5)
        self._bar.setStyleSheet("QProgressBar{border:none;background:#dde3ea;border-radius:0;}"
                                "QProgressBar::chunk{background:#2d6a4f;border-radius:0;}")

    @staticmethod
    def _build_pixmap() -> QPixmap:
        dark = (QApplication.instance().styleHints().colorScheme() == Qt.ColorScheme.Dark)
        W, H = 480, 280
        pix = QPixmap(W, H)
        pix.fill(QColor("#1e2430" if dark else "#f8f9fb"))
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("#3d4a5c" if dark else "#d0d7de"))
        p.drawRect(0, 0, W - 1, H - 1)
        if config.ICON_PATH.is_file():
            icon_pix = QPixmap(str(config.ICON_PATH)).scaled(
                72, 72, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            if not icon_pix.isNull():
                p.drawPixmap((W - icon_pix.width()) // 2, 52, icon_pix)
        f_title = QFont("Segoe UI", 22, QFont.Weight.Bold)
        p.setFont(f_title)
        p.setPen(QColor("#e8ecf4" if dark else "#1a202c"))
        p.drawText(0, 136, W, 36, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                   "BowTally")
        f_sub = QFont("Segoe UI", 10)
        p.setFont(f_sub)
        p.setPen(QColor("#8899aa" if dark else "#6b7280"))
        p.drawText(0, 174, W, 24, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                   f"Version {__version__}")
        p.end()
        return pix

    def progress(self, value: int, message: str = ""):
        self._bar.setValue(value)
        if message:
            self.showMessage(message, Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                             QColor("#6b7280"))
        QApplication.processEvents()


def main() -> int:
    setup_logging()
    log.info("BowTally %s startet", __version__)
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(__version__)
    if config.ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(config.ICON_PATH)))
    sys.excepthook = _excepthook

    splash = _Splash()
    splash.show()
    splash.progress(10, "Datenbank wird initialisiert …")

    try:
        from bowtally.database.engine import init_database
        init_database()
    except Exception as exc:
        splash.close()
        log.error("Datenbank konnte nicht initialisiert werden", exc_info=exc)
        QMessageBox.critical(None, "BowTally",
                             f"Die Datenbank konnte nicht geöffnet werden:\n{exc}\n\n"
                             f"Pfad: {config.DB_PATH}\nLog: {config.LOG_PATH}")
        return 1

    splash.progress(60, "Benutzeroberfläche wird geladen …")
    from bowtally.services import settings_service as ss
    from bowtally.ui import theme
    from bowtally.ui.main_window import MainWindow
    theme.apply(app)
    window = MainWindow()
    splash.progress(100, "Bereit")
    window.show()
    splash.finish(window)
    if not (ss.get_club_profile().get("club_name") or "").strip():
        from bowtally.ui.dialogs.first_run_wizard import FirstRunWizard
        FirstRunWizard(window).exec()
        window._refresh_title()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

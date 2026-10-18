# -*- coding: utf-8 -*-
"""Application entry point."""
import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

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


def main() -> int:
    setup_logging()
    log.info("BowTally %s startet", __version__)
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(__version__)
    if config.ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(config.ICON_PATH)))
    sys.excepthook = _excepthook

    try:
        from bowtally.database.engine import init_database
        init_database()
    except Exception as exc:
        log.error("Datenbank konnte nicht initialisiert werden", exc_info=exc)
        QMessageBox.critical(None, "BowTally",
                             f"Die Datenbank konnte nicht geöffnet werden:\n{exc}\n\n"
                             f"Pfad: {config.DB_PATH}\nLog: {config.LOG_PATH}")
        return 1

    from bowtally.ui import theme
    from bowtally.ui.main_window import MainWindow
    theme.apply(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

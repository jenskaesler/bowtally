# -*- coding: utf-8 -*-
"""Small UI helpers shared by all views and dialogs."""
import logging

from PySide6.QtWidgets import QMessageBox, QPushButton, QWidget

from bowtally.services import ValidationError

log = logging.getLogger("bowtally.ui")


def show_error(parent: QWidget | None, exc: BaseException, context: str = "") -> None:
    """Log and display an exception. ValidationError is shown as a plain warning."""
    if isinstance(exc, ValidationError):
        log.warning("%s%s", f"{context}: " if context else "", exc)
        QMessageBox.warning(parent, "Hinweis", str(exc))
        return
    log.error("%s%s", f"{context}: " if context else "", exc, exc_info=exc)
    QMessageBox.critical(parent, "Fehler",
                         f"{context + chr(10) if context else ''}{type(exc).__name__}: {exc}")


def confirm(parent: QWidget | None, text: str, title: str = "Bestätigung") -> bool:
    return QMessageBox.question(parent, title, text) == QMessageBox.StandardButton.Yes


def button(text: str, slot=None, kind: str | None = None) -> QPushButton:
    """kind: None | 'primary' | 'danger' (styled via QSS dynamic properties)."""
    b = QPushButton(text)
    if kind:
        b.setProperty(kind, True)
    if slot is not None:
        b.clicked.connect(slot)
    return b

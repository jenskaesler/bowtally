# -*- coding: utf-8 -*-
"""Small UI helpers shared by all views and dialogs."""
import logging
from contextlib import contextmanager

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QWidget

from bowtally.services import ValidationError

log = logging.getLogger("bowtally.ui")


def show_error(parent: QWidget | None, exc: BaseException, context: str = "") -> None:
    """ValidationError -> warning toast. Anything else -> log + QMessageBox.critical."""
    if isinstance(exc, ValidationError):
        from bowtally.ui.components.toast import Toast
        log.warning("%s%s", f"{context}: " if context else "", exc)
        Toast.show(parent, str(exc), Toast.WARNING)
        return
    log.error("%s%s", f"{context}: " if context else "", exc, exc_info=exc)
    QMessageBox.critical(parent, "Fehler",
                         f"{context + chr(10) if context else ''}{type(exc).__name__}: {exc}")


def confirm(parent: QWidget | None, text: str, title: str = "Bestätigung",
            confirm_text: str = "Fortfahren", destructive: bool = False) -> bool:
    from bowtally.ui.components.confirm_dialog import ConfirmDialog
    return ConfirmDialog.ask(parent, title, text, confirm_text, destructive)


def button(text: str, slot=None, kind: str | None = None, tooltip: str = "") -> QPushButton:
    """kind: None (secondary) | 'primary' | 'danger' (styled via QSS dynamic properties)."""
    b = QPushButton(text)
    if kind:
        b.setProperty(kind, True)
    b.setToolTip(tooltip or text)
    if slot is not None:
        b.clicked.connect(slot)
    return b


def burger_button(tooltip: str, slot=None, menu=None) -> QPushButton:
    """Square icon-only button with the hamburger icon (same height as normal buttons)."""
    from bowtally.ui import theme
    b = QPushButton()
    b.setIcon(theme.icon("menu"))
    b.setIconSize(QSize(18, 18))
    b.setFixedSize(34, 34)
    # the global button padding (7px 16px) would squeeze the icon out of a 34px square
    b.setStyleSheet("QPushButton { padding: 0; } QPushButton::menu-indicator { image: none; }")
    b.setToolTip(tooltip)
    if menu is not None:
        b.setMenu(menu)
    if slot is not None:
        b.clicked.connect(slot)
    return b


@contextmanager
def busy():
    """Wait cursor for operations that may take noticeable time."""
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def save_geom(widget, key: str) -> None:
    QSettings("BowTally", "BowTally").setValue(f"dlg/{key}/geometry", widget.saveGeometry())


def restore_geom(widget, key: str) -> None:
    if geom := QSettings("BowTally", "BowTally").value(f"dlg/{key}/geometry"):
        widget.restoreGeometry(geom)


def repolish(widget: QWidget) -> None:
    """Re-evaluate the stylesheet after a dynamic property changed."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)

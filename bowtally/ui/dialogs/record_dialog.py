# -*- coding: utf-8 -*-
"""Base modal dialog for creating / editing a single record.

Subclass pattern:
    def __init__(self, record=None, parent=None):
        self._record = record           # set before super()
        super().__init__(title, ...)
        if record:
            self.form.set_values({...})
        self._baseline = self.form.snapshot()
        self.saved_id = None

    def _setup_form(self):              # add fields + optionally append to _body_layout
        self.form.add(...)

    def _do_save(self) -> bool:
        ...save...; self.saved_id = ...; return True
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QHBoxLayout, QLabel,
                               QPlainTextEdit, QScrollArea, QTextEdit, QVBoxLayout, QWidget)

from bowtally.ui import button
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.form_field import Form
from bowtally.ui.constants import SETTINGS_COMBO_W, SETTINGS_LABEL_W

_DISCARD_TITLE = "Änderungen verwerfen?"
_DISCARD_TEXT = "Es gibt ungespeicherte Änderungen. Trotzdem schließen?"


class RecordDialog(QDialog):
    def __init__(self, title: str, read_only: bool = False,
                 read_only_hint: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        screen_h = QApplication.primaryScreen().availableGeometry().height()
        self.setMaximumHeight(int(screen_h * 0.8))

        self._read_only = read_only
        self._baseline: tuple = ()

        self.form = Form(label_width=SETTINGS_LABEL_W, combo_width=SETTINGS_COMBO_W)

        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(10)
        self._body_layout.addWidget(self.form)

        self._setup_form()

        if read_only:
            self.form.set_read_only(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(body)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")

        self._save_btn = button("Speichern", self._on_save, "primary")
        self._save_btn.setEnabled(not read_only)
        cancel_btn = button("Abbrechen", self._on_cancel)

        footer = QHBoxLayout()
        footer.addWidget(cancel_btn)
        footer.addStretch()
        footer.addWidget(self._save_btn)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        if read_only_hint:
            hint_lbl = QLabel(read_only_hint, objectName="readOnlyHint")
            hint_lbl.setWordWrap(True)
            hint_lbl.setContentsMargins(8, 6, 8, 6)
            lay.addWidget(hint_lbl)
        lay.addWidget(scroll, 1)
        lay.addWidget(sep)
        lay.addLayout(footer)

    def showEvent(self, event):
        super().showEvent(event)
        p = self.parent()
        if p:
            pg = p.window().geometry()
            sg = self.geometry()
            self.move(pg.x() + (pg.width() - sg.width()) // 2,
                      pg.y() + (pg.height() - sg.height()) // 2)
        self.form.focus_first()

    def _setup_form(self) -> None:
        """Override to add fields to self.form and optional widgets to self._body_layout."""

    def _do_save(self) -> bool:
        """Override: save the record; return True on success, False to stay open."""
        return False

    def _is_dirty(self) -> bool:
        return not self._read_only and self.form.snapshot() != self._baseline

    def _on_save(self):
        if not self.form.validate():
            return
        if self._do_save():
            self.accept()

    def _on_cancel(self):
        if self._is_dirty() and not ConfirmDialog.ask(
                self, _DISCARD_TITLE, _DISCARD_TEXT, "Verwerfen", destructive=False):
            return
        self.reject()

    def closeEvent(self, event):
        if self._is_dirty() and not ConfirmDialog.ask(
                self, _DISCARD_TITLE, _DISCARD_TEXT, "Verwerfen", destructive=False):
            event.ignore()
            return
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not isinstance(QApplication.focusWidget(), (QTextEdit, QPlainTextEdit)):
                if not self._read_only:
                    self._on_save()
                return
        elif event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
            return
        super().keyPressEvent(event)

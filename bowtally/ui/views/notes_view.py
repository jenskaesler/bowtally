# -*- coding: utf-8 -*-
"""Notizen: freies Textfeld pro Turnier (nach Abschluss nur lesbar)."""
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from bowtally.services import tournament_service as ts
from bowtally.ui import button
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context


class NotesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.header = PageHeader("Notizen")
        self.btn_save = button("Notizen speichern", self.save, "primary", "Notizen speichern")
        self.header.add(self.btn_save)
        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("Freie Notizen zum Turnier …")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        lay.addWidget(self.edit, 1)

    def set_tournament(self, t):
        self.tournament = t
        locked = t.phase == "closed"
        self.edit.setPlainText(t.internal_notes or "")
        self.edit.setReadOnly(locked)
        self.btn_save.setEnabled(not locked)
        self.header.set_subtitle("Das Turnier ist abgeschlossen, Änderungen sind gesperrt."
                                 if locked else "Interne Notizen, erscheinen nicht in der Ausschreibung")

    def save(self):
        ts.update_tournament_fields(self.tournament.id, {"internal_notes": self.edit.toPlainText()})
        Toast.show(self, "Notizen gespeichert", Toast.SUCCESS)
        context.notify()

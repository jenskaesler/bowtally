# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QVBoxLayout)

from bowtally.services import master_data_service as md
from bowtally.ui import show_error


class BowClassDialog(QDialog):
    def __init__(self, bow_class=None, parent=None):
        super().__init__(parent)
        self.class_id = bow_class.id if bow_class else None
        read_only = bool(bow_class and bow_class.is_builtin)
        self.setWindowTitle("Bogenklasse" if bow_class else "Neue Bogenklasse")
        self.resize(420, 300)

        self.name = QLineEdit(bow_class.name if bow_class else "")
        self.abbreviation = QLineEdit(bow_class.abbreviation or "" if bow_class else "")
        self.age_group = QLineEdit(bow_class.age_group or "" if bow_class else "")
        self.description = QPlainTextEdit(bow_class.description or "" if bow_class else "")
        self.description.setFixedHeight(80)
        form = QFormLayout()
        form.addRow("Name *", self.name)
        form.addRow("Abkürzung", self.abbreviation)
        form.addRow("Altersgruppe", self.age_group)
        form.addRow("Beschreibung", self.description)

        lay = QVBoxLayout(self)
        if read_only:
            hint = QLabel("Eingebaute Bogenklasse – schreibgeschützt. Zum Anpassen klonen.")
            hint.setProperty("secondary", True)
            lay.addWidget(hint)
            for w in (self.name, self.abbreviation, self.age_group):
                w.setReadOnly(True)
            self.description.setReadOnly(True)
        lay.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close if read_only else
                                   QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        if not read_only:
            buttons.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
            buttons.button(QDialogButtonBox.StandardButton.Save).setProperty("primary", True)
            buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _save(self):
        try:
            md.save_bow_class({"name": self.name.text(),
                               "abbreviation": self.abbreviation.text(),
                               "age_group": self.age_group.text(),
                               "description": self.description.toPlainText()}, self.class_id)
        except Exception as exc:
            show_error(self, exc, "Bogenklasse konnte nicht gespeichert werden")
            return
        self.accept()

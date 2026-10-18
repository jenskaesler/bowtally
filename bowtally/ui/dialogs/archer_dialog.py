# -*- coding: utf-8 -*-
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
                               QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout)

from bowtally.services import master_data_service as md
from bowtally.ui import show_error


class ArcherDialog(QDialog):
    def __init__(self, archer=None, parent=None):
        super().__init__(parent)
        self.archer_id = archer.id if archer else None
        self.setWindowTitle("Schütze bearbeiten" if archer else "Neuer Schütze")
        self.resize(460, 480)

        self.first_name = QLineEdit(archer.first_name if archer else "")
        self.last_name = QLineEdit(archer.last_name if archer else "")
        self.has_birth = QCheckBox("angeben")
        self.birth = QDateEdit()
        self.birth.setCalendarPopup(True)
        self.birth.setDisplayFormat("dd.MM.yyyy")
        self.birth.setDate(QDate(2000, 1, 1))
        if archer and archer.birth_date:
            self.has_birth.setChecked(True)
            self.birth.setDate(QDate(archer.birth_date))
        self.birth.setEnabled(self.has_birth.isChecked())
        self.has_birth.toggled.connect(self.birth.setEnabled)
        self.club = QLineEdit(archer.club or "" if archer else "")
        self.member_number = QLineEdit(archer.member_number or "" if archer else "")
        self.email = QLineEdit(archer.email or "" if archer else "")
        self.phone = QLineEdit(archer.phone or "" if archer else "")
        self.bow_class = QComboBox()
        self.bow_class.addItem("(keine)", None)
        for bc in md.list_bow_classes():
            self.bow_class.addItem(bc.name, bc.id)
        if archer and archer.default_bow_class_id:
            self.bow_class.setCurrentIndex(self.bow_class.findData(archer.default_bow_class_id))
        self.notes = QPlainTextEdit(archer.notes or "" if archer else "")
        self.notes.setFixedHeight(70)
        self.active = QCheckBox("Aktiv")
        self.active.setChecked(archer.active if archer else True)

        form = QFormLayout()
        form.addRow("Vorname *", self.first_name)
        form.addRow("Nachname *", self.last_name)
        birth_row = QHBoxLayout()
        birth_row.addWidget(self.has_birth)
        birth_row.addWidget(self.birth, 1)
        form.addRow("Geburtsdatum", birth_row)
        form.addRow("Verein", self.club)
        form.addRow("Mitgliedsnummer", self.member_number)
        form.addRow("E-Mail", self.email)
        form.addRow("Telefon", self.phone)
        form.addRow("Standard-Bogenklasse", self.bow_class)
        form.addRow("Notizen", self.notes)
        form.addRow("", self.active)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty("primary", True)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

    def _save(self):
        data = {
            "first_name": self.first_name.text(), "last_name": self.last_name.text(),
            "birth_date": self.birth.date().toPython() if self.has_birth.isChecked() else None,
            "club": self.club.text(), "member_number": self.member_number.text(),
            "email": self.email.text(), "phone": self.phone.text(),
            "default_bow_class_id": self.bow_class.currentData(),
            "notes": self.notes.toPlainText(), "active": self.active.isChecked(),
        }
        try:
            md.save_archer(data, self.archer_id)
        except Exception as exc:
            show_error(self, exc, "Schütze konnte nicht gespeichert werden")
            return
        self.accept()

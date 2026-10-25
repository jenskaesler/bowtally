# -*- coding: utf-8 -*-
"""First-run setup wizard shown when club_name is not yet configured."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QVBoxLayout, QWidget)

from bowtally.services import settings_service as ss
from bowtally.ui import button


class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Willkommen bei BowTally")
        self.setMinimumWidth(520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        welcome = QLabel(
            "<h2>Willkommen bei BowTally!</h2>"
            "<p>Bitte gib ein paar grundlegende Informationen über deinen Verein ein.<br>"
            "Du kannst diese Angaben jederzeit unter <b>Einstellungen → Vereinsprofil</b> "
            "ändern.</p>",
            objectName="pageSubtitle")
        welcome.setWordWrap(True)
        welcome.setTextFormat(Qt.TextFormat.RichText)

        box = QGroupBox("Vereinsdaten")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.club_name = QLineEdit()
        self.club_name.setPlaceholderText("z. B. Bogensportclub Musterstadt e.V.")
        self.city = QLineEdit()
        self.city.setPlaceholderText("z. B. Musterstadt")
        self.federation = QLineEdit()
        self.federation.setPlaceholderText("z. B. DSB")
        form.addRow("Vereinsname *", self.club_name)
        form.addRow("Ort", self.city)
        form.addRow("Verband", self.federation)

        self._error_lbl = QLabel(objectName="dangerText")
        self._error_lbl.hide()

        skip_btn = button("Überspringen", self.reject,
                          tooltip="Einrichtung überspringen – später unter Einstellungen nachholen")
        save_btn = button("Speichern und starten", self._save, "primary")

        btn_row = QHBoxLayout()
        btn_row.addWidget(skip_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.addWidget(welcome)
        lay.addWidget(box)
        lay.addWidget(self._error_lbl)
        lay.addLayout(btn_row)

    def _save(self):
        name = self.club_name.text().strip()
        if not name:
            self._error_lbl.setText("Vereinsname ist erforderlich.")
            self._error_lbl.show()
            self.club_name.setFocus()
            return
        ss.save_club_profile({"club_name": name,
                              "city": self.city.text().strip(),
                              "federation": self.federation.text().strip()})
        self.accept()

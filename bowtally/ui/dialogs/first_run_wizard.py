# -*- coding: utf-8 -*-
"""First-run setup wizard shown when club_name is not yet configured."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QLineEdit, QStackedWidget, QTextBrowser,
                               QVBoxLayout, QWidget)

from bowtally import config
from bowtally.services import settings_service as ss
from bowtally.ui import button


class FirstRunWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Willkommen bei BowTally")
        self.setMinimumWidth(560)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_club())
        self._stack.addWidget(self._page_license())

        self._error_lbl = QLabel(objectName="dangerText")
        self._error_lbl.hide()

        self._next_btn = button("Weiter", self._next, "primary")
        self._cancel_btn = button("Abbrechen", self.reject)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(self._next_btn)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.addWidget(self._stack, 1)
        lay.addWidget(self._error_lbl)
        lay.addLayout(btn_row)
        self._show_page(0)

    # ------------------------------------------------------------ pages
    def _page_club(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(14)

        welcome = QLabel(
            "<h2>Willkommen bei BowTally!</h2>"
            "<p>Bitte gib ein paar grundlegende Informationen über deinen Verein ein.<br>"
            "Du kannst diese Angaben jederzeit unter <b>Einstellungen → Vereinsprofil</b> "
            "ändern.</p>",
            objectName="pageSubtitle")
        welcome.setWordWrap(True)
        welcome.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(welcome)

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
        lay.addWidget(box)
        lay.addStretch()
        return w

    def _page_license(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(10)

        title = QLabel("<h2>Lizenzbedingungen</h2>", objectName="pageSubtitle")
        lay.addWidget(title)

        browser = QTextBrowser()
        browser.setPlainText(config.license_text())
        browser.setOpenExternalLinks(False)
        lay.addWidget(browser, 1)

        self._license_check = QCheckBox(
            "Ich habe die Lizenzbedingungen gelesen und stimme ihnen zu.")
        lay.addWidget(self._license_check)
        lay.addStretch()
        return w

    # ------------------------------------------------------------ navigation
    def _show_page(self, index: int):
        self._stack.setCurrentIndex(index)
        self._next_btn.setText("Weiter" if index == 0 else "Speichern und starten")
        self._error_lbl.hide()

    def _next(self):
        if self._stack.currentIndex() == 0:
            if not self.club_name.text().strip():
                self._error_lbl.setText("Vereinsname ist erforderlich.")
                self._error_lbl.show()
                self.club_name.setFocus()
                return
            self._show_page(1)
            return
        self._save()

    def _save(self):
        if not self._license_check.isChecked():
            self._error_lbl.setText("Bitte stimme den Lizenzbedingungen zu.")
            self._error_lbl.show()
            return
        ss.save_club_profile({"club_name": self.club_name.text().strip(),
                              "city": self.city.text().strip(),
                              "federation": self.federation.text().strip()})
        self.accept()

    def reject(self):
        """License not accepted or wizard skipped: close the application."""
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
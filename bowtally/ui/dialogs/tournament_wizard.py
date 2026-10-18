# -*- coding: utf-8 -*-
"""9-step tournament wizard (also used to edit an existing tournament).

Every page shows a step indicator, a title and a short explanation.
"""
from PySide6.QtCore import QDate, Qt, QTime
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDateEdit, QDoubleSpinBox,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QScrollArea, QSpinBox, QTableWidget,
                               QTableWidgetItem, QTimeEdit, QToolButton, QVBoxLayout, QWidget,
                               QWizard, QWizardPage)

from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import button, repolish, show_error, theme
from bowtally.ui.components.capacity_bar import CapacityBar
from bowtally.ui.components.toast import Toast

DEFAULT_TARGETS = 28
DEFAULT_DEADLINE_DAYS = 14
STEPS = ["Grunddaten", "Regelwerk", "Bogenklassen", "Konfiguration", "Fristen und Zeiten",
         "Startgebühren", "Kontakt und Bank", "Hinweise und Texte", "Zusammenfassung"]
CHIP_COLUMNS = 3
INTRO_PLACEHOLDER = "Herzliche Einladung zum …"
CLOSING_PLACEHOLDER = "Wir freuen uns auf eure Teilnahme!"


class StepIndicator(QWidget):
    """Numbered dots; the current step shows its name, the others as tooltip."""

    def __init__(self, current: int):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 12)
        lay.setSpacing(6)
        for i, name in enumerate(STEPS):
            state = "current" if i == current else "done" if i < current else "todo"
            dot = QLabel("✓" if state == "done" else str(i + 1), objectName="stepDot")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setToolTip(name)
            dot.setProperty("state", state)
            repolish(dot)
            lay.addWidget(dot)
            if i == current:
                label = QLabel(name, objectName="stepLabel")
                label.setProperty("state", state)
                repolish(label)
                lay.addWidget(label)
            if i < len(STEPS) - 1:
                line = QFrame(objectName="stepLine")
                line.setMinimumWidth(10)
                lay.addWidget(line, 1)


class _Page(QWizardPage):
    def __init__(self, step: int, title: str, explanation: str, is_complete=None):
        super().__init__()
        self._is_complete = is_complete
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.addWidget(StepIndicator(step))
        outer.addWidget(QLabel(title, objectName="wizardTitle"))
        info = QLabel(explanation, objectName="pageSubtitle")
        info.setWordWrap(True)
        outer.addWidget(info)
        outer.addSpacing(8)
        self.body = QVBoxLayout()
        outer.addLayout(self.body, 1)

    def isComplete(self) -> bool:
        return self._is_complete() if self._is_complete else super().isComplete()


class FeeTable(QWidget):
    """Editable fee rows (name, amount, delete). Keeps the id of existing fees."""

    def __init__(self, fees: list[dict]):
        super().__init__()
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Bezeichnung", "Betrag", ""])
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(2, 44)
        self._ids: list[int | None] = []
        for f in fees:
            self.add_row(f.get("name", ""), f.get("amount", 0), f.get("id"))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.table, 1)
        lay.addWidget(button("Zeile hinzufügen", lambda: self.add_row("", 0),
                             tooltip="Weitere Startgebühr"), 0, Qt.AlignmentFlag.AlignLeft)

    def add_row(self, name: str, amount: float, fee_id: int | None = None):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._ids.append(fee_id)
        edit = QLineEdit(name)
        edit.setPlaceholderText("z. B. Erwachsene")
        self.table.setCellWidget(r, 0, edit)
        spin = QDoubleSpinBox()
        spin.setRange(0, 9999)
        spin.setDecimals(2)
        spin.setSuffix(" €")
        spin.setValue(float(amount or 0))
        self.table.setCellWidget(r, 1, spin)
        delete = QToolButton(objectName="iconButton")
        delete.setIcon(QIcon(theme.pixmap("trash", theme.current()["accent"], 16)))
        delete.setToolTip("Zeile löschen")
        delete.clicked.connect(lambda _=False, w=edit: self._remove(w))
        self.table.setCellWidget(r, 2, delete)
        if not name:
            edit.setFocus()

    def _remove(self, edit: QLineEdit):
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, 0) is edit:
                self.table.removeRow(r)
                del self._ids[r]
                return

    def fees(self) -> list[dict]:
        out = []
        for r in range(self.table.rowCount()):
            name = self.table.cellWidget(r, 0).text().strip()
            if name:
                out.append({"id": self._ids[r], "name": name,
                            "amount": self.table.cellWidget(r, 1).value()})
        return out


class TournamentWizard(QWizard):
    def __init__(self, tournament=None, parent=None):
        super().__init__(parent)
        self.tournament = tournament
        self.created_id: int | None = None
        self.setWindowTitle("Turnier bearbeiten" if tournament else "Neues Turnier")
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage)
        self.resize(860, 680)
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter")
        self.setButtonText(QWizard.WizardButton.BackButton, "Zurück")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")
        self.setButtonText(QWizard.WizardButton.FinishButton,
                           "Speichern" if tournament else "Turnier erstellen")
        for which in (QWizard.WizardButton.FinishButton, QWizard.WizardButton.NextButton):
            self.button(which).setProperty("primary", True)
            repolish(self.button(which))
        self.rules = sc.list_rules()
        self.classes = md.list_bow_classes()
        for page in (self._page_basics(), self._page_rule(), self._page_classes(),
                     self._page_config(), self._page_deadlines(), self._page_fees(),
                     self._page_contact(), self._page_texts(), self._page_summary()):
            self.addPage(page)

    def _t(self, attr, default=None):
        value = getattr(self.tournament, attr, None) if self.tournament else None
        return default if value is None else value

    # ------------------------------------------------------------ 1 basics
    def _page_basics(self) -> QWizardPage:
        t = self.tournament
        self.name = QLineEdit(self._t("name", ""))
        self.name.setPlaceholderText("z. B. 3D-Waldturnier 2027")
        self.date = QDateEdit()
        self.date.setDate(QDate(t.date) if t else QDate.currentDate().addDays(60))
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd.MM.yyyy")
        self.location = QLineEdit(self._t("location", ""))
        self.organizer = QLineEdit(self._t("organizer", ""))
        self.description = QPlainTextEdit(self._t("description", ""))
        self.description.setFixedHeight(90)
        page = _Page(0, "Grunddaten", "Wie heißt das Turnier, wann und wo findet es statt? "
                     "Pflicht ist nur der Name.", lambda: bool(self.name.text().strip()))
        self.name.textChanged.connect(page.completeChanged)
        form = QFormLayout()
        form.addRow("Turniername *", self.name)
        form.addRow("Datum *", self.date)
        form.addRow("Ort", self.location)
        form.addRow("Veranstalter", self.organizer)
        form.addRow("Beschreibung (intern)", self.description)
        page.body.addLayout(form)
        page.body.addStretch()
        return page

    # ------------------------------------------------------------ 2 rule
    def _page_rule(self) -> QWizardPage:
        self.rule_list = QListWidget()
        for r in self.rules:
            item = QListWidgetItem(r.name + ("  ·  eingebaut" if r.is_builtin else ""))
            item.setData(Qt.ItemDataRole.UserRole, r.id)
            self.rule_list.addItem(item)
            if self.tournament and r.id == self.tournament.scoring_rule_id:
                self.rule_list.setCurrentItem(item)
        self.matrix = QTableWidget(0, 2)
        self.matrix.setHorizontalHeaderLabels(["Zone", "Punkte"])
        self.matrix.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.matrix.verticalHeader().hide()
        self.matrix.setShowGrid(False)
        self.matrix.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.rule_info = QLabel(objectName="pageSubtitle")
        self.rule_info.setWordWrap(True)
        page = _Page(1, "Regelwerk", "Nach welchem Regelwerk wird gewertet? Rechts siehst du "
                     "die Punkte je Trefferzone. Es gibt bewusst keine Vorauswahl.",
                     lambda: self.selected_rule() is not None)
        self.rule_list.currentItemChanged.connect(lambda *_: (self._show_rule(),
                                                              page.completeChanged.emit()))
        right = QVBoxLayout()
        right.addWidget(QLabel("Punktematrix", objectName="fieldLabel"))
        right.addWidget(self.matrix, 1)
        right.addWidget(self.rule_info)
        row = QHBoxLayout()
        row.addWidget(self.rule_list, 1)
        row.addLayout(right, 1)
        page.body.addLayout(row)
        self._show_rule()
        return page

    def selected_rule(self):
        item = self.rule_list.currentItem()
        if item is None:
            return None
        rid = item.data(Qt.ItemDataRole.UserRole)
        return next(r for r in self.rules if r.id == rid)

    def _show_rule(self):
        rule = self.selected_rule()
        zones = rule.ring_values if rule else []
        self.matrix.setRowCount(len(zones))
        for i, z in enumerate(zones):
            self.matrix.setItem(i, 0, QTableWidgetItem(z["zone"]))
            pts = QTableWidgetItem(str(z["points"]))
            pts.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.matrix.setItem(i, 1, pts)
        self.rule_info.setText(
            f"{rule.max_shots_per_target} Schuss je Scheibe"
            f"{', Nachschuss erlaubt' if rule.allow_retry_shot else ''}. "
            f"{(rule.rules_json or {}).get('note', '')}" if rule
            else "Bitte links ein Regelwerk auswählen.")
        if rule and hasattr(self, "shots"):
            self.shots.setMaximum(rule.max_shots_per_target)
            if not self.tournament:
                self.shots.setValue(rule.max_shots_per_target)

    # ------------------------------------------------------------ 3 classes (chips)
    def _page_classes(self) -> QWizardPage:
        selected = {bc.id for bc in self.tournament.bow_classes} if self.tournament else None
        self.class_chips: dict[int, QPushButton] = {}
        page = _Page(2, "Bogenklassen", "Welche Klassen werden gewertet? Zum An- und Abwählen "
                     "einfach anklicken. Eingebaute Klassen sind vorausgewählt.",
                     lambda: any(c.isChecked() for c in self.class_chips.values()))
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(8)
        for i, bc in enumerate(self.classes):
            chip = QPushButton(f"{bc.name}  ({bc.abbreviation})" if bc.abbreviation else bc.name,
                               objectName="chip", checkable=True)
            chip.setChecked(bc.id in selected if selected is not None else bc.is_builtin)
            chip.setToolTip(bc.description or bc.name)
            chip.toggled.connect(page.completeChanged)
            self.class_chips[bc.id] = chip
            grid.addWidget(chip, i // CHIP_COLUMNS, i % CHIP_COLUMNS)
        grid.setRowStretch(len(self.classes) // CHIP_COLUMNS + 1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(inner)
        tools = QHBoxLayout()
        tools.addWidget(button("Alle", lambda: self._set_all_classes(True),
                               tooltip="Alle Klassen auswählen"))
        tools.addWidget(button("Keine", lambda: self._set_all_classes(False),
                               tooltip="Auswahl aufheben"))
        tools.addStretch()
        page.body.addLayout(tools)
        page.body.addWidget(scroll, 1)
        return page

    def _set_all_classes(self, checked: bool):
        for chip in self.class_chips.values():
            chip.setChecked(checked)

    # ------------------------------------------------------------ 4 config
    def _page_config(self) -> QWizardPage:
        self.targets = QSpinBox()
        self.targets.setRange(1, 200)
        self.targets.setValue(self._t("num_targets", DEFAULT_TARGETS))
        self.shots = QSpinBox()
        rule = self.selected_rule()
        self.shots.setRange(1, rule.max_shots_per_target if rule else 3)
        self.shots.setValue(self._t("shots_per_target",
                                    rule.max_shots_per_target if rule else 1))
        self.groups = QLineEdit(self._t("start_groups", ""))
        self.groups.setPlaceholderText("z. B. A, B, C, D")
        self.course_notes = QPlainTextEdit(self._t("notes", ""))
        self.course_notes.setPlaceholderText("z. B. Festes Schuhwerk empfohlen, Parcours ca. "
                                             "4 km")
        self.course_notes.setFixedHeight(70)
        page = _Page(3, "Konfiguration", "Wie viele Scheiben hat der Parcours und wie viele "
                     "Schüsse je Scheibe? Startgruppen sind optional und werden bei der "
                     "Startnummernvergabe reihum verteilt.")
        form = QFormLayout()
        form.addRow("Anzahl Scheiben", self.targets)
        form.addRow("Schüsse je Scheibe", self.shots)
        form.addRow("Startgruppen", self.groups)
        form.addRow("Hinweise zum Parcours", self.course_notes)
        page.body.addLayout(form)
        page.body.addStretch()
        return page

    # ------------------------------------------------------------ 5 deadlines
    def _page_deadlines(self) -> QWizardPage:
        self.deadline = QDateEdit()
        self.deadline.setCalendarPopup(True)
        self.deadline.setDisplayFormat("dd.MM.yyyy")
        deadline = self._t("registration_deadline")
        self.deadline.setDate(QDate(deadline) if deadline else
                              self.date.date().addDays(-DEFAULT_DEADLINE_DAYS))
        self.max_participants = QSpinBox()
        self.max_participants.setRange(0, 9999)
        self.max_participants.setValue(self._t("max_participants", 0))
        self.checkin_time = QTimeEdit(QTime.fromString(self._t("checkin_start_time", "09:00"),
                                                       "HH:mm"))
        self.shooting_time = QTimeEdit(QTime.fromString(self._t("shooting_start_time", "10:00"),
                                                        "HH:mm"))
        for w in (self.checkin_time, self.shooting_time):
            w.setDisplayFormat("HH:mm")
        self.practice = QCheckBox("Einschießen erlaubt")
        self.practice.setChecked(self._t("practice_allowed", True))
        self.practice_location = QLineEdit(self._t("practice_location", ""))
        self.practice_location.setPlaceholderText("z. B. dem Einschießplatz am Vereinsheim")
        self.capacity = CapacityBar()
        self.max_participants.valueChanged.connect(self._update_capacity)
        page = _Page(4, "Fristen und Zeiten", "Bis wann kann man sich anmelden, wie viele Plätze "
                     "gibt es und wann geht es am Turniertag los?")
        form = QFormLayout()
        form.addRow("Anmeldefrist", self.deadline)
        form.addRow("Maximale Teilnehmerzahl", self.max_participants)
        form.addRow("", QLabel("0 = keine Begrenzung", objectName="pageSubtitle"))
        form.addRow("Einschreibung ab", self.checkin_time)
        form.addRow("Schießbeginn", self.shooting_time)
        form.addRow("", self.practice)
        form.addRow("Einschießbereich", self.practice_location)
        form.addRow("Auslastung", self.capacity)
        self.practice.toggled.connect(lambda on: form.setRowVisible(self.practice_location, on))
        form.setRowVisible(self.practice_location, self.practice.isChecked())
        page.body.addLayout(form)
        page.body.addStretch()
        self._update_capacity()
        return page

    def _update_capacity(self):
        active = sum(ts.is_active_participant(p) for p in self.tournament.participants) \
            if self.tournament else 0
        mx = self.max_participants.value() or None
        self.capacity.set_capacity(ts.CapacityInfo(
            mx, active, max(mx - active, 0) if mx else None,
            min(active / mx * 100, 100) if mx else 0.0, bool(mx) and active >= mx))

    # ------------------------------------------------------------ 6 fees
    def _page_fees(self) -> QWizardPage:
        if self.tournament:
            fees = [{"id": f.id, "name": f.name, "amount": f.amount}
                    for f in self.tournament.fees]
        else:
            fees = [{"name": f.name, "amount": f.amount} for f in ts.list_fee_templates()]
        self.fee_table = FeeTable(fees)
        page = _Page(5, "Startgebühren", "Vorbelegt mit den Vorlagen. Bezeichnung und Betrag "
                     "sind direkt änderbar. Mindestens eine Gebühr wird empfohlen.")
        page.body.addWidget(self.fee_table, 1)
        return page

    # ------------------------------------------------------------ 7 contact + bank
    def _page_contact(self) -> QWizardPage:
        self.contact_name = QLineEdit(self._t("contact_name", ""))
        self.contact_phone = QLineEdit(self._t("contact_phone", ""))
        self.contact_email = QLineEdit(self._t("contact_email", ""))
        self.bank_holder = QLineEdit(self._t("bank_account_holder", ""))
        self.bank_iban = QLineEdit(self._t("bank_iban", ""))
        self.bank_iban.setPlaceholderText("DE00 0000 0000 0000 0000 00")
        self.bank_bic = QLineEdit(self._t("bank_bic", ""))
        self.bank_reference = QLineEdit(self._t("bank_reference_template", ""))
        self.bank_reference.setPlaceholderText("z. B. 3D Turnier 2027, {name}, {bow_class}")
        page = _Page(6, "Kontakt und Bankdaten", "Wer ist Ansprechpartner und wohin wird das "
                     "Startgeld überwiesen? Platzhalter im Verwendungszweck: {name}, "
                     "{bow_class}.")
        club = ss.get_club_profile()
        if any(club.get(k) for k in ("club_name", "phone", "email")):
            btn = button("Aus Vereinsprofil übernehmen", lambda: self._from_club(club),
                         tooltip="Telefon, E-Mail und Vereinsname (als Kontoinhaber) "
                                 "übernehmen")
            page.body.addWidget(btn, 0, Qt.AlignmentFlag.AlignLeft)
        form = QFormLayout()
        form.addRow(QLabel("Kontaktperson", objectName="sectionTitle"))
        form.addRow("Name", self.contact_name)
        form.addRow("Telefon", self.contact_phone)
        form.addRow("E-Mail", self.contact_email)
        form.addRow(QLabel("Bankverbindung", objectName="sectionTitle"))
        form.addRow("Kontoinhaber", self.bank_holder)
        form.addRow("IBAN", self.bank_iban)
        form.addRow("BIC", self.bank_bic)
        form.addRow("Verwendungszweck", self.bank_reference)
        page.body.addLayout(form)
        page.body.addStretch()
        return page

    def _from_club(self, club: dict):
        for edit, value in ((self.contact_phone, club.get("phone")),
                            (self.contact_email, club.get("email")),
                            (self.bank_holder, club.get("club_name"))):
            if value and not edit.text().strip():
                edit.setText(value)

    # ------------------------------------------------------------ 8 texts
    def _page_texts(self) -> QWizardPage:
        from bowtally.reports.announcement import split_info
        intro, closing = split_info(self._t("additional_info", ""))
        self.intro = QPlainTextEdit(intro)
        self.intro.setPlaceholderText(INTRO_PLACEHOLDER)
        self.legal = QPlainTextEdit(self._t("legal_notes", ss.get("default_legal_notes", "")))
        self.closing = QPlainTextEdit(closing)
        self.closing.setPlaceholderText(CLOSING_PLACEHOLDER)
        for w, h in ((self.intro, 80), (self.legal, 130), (self.closing, 60)):
            w.setFixedHeight(h)
        page = _Page(7, "Hinweise und Texte", "Texte für die Ausschreibung. Wichtige Hinweise: "
                     "eine Zeile je Hinweis.")
        form = QFormLayout()
        form.addRow("Einleitungstext", self.intro)
        form.addRow("Wichtige Hinweise", self.legal)
        form.addRow("Abschlusstext", self.closing)
        page.body.addLayout(form)
        page.body.addStretch()
        return page

    def _additional_info(self) -> str | None:
        # the first blank line separates intro and closing -> intro stays one paragraph
        intro = "\n".join(line for line in self.intro.toPlainText().splitlines()
                          if line.strip())
        closing = self.closing.toPlainText().strip()
        return "\n\n".join(p for p in (intro, closing) if p) or None

    # ------------------------------------------------------------ 9 summary
    def _page_summary(self) -> QWizardPage:
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.summary.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.summary.linkActivated.connect(self._jump)
        self.generate = QCheckBox("Ausschreibung jetzt generieren")
        self.generate.setChecked(self.tournament is None)
        page = _Page(8, "Zusammenfassung", "Bitte prüfen. Über „Bearbeiten“ springst du "
                     "direkt zum jeweiligen Schritt.")
        page.initializePage = self._fill_summary
        page.validatePage = self._create
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self.summary)
        page.body.addWidget(scroll, 1)
        page.body.addWidget(self.generate)
        return page

    def _jump(self, link: str):
        target = int(link)
        while self.currentId() > target:
            self.back()

    def _class_ids(self) -> list[int]:
        return [cid for cid, chip in self.class_chips.items() if chip.isChecked()]

    def _fill_summary(self):
        rule = self.selected_rule()
        names = [bc.name for bc in self.classes if bc.id in self._class_ids()]
        groups = ts.split_groups(self.groups.text())
        fees = self.fee_table.fees()
        warning = theme.current()["warning"]

        def esc(s):
            return str(s).replace("&", "&amp;").replace("<", "&lt;")

        def money(v):
            return f"{v:.2f} €".replace(".", ",")

        def short(text, n=80):
            return text if len(text) <= n else text[:n] + " …"

        legal_count = len([x for x in self.legal.toPlainText().splitlines() if x.strip()])
        sections = [
            (0, "Grunddaten", [("Name", self.name.text()),
                               ("Datum", self.date.date().toString("dd.MM.yyyy")),
                               ("Ort", self.location.text() or "–"),
                               ("Veranstalter", self.organizer.text() or "–")]),
            (1, "Regelwerk", [("Regelwerk", rule.name if rule else "–")]),
            (2, "Bogenklassen", [(f"{len(names)} Klassen", ", ".join(names))]),
            (3, "Konfiguration", [("Parcours", f"{self.targets.value()} Scheiben × "
                                               f"{self.shots.value()} Schuss"),
                                  ("Startgruppen", ", ".join(groups) or "keine")]),
            (4, "Fristen und Zeiten", [
                ("Anmeldefrist", self.deadline.date().toString("dd.MM.yyyy")),
                ("Max. Teilnehmer", self.max_participants.value() or "unbegrenzt"),
                ("Einschreibung / Start", f"{self.checkin_time.time().toString('HH:mm')} / "
                                          f"{self.shooting_time.time().toString('HH:mm')} Uhr"),
                ("Einschießen", (self.practice_location.text() or "ja")
                 if self.practice.isChecked() else "nein")]),
            (5, "Startgebühren", [(f["name"], money(f["amount"])) for f in fees]),
            (6, "Kontakt und Bank", [("Kontakt", " · ".join(filter(None, (
                self.contact_name.text(), self.contact_phone.text(),
                self.contact_email.text()))) or "–"),
                ("IBAN", self.bank_iban.text() or "–")]),
            (7, "Hinweise und Texte", [("Einleitung", short(self.intro.toPlainText()) or "–"),
                                       ("Hinweise", f"{legal_count} Einträge")]),
        ]
        html = []
        for step, title, rows in sections:
            html.append(f"<p style='margin-top:10px'><b style='font-size:11pt'>{title}</b>"
                        f"&nbsp;&nbsp;<a href='{step}'>Bearbeiten</a></p><table cellpadding='3'>")
            html += [f"<tr><td style='padding-right:16px'>{esc(k)}</td><td>{esc(v)}</td></tr>"
                     for k, v in rows]
            if step == 5 and not fees:
                html.append(f"<tr><td colspan='2' style='color:{warning}'><b>Warnung:</b> "
                            "Keine Startgebühr angelegt. Ohne Gebühr ist kein Wechsel in die "
                            "Anmeldephase möglich.</td></tr>")
            html.append("</table>")
        self.summary.setText("".join(html))

    def _create(self) -> bool:
        data = {"name": self.name.text().strip(), "date": self.date.date().toPython(),
                "location": self.location.text(), "organizer": self.organizer.text(),
                "description": self.description.toPlainText(),
                "scoring_rule_id": self.selected_rule().id,
                "num_targets": self.targets.value(), "shots_per_target": self.shots.value(),
                "start_groups": ", ".join(ts.split_groups(self.groups.text())) or None,
                "notes": self.course_notes.toPlainText(),
                "registration_deadline": self.deadline.date().toPython(),
                "max_participants": self.max_participants.value(),
                "checkin_start_time": self.checkin_time.time().toString("HH:mm"),
                "shooting_start_time": self.shooting_time.time().toString("HH:mm"),
                "practice_allowed": self.practice.isChecked(),
                "practice_location": self.practice_location.text()
                if self.practice.isChecked() else None,
                "contact_name": self.contact_name.text(),
                "contact_phone": self.contact_phone.text(),
                "contact_email": self.contact_email.text(),
                "bank_account_holder": self.bank_holder.text(),
                "bank_iban": self.bank_iban.text(), "bank_bic": self.bank_bic.text(),
                "bank_reference_template": self.bank_reference.text(),
                "legal_notes": self.legal.toPlainText(),
                "additional_info": self._additional_info()}
        try:
            t = ts.save_tournament(data, self._class_ids(),
                                   self.tournament.id if self.tournament else None,
                                   fees=self.fee_table.fees())
        except Exception as exc:
            show_error(self, exc, "Turnier konnte nicht gespeichert werden")
            return False
        self.created_id = t.id
        parent = self.parent() or self
        Toast.show(parent, f"Turnier '{t.name}' "
                   f"{'gespeichert' if self.tournament else 'erstellt'}", Toast.SUCCESS)
        if self.generate.isChecked():
            try:
                from bowtally.reports.announcement import generate_announcement_pdf
                from bowtally.ui.dialogs.export_helper import open_path
                path = generate_announcement_pdf(t.id)
                Toast.show(parent, "Ausschreibung erstellt", Toast.SUCCESS,
                           ("Öffnen", lambda: open_path(parent, path)))
            except Exception as exc:
                show_error(self, exc, "Ausschreibung konnte nicht erstellt werden")
        return True

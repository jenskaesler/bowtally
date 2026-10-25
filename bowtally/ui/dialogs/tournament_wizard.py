# -*- coding: utf-8 -*-
"""9-step tournament wizard (also used to edit an existing tournament).

Every page shows a step indicator, a title and a short explanation.
"""
from PySide6.QtCore import QDate, Qt, QTime, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QDoubleSpinBox,
                               QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QScrollArea, QSpinBox, QTableWidget,
                               QTableWidgetItem, QTimeEdit, QToolButton, QVBoxLayout, QWidget,
                               QWizard, QWizardPage)

from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import button, repolish, restore_geom, save_geom, show_error, theme
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


def _field_row(field: QWidget, btn: "QWidget | None") -> QWidget:
    if btn is None:
        return field
    w = QWidget()
    row = QHBoxLayout(w)
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(field, 1)
    row.addWidget(btn)
    return w


def _fill_if_empty(edit: QLineEdit, value: str):
    if value and not edit.text().strip():
        edit.setText(value)


def _fill_text_if_empty(edit: QPlainTextEdit, value: str):
    if value and not edit.toPlainText().strip():
        edit.setPlainText(value)


def _club_address(club: dict) -> str:
    parts = [club.get("street") or ""]
    city_part = " ".join(filter(None, [club.get("zip_code"), club.get("city")]))
    if city_part:
        parts.append(city_part)
    return ", ".join(p for p in parts if p)


class TournamentWizard(QWizard):
    def __init__(self, tournament=None, start_page: int = 0, clone: bool = False, parent=None):
        super().__init__(parent)
        self._template = tournament if clone else None
        self.tournament = None if clone else tournament
        self.created_id: int | None = None
        self._start_page = start_page
        self.setWindowTitle("Turnier kopieren" if clone
                            else ("Turnier bearbeiten" if tournament else "Neues Turnier"))
        self.setWizardStyle(QWizard.WizardStyle.ClassicStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage)
        self.resize(860, 680)
        restore_geom(self, "wizard")
        self.finished.connect(lambda: save_geom(self, "wizard"))
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

    def showEvent(self, event):
        super().showEvent(event)
        if self._start_page > 0:
            target = self._start_page
            self._start_page = 0
            QTimer.singleShot(0, lambda: self._advance_to(target))

    def _advance_to(self, target: int):
        while self.currentId() < target:
            self.next()

    def _t(self, attr, default=None):
        source = self.tournament or self._template
        value = getattr(source, attr, None) if source else None
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
        club = ss.get_club_profile()
        form = QFormLayout()
        form.addRow("Turniername *", self.name)
        form.addRow("Datum *", self.date)
        loc_row = _field_row(self.location,
                             button("Aus Stammdaten", lambda: _fill_if_empty(
                                 self.location, _club_address(club)),
                                    tooltip="Vereinsadresse übernehmen")
                             if club.get("city") else None)
        form.addRow("Ort", loc_row)
        org_row = _field_row(self.organizer,
                             button("Aus Stammdaten", lambda: _fill_if_empty(
                                 self.organizer, club.get("club_name", "")),
                                    tooltip="Vereinsname als Veranstalter übernehmen")
                             if club.get("club_name") else None)
        form.addRow("Veranstalter", org_row)
        form.addRow("Beschreibung (intern)", self.description)
        page.body.addLayout(form)
        page.body.addStretch()
        return page

    # ------------------------------------------------------------ 2 rule
    def _page_rule(self) -> QWizardPage:
        self.rule_list = QListWidget()
        for r in self.rules:
            item = QListWidgetItem(r.name + ("  ·  standard" if r.is_builtin else ""))
            item.setData(Qt.ItemDataRole.UserRole, r.id)
            self.rule_list.addItem(item)
            if self.tournament and r.id == self.tournament.scoring_rule_id:
                self.rule_list.setCurrentItem(item)
        self.rule_detail = QLabel()
        self.rule_detail.setWordWrap(True)
        self.rule_detail.setTextFormat(Qt.TextFormat.RichText)
        self.rule_detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.rule_detail.setObjectName("card")
        self.rule_detail.setMinimumWidth(200)
        page = _Page(1, "Regelwerk",
                     "Welches Regelwerk gilt? Links auswählen – rechts siehst du Details "
                     "und die Punktevergabe. Es gibt keine Vorauswahl.",
                     lambda: self.selected_rule() is not None)
        self.rule_list.currentItemChanged.connect(lambda *_: (self._show_rule(),
                                                              page.completeChanged.emit()))
        left = QVBoxLayout()
        left.addWidget(QLabel("Regelwerk auswählen", objectName="fieldLabel"))
        left.addWidget(self.rule_list, 1)
        right = QVBoxLayout()
        right.addWidget(QLabel("Regeldetails", objectName="fieldLabel"))
        right.addWidget(self.rule_detail, 1)
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addLayout(left, 1)
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
        if not rule:
            self.rule_detail.setText(
                "<p style='color:gray;padding:12px'>Bitte links ein Regelwerk auswählen.</p>")
            return
        zones_html = "".join(
            f"<tr><td style='padding:2px 20px 2px 0;color:gray'>{z['zone']}</td>"
            f"<td style='text-align:right;font-weight:bold'>{z['points']}</td></tr>"
            for z in rule.ring_values
        )
        note = (rule.rules_json or {}).get("note", "")
        retry = "  ·  Nachschuss erlaubt" if rule.allow_retry_shot else ""
        builtin = "  <span style='color:gray'>(standard)</span>" if rule.is_builtin else ""
        html = (
            f"<div style='padding:12px'>"
            f"<p style='font-size:12pt;font-weight:bold;margin:0 0 6px'>{rule.name}{builtin}</p>"
            f"<p style='margin:0 0 4px;color:gray'>"
            f"{rule.max_shots_per_target} Schuss je Scheibe{retry}</p>"
            + (f"<p style='margin:4px 0'>{note}</p>" if note else "")
            + f"<p style='font-weight:bold;margin:12px 0 4px'>Punkte je Trefferzone</p>"
            f"<table>{zones_html}</table></div>"
        )
        self.rule_detail.setText(html)
        if hasattr(self, "shots"):
            self.shots.setMaximum(rule.max_shots_per_target)
            if not self.tournament:
                self.shots.setValue(rule.max_shots_per_target)

    # ------------------------------------------------------------ 3 classes (chips)
    def _page_classes(self) -> QWizardPage:
        selected = {bc.id for bc in self.tournament.bow_classes} if self.tournament else None
        self.class_chips: dict[int, QPushButton] = {}
        page = _Page(2, "Bogenklassen", "Welche Klassen werden gewertet? Zum An- und Abwählen "
                     "einfach anklicken. Standardmäßig keine vorausgewählt.",
                     lambda: any(c.isChecked() for c in self.class_chips.values()))
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(8)
        for i, bc in enumerate(self.classes):
            chip = QPushButton(f"{bc.name}  ({bc.abbreviation})" if bc.abbreviation else bc.name,
                               objectName="chip", checkable=True)
            chip.setChecked(bc.id in selected if selected is not None else False)
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
        tools.addWidget(button("Eigene", self._set_custom_classes,
                               tooltip="Nur benutzerdefinierte Klassen auswählen"))
        tools.addStretch()
        page.body.addLayout(tools)
        page.body.addWidget(scroll, 1)
        return page

    def _set_all_classes(self, checked: bool):
        for chip in self.class_chips.values():
            chip.setChecked(checked)

    def _set_custom_classes(self):
        custom_ids = {bc.id for bc in self.classes if not bc.is_builtin}
        if custom_ids:
            for cid, chip in self.class_chips.items():
                chip.setChecked(cid in custom_ids)

    # ------------------------------------------------------------ 4 config
    def _page_config(self) -> QWizardPage:
        from PySide6.QtWidgets import QGroupBox
        self.groups = QLineEdit(self._t("start_groups", ""))
        self.groups.setPlaceholderText("z. B. A, B, C, D")
        self.course_notes = QPlainTextEdit(self._t("notes", ""))
        self.course_notes.setPlaceholderText("z. B. Festes Schuhwerk empfohlen, Parcours ca. "
                                             "4 km")
        self.course_notes.setFixedHeight(70)

        self.scoring_mode = QComboBox()
        for val, lbl in [
            ("per_target", "Scheibenwertung"),
            ("per_round", "Rundenwertung"),
            ("total_only", "Nur Gesamtpunkte"),
        ]:
            self.scoring_mode.addItem(lbl, val)  # noqa: just loop body
        cur = self._t("scoring_mode", "per_target")
        idx = self.scoring_mode.findData(cur)
        if idx >= 0:
            self.scoring_mode.setCurrentIndex(idx)

        self._round_table = QTableWidget(0, 6)
        self._round_table.setHorizontalHeaderLabels(
            ["Bezeichnung", "Regelwerk", "Ziele", "Pfeile", "Entfernung", ""])
        self._round_table.verticalHeader().setDefaultSectionSize(36)
        self._round_table.setShowGrid(False)
        h = self._round_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1, 140), (2, 60), (3, 60), (4, 110), (5, 36)]:
            h.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self._round_table.setColumnWidth(col, w)
        self._round_table.setFixedHeight(168)
        self._round_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._round_group = QGroupBox("Rundenkonfiguration")
        rg_lay = QVBoxLayout(self._round_group)
        rg_lay.setContentsMargins(8, 8, 8, 8)
        rg_lay.addWidget(self._round_table)
        add_btn = button("+ Runde", self._add_round, tooltip="Weitere Runde anlegen")
        tip = QLabel("Tipp: DBSV-Turnier → Runde 1 = Waldrunde, "
                     "Runde 2 = Jagdrunde", objectName="pageSubtitle")
        tip.setWordWrap(True)
        btn_row = QHBoxLayout()
        btn_row.addWidget(add_btn)
        btn_row.addSpacing(16)
        btn_row.addWidget(tip, 1)
        rg_lay.addLayout(btn_row)
        self._init_round_table()

        page = _Page(3, "Konfiguration", "Rundenkonfiguration, Wertungsmodus und Startgruppen. "
                     "Jede Runde kann ein eigenes Regelwerk und eigene Scheibenanzahl haben.")
        form = QFormLayout()
        club = ss.get_club_profile()
        course_desc = club.get("course_description") or ""
        notes_row = _field_row(
            self.course_notes,
            button("Aus Stammdaten", lambda: _fill_text_if_empty(self.course_notes, course_desc),
                   tooltip="Parcour-Beschreibung aus Vereinsprofil übernehmen")
            if course_desc else None)
        form.addRow("Wertungsmodus", self.scoring_mode)
        form.addRow("Startgruppen", self.groups)
        form.addRow("Hinweise zum Parcours", notes_row)
        page.body.addLayout(form)
        page.body.addWidget(self._round_group)
        page.body.addStretch()
        return page

    def _init_round_table(self):
        """Populate round table on page creation from existing rounds or defaults."""
        existing = {r.round_number: r for r in (self.tournament.rounds or [])} \
            if self.tournament else {}
        n = max(1, len(existing))
        self._round_table.setRowCount(n)
        for i in range(n):
            self._init_round_row(i, tr=existing.get(i + 1))

    def _init_round_row(self, i: int, tr=None):
        """Create all cell widgets for row i; skips columns that already have a widget."""
        if self._round_table.item(i, 0) is None:
            lbl = (tr.label if tr and tr.label else f"{i + 1}. Runde")
            self._round_table.setItem(i, 0, QTableWidgetItem(lbl))
        if self._round_table.cellWidget(i, 1) is None:
            cb = QComboBox()
            cb.addItem("Turnier-Standard", None)
            for rule in self.rules:
                cb.addItem(rule.name, rule.id)
            pre = tr.scoring_rule_id if tr else None
            if pre is not None:
                idx = cb.findData(pre)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            self._round_table.setCellWidget(i, 1, cb)
        if self._round_table.cellWidget(i, 2) is None:
            sp = QSpinBox()
            sp.setRange(0, 200)
            sp.setSpecialValueText("—")
            sp.setValue(tr.num_targets or 0 if tr else 0)
            self._round_table.setCellWidget(i, 2, sp)
        if self._round_table.cellWidget(i, 3) is None:
            sp = QSpinBox()
            sp.setRange(0, 10)
            sp.setSpecialValueText("—")
            sp.setValue(tr.shots_per_target or 0 if tr else 0)
            self._round_table.setCellWidget(i, 3, sp)
        if self._round_table.cellWidget(i, 4) is None:
            cb = QComboBox()
            cb.addItem("Standard", None)
            cb.addItem("Bekannte Entfernung", "known")
            cb.addItem("Unbekannte Entfernung", "unknown")
            pre = tr.distance_type if tr else None
            if pre:
                idx = cb.findData(pre)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
            self._round_table.setCellWidget(i, 4, cb)
        if self._round_table.cellWidget(i, 5) is None:
            btn = QToolButton(objectName="iconButton")
            btn.setIcon(QIcon(theme.pixmap("trash", theme.current()["accent"], 14)))
            btn.setToolTip("Runde entfernen")
            btn.clicked.connect(self._delete_round)
            self._round_table.setCellWidget(i, 5, btn)

    def _add_round(self):
        n = self._round_table.rowCount()
        self._round_table.setRowCount(n + 1)
        self._init_round_row(n)

    def _delete_round(self):
        if self._round_table.rowCount() <= 1:
            return
        btn = self.sender()
        for r in range(self._round_table.rowCount()):
            if self._round_table.cellWidget(r, 5) is btn:
                self._round_table.removeRow(r)
                return

    def _rounds_data(self) -> list[dict]:
        existing_ids = {}
        if self.tournament:
            for r in (self.tournament.rounds or []):
                existing_ids[r.round_number] = r.id
        rows = []
        for i in range(self._round_table.rowCount()):
            rn = i + 1
            it = self._round_table.item(i, 0)
            lbl = it.text().strip() if it else f"{rn}. Runde"
            rule_w = self._round_table.cellWidget(i, 1)
            tgt_w = self._round_table.cellWidget(i, 2)
            spt_w = self._round_table.cellWidget(i, 3)
            dt_w = self._round_table.cellWidget(i, 4)
            rows.append({
                "round_number": rn,
                "label": lbl or f"{rn}. Runde",
                "id": existing_ids.get(rn),
                "scoring_rule_id": rule_w.currentData() if rule_w else None,
                "num_targets": (tgt_w.value() or None) if tgt_w else None,
                "shots_per_target": (spt_w.value() or None) if spt_w else None,
                "distance_type": dt_w.currentData() if dt_w else None,
            })
        return rows

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
        self.practice.toggled.connect(lambda on: form.setRowVisible(self.practice_location, on))
        form.setRowVisible(self.practice_location, self.practice.isChecked())
        from PySide6.QtWidgets import QGroupBox
        cap_box = QGroupBox("Auslastung")
        cap_lay = QVBoxLayout(cap_box)
        cap_lay.setContentsMargins(8, 8, 8, 8)
        cap_lay.addWidget(self.capacity)
        page.body.addLayout(form)
        page.body.addWidget(cap_box)
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
        if any(club.get(k) for k in ("club_name", "phone", "email", "bank_iban")):
            btn = button("Aus Vereinsprofil übernehmen", lambda: self._from_club(club),
                         tooltip="Kontakt- und Bankdaten aus dem Vereinsprofil übernehmen")
            page.body.addWidget(btn, 0, Qt.AlignmentFlag.AlignLeft)
        _CONTACT_ROLES = [
            ("first_board", "1. Vorsitzender/in"),
            ("second_board", "2. Vorsitzender/in"),
            ("treasurer", "Kassenwart/-in"),
            ("sports_dir", "Sportleiter/in"),
            ("bow_ref", "Bogenreferent/in"),
        ]
        role_contacts = [(key, label,
                          f"{club.get(f'{key}_fname','') or ''} "
                          f"{club.get(f'{key}_lname','') or ''}".strip(),
                          club.get(f"{key}_phone") or "",
                          club.get(f"{key}_email") or "")
                         for key, label in _CONTACT_ROLES]
        role_contacts = [(k, l, n, p, e) for k, l, n, p, e in role_contacts if n]
        _role_data = {n: (p, e) for _, _, n, p, e in role_contacts}
        form = QFormLayout()
        if role_contacts:
            self._contact_combo = QComboBox()
            for _, label, name, _p, _e in role_contacts:
                self._contact_combo.addItem(f"{label}: {name}", name)
            stored = self._t("contact_name", "")
            idx = self._contact_combo.findData(stored)
            if idx >= 0:
                self._contact_combo.setCurrentIndex(idx)
            else:
                default_role = ss.get("default_contact_role", "treasurer")
                default_idx = next((i for i, (k, *_) in enumerate(role_contacts)
                                    if k == default_role),
                                   next((i for i, (k, *_) in enumerate(role_contacts)
                                         if k == "treasurer"), 0))
                self._contact_combo.setCurrentIndex(default_idx)
            self.contact_name.setText(self._contact_combo.currentData() or "")
            self._contact_combo.currentIndexChanged.connect(
                lambda: self.contact_name.setText(self._contact_combo.currentData() or ""))

            def _apply_contact():
                name = self._contact_combo.currentData() or ""
                self.contact_name.setText(name)
                phone, email = _role_data.get(name, ("", ""))
                if phone:
                    self.contact_phone.setText(phone)
                if email:
                    self.contact_email.setText(email)

            combo_row = QHBoxLayout()
            combo_row.setContentsMargins(0, 0, 0, 0)
            combo_row.addWidget(self._contact_combo, 1)
            combo_row.addWidget(button("Übernehmen", _apply_contact,
                                       tooltip="Name, Telefon und E-Mail dieser Person übernehmen"))
            combo_widget = QWidget()
            combo_widget.setLayout(combo_row)
            form.addRow("Kontaktperson", combo_widget)
        else:
            form.addRow("Kontaktperson", self.contact_name)
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
        for edit, value in (
            (self.contact_phone, club.get("phone")),
            (self.contact_email, club.get("email")),
            (self.bank_holder, club.get("bank_account_holder") or club.get("club_name")),
            (self.bank_iban, club.get("bank_iban")),
            (self.bank_bic, club.get("bank_bic")),
            (self.bank_reference, club.get("bank_reference_template")),
        ):
            if value:
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
        for w in (self.intro, self.legal, self.closing):
            w.setFixedHeight(130)
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
        self._sum_widget = QWidget()
        self._sum_layout = QVBoxLayout(self._sum_widget)
        self._sum_layout.setContentsMargins(2, 2, 4, 2)
        self._sum_layout.setSpacing(8)
        self.generate = QCheckBox("Ausschreibung jetzt generieren")
        self.generate.setChecked(self.tournament is None)
        page = _Page(8, "Zusammenfassung", "Bitte prüfen. Über „Bearbeiten“ springst du "
                     "direkt zum jeweiligen Schritt.")
        page.initializePage = self._fill_summary
        page.validatePage = self._create
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._sum_widget)
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
        while self._sum_layout.count():
            item = self._sum_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rule = self.selected_rule()
        names = [bc.name for bc in self.classes if bc.id in self._class_ids()]
        groups = ts.split_groups(self.groups.text())
        fees = self.fee_table.fees()
        warning = theme.current()["warning"]

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
            (3, "Konfiguration", [("Runden", str(self._round_table.rowCount())),
                                  ("Wertung", self.scoring_mode.currentText()),
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
        LABEL_W = 160
        for step, title, rows in sections:
            box = QFrame(objectName="card")
            box_lay = QVBoxLayout(box)
            box_lay.setContentsMargins(14, 10, 14, 12)
            box_lay.setSpacing(4)
            hdr_row = QHBoxLayout()
            hdr_row.setSpacing(8)
            hdr_row.addWidget(QLabel(title, objectName="sectionTitle"))
            edit_btn = QPushButton("Bearbeiten", objectName="link")
            edit_btn.clicked.connect(lambda _, s=step: self._jump(str(s)))
            hdr_row.addWidget(edit_btn)
            hdr_row.addStretch()
            box_lay.addLayout(hdr_row)
            box_lay.addWidget(QFrame(objectName="separator"))
            for key, val in rows:
                r = QHBoxLayout()
                r.setSpacing(0)
                k_lbl = QLabel(str(key))
                k_lbl.setFixedWidth(LABEL_W)
                k_lbl.setProperty("secondary", True)
                v_lbl = QLabel(str(val))
                v_lbl.setWordWrap(True)
                r.addWidget(k_lbl)
                r.addWidget(v_lbl, 1)
                box_lay.addLayout(r)
            if step == 5 and not fees:
                warn = QLabel(f"<b>Warnung:</b> Keine Startgebühr angelegt. Ohne Gebühr ist "
                              "kein Wechsel in die Anmeldephase möglich.")
                warn.setWordWrap(True)
                warn.setTextFormat(Qt.TextFormat.RichText)
                warn.setStyleSheet(f"color:{warning}")
                box_lay.addWidget(warn)
            self._sum_layout.addWidget(box)
        self._sum_layout.addStretch()

    def _create(self) -> bool:
        data = {"name": self.name.text().strip(), "date": self.date.date().toPython(),
                "location": self.location.text(), "organizer": self.organizer.text(),
                "description": self.description.toPlainText(),
                "scoring_rule_id": self.selected_rule().id,
                "num_targets": (self._round_table.cellWidget(0, 2).value() or DEFAULT_TARGETS)
                               if self._round_table.cellWidget(0, 2) else DEFAULT_TARGETS,
                "shots_per_target": (self._round_table.cellWidget(0, 3).value() or 1)
                                    if self._round_table.cellWidget(0, 3) else 1,
                "num_rounds": self._round_table.rowCount(),
                "scoring_mode": self.scoring_mode.currentData() or "per_target",
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
                                   fees=self.fee_table.fees(),
                                   rounds=self._rounds_data())
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

# -*- coding: utf-8 -*-
"""9-step tournament wizard (also used to edit an existing tournament).

Every page shows a step indicator, a title and a short explanation.
"""
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                               QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QScrollArea, QSizePolicy, QSpinBox, QTableWidget,
                               QTableWidgetItem, QToolButton, QVBoxLayout, QWidget,
                               QWizard, QWizardPage)

from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import button, repolish, restore_geom, save_geom, show_error, theme
from bowtally.ui.components.capacity_bar import CapacityBar
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.form_field import CurrencyField, DateField, TimeField
from bowtally.ui.components.toast import Toast

DEFAULT_TARGETS = 28
DEFAULT_DEADLINE_DAYS = 14
WIZARD_LABEL_W = 200   # fixed label column so all pages align
WIZARD_COMBO_W = 220   # fixed width for combos / date / time / spin
STEPS = ["Grunddaten", "Konfiguration", "Bogenklassen", "Fristen und Zeiten",
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


    def set_action_btn(self, btn: QWidget) -> None:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout().addWidget(sep)
        row = QHBoxLayout()
        row.addWidget(btn)
        row.addStretch()
        self.layout().addLayout(row)


class FeeTable(QWidget):
    """Editable fee rows (name, amount, delete). Keeps the id of existing fees."""

    def __init__(self, fees: list[dict]):
        super().__init__()
        self.table = QTableWidget(0, 3)
        self.table.setAlternatingRowColors(True)
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
        spin = CurrencyField()
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


def _form() -> QFormLayout:
    f = QFormLayout()
    f.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
    f.setHorizontalSpacing(12)
    f.setVerticalSpacing(8)
    return f


def _lbl(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFixedWidth(WIZARD_LABEL_W)
    return lbl


class TournamentWizard(QWizard):
    def __init__(self, tournament=None, start_page: int = 0, clone: bool = False, parent=None):
        super().__init__(parent)
        self._template = tournament if clone else None
        self.tournament = None if clone else tournament
        self.created_id: int | None = None
        self._start_page = start_page
        self.setWindowTitle("Turnier kopieren" if clone
                            else ("Turnier bearbeiten" if tournament else "Neues Turnier"))
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage)
        self.resize(860, 680)
        restore_geom(self, "wizard")
        self.finished.connect(lambda: save_geom(self, "wizard"))
        self.setButtonText(QWizard.WizardButton.NextButton, "Weiter")
        self.setButtonText(QWizard.WizardButton.BackButton, "Zurück")
        self.setButtonText(QWizard.WizardButton.CancelButton, "Abbrechen")
        self.button(QWizard.WizardButton.CancelButton).setProperty("cancel", True)
        self.setButtonText(QWizard.WizardButton.FinishButton,
                           "Speichern" if tournament else "Turnier erstellen")
        for which in (QWizard.WizardButton.FinishButton, QWizard.WizardButton.NextButton):
            self.button(which).setProperty("primary", True)
            repolish(self.button(which))
        self.rules = sc.list_rules()
        self.classes = md.list_bow_classes()
        # Page-specific actions live in the wizard footer as custom buttons (left of Back/Next)
        self._footer_actions: dict[int, tuple[str, str, callable]] = {}
        self.setOption(QWizard.WizardOption.HaveCustomButton1)
        self.customButtonClicked.connect(
            lambda which: which == QWizard.WizardButton.CustomButton1.value  # Signal liefert int
            and self._footer_actions[self.currentId()][2]())
        self.currentIdChanged.connect(self._update_footer)
        for page in (self._page_basics(), self._page_config(), self._page_classes(),
                     self._page_deadlines(), self._page_fees(),
                     self._page_contact(), self._page_texts(), self._page_summary()):
            self.addPage(page)
        self._update_footer(0)

    def _update_footer(self, page_id: int):
        B = QWizard.WizardButton
        left = []
        if page_id in self._footer_actions:
            text, tooltip, _ = self._footer_actions[page_id]
            self.setButtonText(B.CustomButton1, text)
            self.button(B.CustomButton1).setToolTip(tooltip)
            left.append(B.CustomButton1)
        self.setButtonLayout(left + [B.Stretch, B.BackButton, B.NextButton, B.FinishButton,
                                     B.CancelButton])

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
        self.date = DateField(allow_empty=False)
        self.date.setDate(QDate(t.date) if t else QDate.currentDate().addDays(60))
        self.date.setFixedWidth(WIZARD_COMBO_W)
        self.location = QLineEdit(self._t("location", ""))
        self.organizer = QLineEdit(self._t("organizer", ""))
        self.description = QPlainTextEdit(self._t("internal_notes", ""))
        self.description.setFixedHeight(90)
        page = _Page(0, "Grunddaten", "Wie heißt das Turnier, wann und wo findet es statt? "
                     "Pflicht ist nur der Name.", lambda: bool(self.name.text().strip()))
        self.name.textChanged.connect(page.completeChanged)
        club = ss.get_club_profile()
        form = _form()
        form.addRow(_lbl("Turniername *"), self.name)
        form.addRow(_lbl("Datum *"), self.date)
        form.addRow(_lbl("Ort"), self.location)
        form.addRow(_lbl("Veranstalter"), self.organizer)
        form.addRow(_lbl("Notizen (intern)"), self.description)
        self._basics_dirty: set = set()
        self.organizer.textEdited.connect(lambda _: self._basics_dirty.add("organizer"))
        self.location.textEdited.connect(lambda _: self._basics_dirty.add("location"))
        page.body.addLayout(form)
        page.body.addStretch()
        if club.get("club_name") or club.get("city"):
            self._footer_actions[0] = ("Vereinsdaten übernehmen",
                                       "Veranstalter und Ort aus dem Vereinsprofil übernehmen",
                                       lambda: self._fill_basics(club))
        return page

    # ------------------------------------------------------------ 2 classes (chips)
    def _page_classes(self) -> QWizardPage:
        selected = {bc.id for bc in self.tournament.bow_classes} if self.tournament else None
        self.class_chips: dict[int, QPushButton] = {}
        page = _Page(2, "Bogenklassen", "Welche Klassen werden gewertet? "
                     "Zum An- und Abwählen einfach anklicken. Standardmäßig keine vorausgewählt.",
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

    # ------------------------------------------------------------ 1 config
    def _page_config(self) -> QWizardPage:
        self.groups = QLineEdit(self._t("start_groups", ""))
        self.groups.setPlaceholderText("z. B. A, B, C, D")
        self._draw_cb = QCheckBox("Teilnehmer per Auslosung einteilen")
        self._draw_cb.setChecked(bool(self._t("use_draw", False)))
        self.groups.setReadOnly(self._draw_cb.isChecked())
        self._draw_cb.toggled.connect(self.groups.setReadOnly)

        self.scoring_mode = QComboBox()
        self.scoring_mode.setFixedWidth(WIZARD_COMBO_W)
        for val, lbl in [
            ("per_target", "Pro Ziel"),
            ("per_round", "Rundenwertung"),
            ("total_only", "Nur Gesamtpunkte"),
        ]:
            self.scoring_mode.addItem(lbl, val)  # noqa: just loop body
        cur = self._t("scoring_mode", "per_target")
        idx = self.scoring_mode.findData(cur)
        if idx >= 0:
            self.scoring_mode.setCurrentIndex(idx)

        self._round_table = QTableWidget(0, 6)
        self._round_table.setAlternatingRowColors(True)
        self._round_table.setHorizontalHeaderLabels(
            ["Bezeichnung", "Regelwerk", "Ziele", "Pfeile", "Entfernung", ""])
        self._round_table.verticalHeader().setDefaultSectionSize(36)
        self._round_table.setShowGrid(False)
        h = self._round_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, w in [(1, 140), (2, 60), (3, 60), (4, 110), (5, 36)]:
            h.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self._round_table.setColumnWidth(col, w)
        self._round_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._round_group = QGroupBox("Rundenkonfiguration")
        self._round_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        rg_lay = QVBoxLayout(self._round_group)
        rg_lay.setContentsMargins(8, 8, 8, 8)
        rg_lay.addWidget(self._round_table, 1)
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

        page = _Page(1, "Konfiguration",
                     "Rundenkonfiguration, Wertungsmodus und Startgruppen. "
                     "Jede Runde hat ein eigenes Regelwerk und eigene Scheibenanzahl.")
        form = _form()
        form.addRow(_lbl("Wertungsmodus"), self.scoring_mode)
        form.addRow(_lbl(""), self._draw_cb)
        form.addRow(_lbl("Startgruppen"), self.groups)
        page.body.addLayout(form)
        page.body.addWidget(self._round_group, 1)
        return page

    def _init_round_table(self):
        """Populate round table on page creation from existing rounds or defaults."""
        existing = {r.round_number: r for r in (self.tournament.rounds or [])} \
            if self.tournament else {}
        n = max(1, len(existing))
        self._round_table.setRowCount(n)
        self._loading_rounds = True
        for i in range(n):
            self._init_round_row(i, tr=existing.get(i + 1))
        self._loading_rounds = False
        if self.tournament is None:
            for r in range(n):
                self._on_rule_changed(r)

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
            if pre is None and self.tournament is None:
                default_id = ss.get("default_scoring_rule_id")
                if default_id:
                    pre = int(default_id)
            cb.currentIndexChanged.connect(lambda idx, row=i: self._on_rule_changed(row))
            self._round_table.setCellWidget(i, 1, cb)
            if pre is not None:
                idx = cb.findData(pre)
                if idx >= 0:
                    cb.setCurrentIndex(idx)
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

    def _on_rule_changed(self, row: int):
        if getattr(self, "_loading_rounds", False):
            return
        cb = self._round_table.cellWidget(row, 1)
        rule_id = cb.currentData() if cb else None
        rule = next((r for r in self.rules if r.id == rule_id), None)
        if rule is None:
            return
        sp = self._round_table.cellWidget(row, 3)
        if sp:
            sp.setValue(rule.max_shots_per_target or 0)

    def _add_round(self):
        n = self._round_table.rowCount()
        self._round_table.setRowCount(n + 1)
        self._init_round_row(n)
        self._on_rule_changed(n)  # Spalte 3 existiert erst jetzt: Pfeile aus Default-Regelwerk setzen

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
        self.deadline = DateField(allow_empty=False)
        deadline = self._t("registration_deadline")
        self.deadline.setDate(QDate(deadline) if deadline else
                              self.date.date().addDays(-DEFAULT_DEADLINE_DAYS))
        self.max_participants = QSpinBox()
        self.max_participants.setRange(0, 9999)
        self.max_participants.setValue(self._t("max_participants", 0))
        self.checkin_time = TimeField(allow_empty=False)
        self.checkin_time.setTime(self._t("checkin_start_time", "09:00") or "09:00")
        self.shooting_time = TimeField(allow_empty=False)
        self.shooting_time.setTime(self._t("shooting_start_time", "10:00") or "10:00")
        for w in (self.deadline, self.checkin_time, self.shooting_time, self.max_participants):
            w.setFixedWidth(WIZARD_COMBO_W)
        self.practice = QCheckBox("Einschießen erlaubt")
        self.practice.setChecked(self._t("practice_allowed", False))
        self.practice_location = QLineEdit(self._t("practice_location", ""))
        self.practice_location.setPlaceholderText("z. B. dem Einschießplatz am Vereinsheim")
        self.capacity = CapacityBar()
        self.max_participants.valueChanged.connect(self._update_capacity)
        page = _Page(3, "Fristen und Zeiten", "Bis wann kann man sich anmelden, wie viele Plätze "
                     "gibt es und wann geht es am Turniertag los?")
        page.validatePage = self._validate_practice
        form = _form()
        form.addRow(_lbl("Anmeldefrist"), self.deadline)
        form.addRow(_lbl("Einschreibung ab"), self.checkin_time)
        form.addRow(_lbl("Schießbeginn"), self.shooting_time)
        form.addRow("", self.practice)
        form.addRow(_lbl("Einschießbereich"), self.practice_location)
        form.addRow(_lbl("Maximale Teilnehmerzahl"), self.max_participants)
        form.addRow("", QLabel("0 = keine Begrenzung", objectName="pageSubtitle"))
        self.practice.toggled.connect(lambda on: form.setRowVisible(self.practice_location, on))
        form.setRowVisible(self.practice_location, self.practice.isChecked())
        cap_box = QGroupBox("Auslastung")
        cap_lay = QVBoxLayout(cap_box)
        cap_lay.setContentsMargins(8, 8, 8, 8)
        cap_lay.addWidget(self.capacity)
        page.body.addLayout(form)
        page.body.addWidget(cap_box)
        page.body.addStretch()
        self._update_capacity()
        return page

    def _validate_practice(self) -> bool:
        if self.practice.isChecked() and not self.practice_location.text().strip():
            Toast.show(self, "Bitte den Einschießbereich angeben.", Toast.WARNING)
            self.practice_location.setFocus()
            return False
        return True

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
        page = _Page(4, "Startgebühren", "Vorbelegt mit den Vorlagen. Bezeichnung und Betrag "
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
        page = _Page(5, "Kontakt und Bankdaten", "Wer ist Ansprechpartner und wohin wird das "
                     "Startgeld überwiesen? Platzhalter im Verwendungszweck: {name}, "
                     "{bow_class}.")
        club = ss.get_club_profile()
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
        form = _form()
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
            form.addRow(_lbl("Kontaktperson"), self._contact_combo)
        else:
            form.addRow(_lbl("Kontaktperson"), self.contact_name)
        form.addRow(_lbl("Telefon"), self.contact_phone)
        form.addRow(_lbl("E-Mail"), self.contact_email)
        form.addRow(QLabel("Bankverbindung", objectName="sectionTitle"))
        form.addRow(_lbl("Kontoinhaber"), self.bank_holder)
        form.addRow(_lbl("IBAN"), self.bank_iban)
        form.addRow(_lbl("BIC"), self.bank_bic)
        form.addRow(_lbl("Verwendungszweck"), self.bank_reference)
        self._contact_dirty: set = set()
        for _w in (self.contact_name, self.contact_phone, self.contact_email,
                   self.bank_holder, self.bank_iban, self.bank_bic, self.bank_reference):
            _w.textEdited.connect(lambda _, w=_w: self._contact_dirty.add(w))
        page.body.addLayout(form)
        page.body.addStretch()
        if any(club.get(k) for k in ("club_name", "phone", "email", "bank_iban")):
            self._footer_actions[5] = ("Vereinsdaten übernehmen",
                                       "Kontakt- und Bankdaten aus dem Vereinsprofil übernehmen",
                                       lambda: self._fill_contact(club, _role_data))
        return page

    def _fill_basics(self, club: dict):
        club_name = club.get("club_name", "")
        city = club.get("city", "")
        overwrite = []
        if "organizer" in self._basics_dirty and club_name:
            overwrite.append("Veranstalter")
        if "location" in self._basics_dirty and city:
            overwrite.append("Ort")
        if overwrite and not ConfirmDialog.ask(
                self, "Felder überschreiben?",
                "Folgende Felder sind bereits ausgefüllt und werden überschrieben:\n– " +
                "\n– ".join(overwrite), "Überschreiben", destructive=False):
            return
        if club_name:
            self.organizer.setText(club_name)
        if city:
            self.location.setText(city)
        self._basics_dirty.clear()
        Toast.show(self, "Vereinsdaten übernommen.", Toast.INFO)

    def _fill_contact(self, club: dict, role_data: dict):
        contact_name_val = ""
        contact_phone_val = ""
        contact_email_val = ""
        if hasattr(self, "_contact_combo"):
            name = self._contact_combo.currentData() or ""
            contact_name_val = name
            contact_phone_val, contact_email_val = role_data.get(name, ("", ""))
        fills = {
            "Kontaktperson": (self.contact_name, contact_name_val),
            "Telefon": (self.contact_phone, contact_phone_val),
            "E-Mail": (self.contact_email, contact_email_val),
            "Kontoinhaber": (self.bank_holder,
                             club.get("bank_account_holder") or club.get("club_name", "")),
            "IBAN": (self.bank_iban, club.get("bank_iban", "")),
            "BIC": (self.bank_bic, club.get("bank_bic", "")),
            "Verwendungszweck": (self.bank_reference, club.get("bank_reference_template", "")),
        }
        overwrite = [label for label, (edit, val) in fills.items()
                     if edit in self._contact_dirty and val]
        if overwrite and not ConfirmDialog.ask(
                self, "Felder überschreiben?",
                "Folgende Felder sind bereits ausgefüllt und werden überschrieben:\n– " +
                "\n– ".join(overwrite), "Überschreiben", destructive=False):
            return
        for _label, (edit, val) in fills.items():
            if val:
                edit.setText(val)
        self._contact_dirty.clear()
        Toast.show(self, "Vereinsdaten übernommen.", Toast.INFO)

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
        # Parcours-Hinweise: aus den Einstellungen vorbelegen, solange das Turnier keine eigenen hat
        club = ss.get_club_profile()
        course_desc = (club.get("course_description")
                       or ss.get("default_parcours_description", "") or "")
        self.course_notes = QPlainTextEdit(self._t("notes", "") or course_desc)
        self.course_notes.setPlaceholderText("z. B. Festes Schuhwerk empfohlen, Parcours ca. 4 km")
        self.course_notes.setFixedHeight(70)
        page = _Page(6, "Hinweise und Texte", "Texte für die Ausschreibung. Wichtige Hinweise: "
                     "eine Zeile je Hinweis.")
        form = _form()
        form.addRow(_lbl("Einleitungstext"), self.intro)
        form.addRow(_lbl("Hinweise zum Parcours"), self.course_notes)
        form.addRow(_lbl("Wichtige Hinweise"), self.legal)
        form.addRow(_lbl("Abschlusstext"), self.closing)
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
        page = _Page(7, "Zusammenfassung",
                     "Bitte prüfen. Bearbeiten-Links springen direkt zum jeweiligen Schritt.")
        page.initializePage = self._fill_summary
        page.validatePage = self._create
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._sum_widget)
        page.body.addWidget(scroll, 1)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        page.body.addWidget(sep)
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
            (1, "Konfiguration", [("Runden", str(self._round_table.rowCount())),
                                  ("Wertung", self.scoring_mode.currentText()),
                                  ("Startgruppen", ", ".join(groups) or "keine")]),
            (2, "Bogenklassen", [(f"{len(names)} Klassen", ", ".join(names))]),
            (3, "Fristen und Zeiten", [
                ("Anmeldefrist", self.deadline.date().toString("dd.MM.yyyy")),
                ("Max. Teilnehmer", self.max_participants.value() or "unbegrenzt"),
                ("Einschreibung / Start", f"{self.checkin_time.time().toString('HH:mm')} / "
                                          f"{self.shooting_time.time().toString('HH:mm')} Uhr"),
                ("Einschießen", (self.practice_location.text() or "ja")
                 if self.practice.isChecked() else "nein")]),
            (4, "Startgebühren", [(f["name"], money(f["amount"])) for f in fees]),
            (5, "Kontakt und Bank", [("Kontakt", " · ".join(filter(None, (
                self.contact_name.text(), self.contact_phone.text(),
                self.contact_email.text()))) or "–"),
                ("IBAN", self.bank_iban.text() or "–")]),
            (6, "Hinweise und Texte", [("Einleitung", short(self.intro.toPlainText()) or "–"),
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
            if step == 4 and not fees:
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
                "internal_notes": self.description.toPlainText(),
                "scoring_rule_id": (self._round_table.cellWidget(0, 1).currentData()
                                    if self._round_table.rowCount() > 0
                                    and self._round_table.cellWidget(0, 1) else None),
                "num_targets": (self._round_table.cellWidget(0, 2).value() or DEFAULT_TARGETS)
                               if self._round_table.cellWidget(0, 2) else DEFAULT_TARGETS,
                "shots_per_target": (self._round_table.cellWidget(0, 3).value() or 1)
                                    if self._round_table.cellWidget(0, 3) else 1,
                "num_rounds": self._round_table.rowCount(),
                "scoring_mode": self.scoring_mode.currentData() or "per_target",
                "start_groups": ", ".join(ts.split_groups(self.groups.text())) or None,
                "use_draw": self._draw_cb.isChecked(),
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
        if self._template is not None:
            try:
                from bowtally.services import course_service as cs
                from bowtally.services import prize_service as prs
                cs.copy_targets(self._template.id, t.id)
                prs.copy_prizes(self._template.id, t.id)
            except Exception:
                pass
        parent = self.parent() or self
        Toast.show(parent, f"Turnier '{t.name}' "
                   f"{'gespeichert' if self.tournament else 'erstellt'}", Toast.SUCCESS)
        return True

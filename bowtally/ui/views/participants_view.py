# -*- coding: utf-8 -*-
"""Participant management of one tournament: picker, registration / payment status,
inline editing, bulk actions, capacity limit and import."""
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDateEdit, QDialog, QDoubleSpinBox,
                               QFormLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMenu, QPushButton, QRadioButton, QVBoxLayout, QWidget)

from bowtally.io.importer import PARTICIPANT_IMPORT_FIELDS
from bowtally.services import master_data_service as md
from bowtally.services import participant_service as ps
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, restore_geom, save_geom, show_error
from bowtally.ui.utils.mailto import open_mailto, tournament_ctx
from bowtally.ui.components.action_bar import Action, ActionBar
from bowtally.ui.components.capacity_bar import CapacityBar
from bowtally.ui.components.confirm_dialog import ConfirmDialog, choose
from bowtally.ui.components.data_table import Cell, ComboDelegate, DataTable, ID_ROLE, TimeDelegate
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.search_bar import SearchBar
from bowtally.ui.components.status_chip import payment_chip, registration_chip
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.dialogs.export_helper import open_path
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.views import menu

HEADERS = ["St.-Nr.", "Name", "Verein", "Bogenklasse", "Startgruppe", "Gebühr", "Anmeldung",
           "Zahlung", "Startzeit"]
COL_NO, COL_CLASS, COL_GROUP, COL_FEE, COL_TIME = 0, 3, 4, 5, 8
ALL_GROUPS = "__all__"
CLOSED_HINT = "Das Turnier ist abgeschlossen, Änderungen sind gesperrt."


def money(amount: float | None) -> str:
    return "–" if amount is None else f"{amount:.2f} €".replace(".", ",")


def full_hint(cap) -> str:
    return f"Maximale Teilnehmerzahl erreicht ({cap.active_count}/{cap.max})"


class ArcherPicker(QDialog):
    """Search + check boxes; archers already in the tournament are greyed out."""

    def __init__(self, assigned_ids: set[int], free_slots: int | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Schützen zuweisen")
        self.resize(560, 600)
        restore_geom(self, "archer_picker")
        self.finished.connect(lambda: save_geom(self, "archer_picker"))
        self.free_slots = free_slots
        self.search = SearchBar("Name, Verein oder Mitgliedsnummer …")
        self.list = QListWidget()
        self.archers = {a.id: a for a in md.list_archers()}
        for a in self.archers.values():
            text = f"{a.last_name}, {a.first_name}"
            details = " · ".join(x for x in (a.club, a.default_bow_class.name
                                              if a.default_bow_class else None) if x)
            item = QListWidgetItem(f"{text}   {details}" if details else text)
            item.setData(Qt.ItemDataRole.UserRole, a.id)
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         f"{text} {a.club or ''} {a.member_number or ''}".lower())
            if a.id in assigned_ids:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setToolTip("Bereits diesem Turnier zugewiesen")
            else:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.list.itemChanged.connect(self._update_count)
        self.list.itemActivated.connect(self._toggle)
        self.search.searchChanged.connect(self._filter)
        self.ok = button("Hinzufügen (0)", self.accept, "primary",
                         "Ausgewählte Schützen dem Turnier zuweisen")
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Abbrechen", self.reject, tooltip="Nichts zuweisen"))
        row.addWidget(self.ok)
        self.hint = QLabel(objectName="pageSubtitle")
        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.list, 1)
        lay.addWidget(self.hint)
        lay.addLayout(row)
        self._update_count()

    def _toggle(self, item):
        if item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
            item.setCheckState(Qt.CheckState.Unchecked if item.checkState()
                               == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def _filter(self, term: str):
        term = term.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(term) and term not in item.data(Qt.ItemDataRole.UserRole + 1))

    def selected_ids(self) -> list[int]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]

    def _update_count(self, *_):
        n = len(self.selected_ids())
        too_many = self.free_slots is not None and n > self.free_slots
        self.ok.setText(f"Hinzufügen ({n})")
        self.ok.setEnabled(0 < n and not too_many)
        base = "Anklicken zum Auswählen. Grau = bereits zugewiesen."
        if self.free_slots is not None:
            base += f" Noch {self.free_slots} Plätze frei."
        self.hint.setText(f"Nur noch {self.free_slots} Plätze frei – bitte weniger auswählen."
                          if too_many else base)


class ClassAssignDialog(QDialog):
    """Asks for a bow class for archers whose default class is not part of the tournament."""

    def __init__(self, archers: list, classes: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bogenklasse zuordnen")
        info = QLabel("Für diese Schützen ist die Standardklasse im Turnier nicht aktiv. "
                      "Bitte eine Klasse wählen:")
        info.setWordWrap(True)
        form = QFormLayout()
        self.combos = {}
        for a in archers:
            cb = QComboBox()
            for bc in classes:
                cb.addItem(bc.name, bc.id)
            self.combos[a.id] = cb
            form.addRow(f"{a.first_name} {a.last_name}", cb)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Abbrechen", self.reject, tooltip="Nicht zuweisen"))
        row.addWidget(button("Speichern", self.accept, "primary", "Klassen übernehmen"))
        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addLayout(form)
        lay.addLayout(row)

    def choices(self) -> dict[int, int]:
        return {aid: cb.currentData() for aid, cb in self.combos.items()}


class _WaitlistNotifyDialog(QDialog):
    """List currently-waitlisted participants; send each a mailto from email_waitlist template."""

    def __init__(self, waitlisted, freed_slots: int, tournament, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warteliste benachrichtigen")
        self.resize(480, 360)
        self._waitlisted = waitlisted
        self._freed = freed_slots
        self._tournament = tournament
        info = QLabel(
            f"{freed_slots} Platz/Plätze frei geworden – "
            f"{len(waitlisted)} Personen auf der Warteliste.",
            objectName="pageSubtitle"
        )
        info.setWordWrap(True)
        self.lst = QListWidget()
        for p in waitlisted:
            has_email = bool(p.archer.email)
            text = (f"{p.archer.last_name}, {p.archer.first_name}"
                    + (f"   {p.archer.email}" if has_email else "   (keine E-Mail)"))
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, p)
            if has_email:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setToolTip("Keine E-Mail-Adresse hinterlegt")
            self.lst.addItem(item)
        self.lst.itemChanged.connect(self._update_btn)
        self.btn = button("E-Mail senden (0)", self._send, "primary")
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Schließen", self.reject))
        row.addWidget(self.btn)
        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addWidget(self.lst, 1)
        lay.addLayout(row)
        self._update_btn()

    def _update_btn(self, *_):
        n = sum(
            1 for i in range(self.lst.count())
            if self.lst.item(i).checkState() == Qt.CheckState.Checked
        )
        self.btn.setText(f"E-Mail senden ({n})")
        self.btn.setEnabled(n > 0)

    def _send(self):
        t = self._tournament
        for i in range(self.lst.count()):
            item = self.lst.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            p = item.data(Qt.ItemDataRole.UserRole)
            open_mailto(ss.KEY_EMAIL_TPL_WAITLIST, p.archer.email, {
                "name": f"{p.archer.first_name} {p.archer.last_name}",
                "verein": p.archer.club or "",
                "klasse": p.bow_class.name if p.bow_class else "",
                "turniername": t.name,
                "datum": f"{t.date:%d.%m.%Y}",
                "freigewordene_plaetze": str(self._freed),
                **tournament_ctx(t, p),
            }, self)
        self.accept()


class _ConfirmPaymentDialog(QDialog):
    """Capture payment status (and optionally fee) when confirming registrations."""

    def __init__(self, fees, current_fee_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anmeldung bestätigen")
        self.resize(380, 240)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.fee_combo = QComboBox()
        self.fee_combo.addItem("– keine –", 0)
        for f in fees:
            self.fee_combo.addItem(f"{f.name} ({money(f.amount)})", f.id)
        idx = self.fee_combo.findData(current_fee_id or 0)
        self.fee_combo.setCurrentIndex(max(0, idx))
        form.addRow("Startgebühr:", self.fee_combo)

        self._btn_grp = QButtonGroup(self)
        self._radio_unpaid = QRadioButton("Ausstehend")
        self._radio_pending = QRadioButton("Erwartet")
        self._radio_paid = QRadioButton("Eingegangen")
        self._radio_unpaid.setChecked(True)
        for i, rb in enumerate([self._radio_unpaid, self._radio_pending, self._radio_paid]):
            self._btn_grp.addButton(rb, i)
        pay_row = QHBoxLayout()
        pay_row.setContentsMargins(0, 0, 0, 0)
        for rb in (self._radio_unpaid, self._radio_pending, self._radio_paid):
            pay_row.addWidget(rb)
        pay_row.addStretch()
        pay_widget = QWidget()
        pay_widget.setLayout(pay_row)
        form.addRow("Zahlung:", pay_widget)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 9999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" €")
        self._lbl_amount = QLabel("Betrag:")
        form.addRow(self._lbl_amount, self.amount_spin)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self._lbl_date = QLabel("Datum:")
        form.addRow(self._lbl_date, self.date_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(button("Abbrechen", self.reject))
        btn_row.addWidget(button("Bestätigen", self.accept, "primary"))

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addStretch()
        lay.addLayout(btn_row)

        self._toggle_paid(False)
        self._radio_paid.toggled.connect(self._toggle_paid)

    def _toggle_paid(self, checked: bool):
        for w in (self._lbl_amount, self.amount_spin, self._lbl_date, self.date_edit):
            w.setVisible(checked)

    def fee_id(self) -> int | None:
        return self.fee_combo.currentData() or None

    def payment_status(self) -> str:
        return ("unpaid", "pending", "paid")[self._btn_grp.checkedId()]

    def amount(self) -> float | None:
        return self.amount_spin.value() if self._radio_paid.isChecked() else None

    def payment_date(self):
        if not self._radio_paid.isChecked():
            return None
        from datetime import date as _date
        d = self.date_edit.date()
        return _date(d.year(), d.month(), d.day())


class ParticipantsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self._parts = {}
        self.search = SearchBar("Teilnehmer suchen …")
        self.search.searchChanged.connect(lambda _t: self._apply_filter())
        self.group_filter = QComboBox()
        self.group_filter.setToolTip("Nach Startgruppe filtern")
        self.group_filter.currentIndexChanged.connect(lambda _i: self._apply_filter())
        self.status_filter = QComboBox()
        self.status_filter.addItem("Alle Teilnehmer", "")
        self.status_filter.addItem("Warteliste", "waitlisted")
        self.status_filter.setToolTip("Nach Status filtern")
        self.status_filter.currentIndexChanged.connect(lambda _i: self._apply_filter())
        self.btn_add = button("Schütze zuweisen", self.pick_archers, "primary",
                              "Schützen aus den Stammdaten zuweisen (Strg+N)")
        self._more_menu = QMenu()
        self._act_renumber = self._more_menu.addAction(
            "Startnummern neu vergeben", self._renumber)
        self._act_import = self._more_menu.addAction(
            "Importieren …", self._import)
        self._more_menu.addSeparator()
        self._act_draw = self._more_menu.addAction("Auslosung …", self._run_draw)
        self._act_starter = self._more_menu.addAction(
            "Starterfeld drucken", self._print_starter)
        self.btn_more = QPushButton("Weitere ▾")
        self.btn_more.setMenu(self._more_menu)
        self.btn_more.setStyleSheet("QPushButton::menu-indicator { image: none; }")
        self.capacity = CapacityBar()
        self.capacity.setFixedWidth(280)
        bar = QHBoxLayout()
        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_more)
        bar.addSpacing(8)
        bar.addWidget(self.search, 1)
        bar.addWidget(self.group_filter)
        bar.addWidget(self.status_filter)
        bar.addSpacing(8)
        bar.addWidget(self.capacity)

        empty = EmptyState("users", "Noch keine Teilnehmer",
                           "Weise Schützen aus den Stammdaten zu oder importiere eine "
                           "Teilnehmerliste.", "Schütze zuweisen")
        empty.actionTriggered.connect(self.pick_archers)
        self.table = DataTable(HEADERS, empty, multi_select=True)
        self.table.set_delegate(COL_CLASS, ComboDelegate(self._class_options, parent=self))
        self.table.set_delegate(COL_GROUP, ComboDelegate(self._group_options, editable=True,
                                                         parent=self))
        self.table.set_delegate(COL_FEE, ComboDelegate(self._fee_options, parent=self))
        self.table.set_delegate(COL_TIME, TimeDelegate(parent=self))
        self.table.cellEdited.connect(self._on_cell_edited)
        self.table.selectionChanged.connect(self._on_selection)
        self.table.contextMenuRequested.connect(self._context_menu)
        self.action_bar = ActionBar()
        hint = QLabel("Doppelklick auf Startnummer, Bogenklasse, Startgruppe, Gebühr oder "
                      "Startzeit bearbeitet direkt in der Tabelle. Rechtsklick für "
                      "Anmeldung, Zahlung und Status.", objectName="pageSubtitle")
        hint.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.table, 1)
        lay.addWidget(self.action_bar)
        lay.addWidget(hint)

    # ------------------------------------------------------------ data
    def set_tournament(self, tournament):
        from bowtally.services.settings_service import get as _get_setting
        self.tournament = t = tournament
        editable = t.status != "closed"
        assignable = editable and t.phase != "shooting"
        cap = ts._capacity(t)
        waitlist_auto = _get_setting("waitlist_mode", "block") == "auto"
        self.capacity.set_capacity(cap)
        shooting_hint = "In der Schieß-Phase können keine Teilnehmer mehr verwaltet werden."
        self._act_renumber.setEnabled(assignable)
        self._act_renumber.setToolTip(
            "Nummern 1..n nach Klasse und Name, Gruppen reihum" if assignable
            else (CLOSED_HINT if not editable else shooting_hint))
        self._act_import.setEnabled(assignable)
        self._act_import.setToolTip(
            "Teilnehmerliste aus CSV, Excel oder OpenDocument" if assignable
            else (CLOSED_HINT if not editable else shooting_hint))
        self._act_draw.setEnabled(editable)
        self._act_starter.setEnabled(True)
        self.btn_more.setEnabled(True)
        add_ok = assignable and (not cap.is_full or waitlist_auto)
        self.btn_add.setEnabled(add_ok)
        self.btn_add.setToolTip(CLOSED_HINT if not editable
                                else shooting_hint if not assignable
                                else full_hint(cap) if cap.is_full and not waitlist_auto
                                else "Schützen aus den Stammdaten zuweisen (Strg+N)")
        parts = sorted(t.participants, key=lambda p: (p.start_number or 10**9,
                                                      p.archer.last_name))
        self._parts = {p.id: p for p in parts}
        self.table.set_rows([[
            Cell(p.start_number, editable=editable),
            f"{p.archer.last_name}, {p.archer.first_name}", p.archer.club,
            Cell(p.bow_class.name if p.bow_class else "", data=p.bow_class_id,
                 editable=editable),
            Cell(p.start_group, editable=editable),
            Cell(p.entry_fee.amount if p.entry_fee else None,
                 text=money(p.entry_fee.amount) if p.entry_fee else "–",
                 data=p.entry_fee_id, editable=editable,
                 tooltip=p.entry_fee.name if p.entry_fee else "Keine Gebühr zugewiesen"),
            Cell(p.registration_status, chip=registration_chip(p.registration_status)),
            Cell(p.payment_status, chip=payment_chip(p.payment_status),
                 tooltip=f"{money(p.fee_amount_paid)} am {p.payment_date:%d.%m.%Y}"
                 if p.payment_date else ""),
            Cell(p.start_time, editable=editable)] for p in parts], [p.id for p in parts])
        current = self.group_filter.currentData()
        self.group_filter.blockSignals(True)
        self.group_filter.clear()
        self.group_filter.addItem("Alle Startgruppen", ALL_GROUPS)
        groups = sorted(set(ts.split_groups(t.start_groups))
                        | {p.start_group for p in parts if p.start_group})
        for g in groups:
            self.group_filter.addItem(f"Gruppe {g}", g)
        self.group_filter.setCurrentIndex(max(0, self.group_filter.findData(current)))
        self.group_filter.setVisible(bool(groups))
        self.group_filter.blockSignals(False)
        self._apply_filter()
        self._on_selection(self.table.selected_ids())

    def _reload(self):
        self.set_tournament(ts.get_tournament(self.tournament.id))
        context.notify()

    def _apply_filter(self):
        self.table.apply_filter(self.search.term())
        group = self.group_filter.currentData()
        if group not in (None, ALL_GROUPS):
            for r in range(self.table.table.rowCount()):
                item = self.table.table.item(r, COL_GROUP)
                if item is not None and item.text() != group:
                    self.table.table.setRowHidden(r, True)
        status_f = self.status_filter.currentData()
        if status_f:
            for r in range(self.table.table.rowCount()):
                if not self.table.table.isRowHidden(r):
                    item = self.table.table.item(r, 0)
                    pid = item.data(ID_ROLE) if item else None
                    p = self._parts.get(pid)
                    if p and p.registration_status != status_f:
                        self.table.table.setRowHidden(r, True)

    def _class_options(self):
        return [(bc.name, bc.id) for bc in self.tournament.bow_classes]

    def _group_options(self):
        return [("", "")] + [(g, g) for g in ts.split_groups(self.tournament.start_groups)]

    def _fee_options(self):
        return [("– keine –", 0)] + [(f"{f.name} ({money(f.amount)})", f.id)
                                     for f in self.tournament.fees]

    # ------------------------------------------------------------ inline editing
    def _on_cell_edited(self, pid, column, value):
        try:
            if column == COL_FEE:
                ps.set_entry_fee(pid, value or None)
            else:
                key = {COL_NO: "start_number", COL_CLASS: "bow_class_id",
                       COL_GROUP: "start_group", COL_TIME: "start_time"}.get(column)
                if key is None:
                    return
                if key == "start_number":
                    text = str(value).strip()
                    if text and not text.isdigit():
                        Toast.show(self, f"Startnummer '{text}' ist keine Zahl", Toast.WARNING)
                        self._reload()
                        return
                    value = int(text) if text else None
                ts.update_participant(pid, {key: value})
        except Exception as exc:
            show_error(self, exc)
        self._reload()

    # ------------------------------------------------------------ selection / bulk
    def _selected(self):
        return [self._parts[i] for i in self.table.selected_ids() if i in self._parts]

    def _locked(self) -> bool:
        return self.tournament is not None and self.tournament.status == "closed"

    def _assignment_locked(self) -> bool:
        return self.tournament is not None and (
            self.tournament.status == "closed" or self.tournament.phase == "shooting"
        )

    def _on_selection(self, ids):
        n = len(ids)
        locked = self._locked()
        alocked = self._assignment_locked()
        tip = CLOSED_HINT if locked else ""
        atip = tip or ("In der Schieß-Phase gesperrt." if alocked else "")
        sel = self._selected()
        to_confirm = sum(p.registration_status == "registered" for p in sel)
        to_pay = sum(p.payment_status != "paid" and p.registration_status != "withdrawn"
                     and p.entry_fee_id is not None for p in sel)
        actions = [] if not n else [
            Action("Anmeldung bestätigen",
                   self.confirm_selected, enabled=not locked and to_confirm > 0,
                   tooltip=tip or 'Status „Bestätigt" setzen'),
            Action("Zahlung eingegangen", self.mark_paid_selected,
                   enabled=not locked and to_pay > 0,
                   tooltip=tip or 'Zahlungsstatus „Bezahlt" mit heutigem Datum'),
            Action("Entfernen", self.remove_selected, "danger", enabled=not alocked,
                   tooltip=atip or "Aus dem Turnier entfernen (mit Rückfrage)")]
        self.action_bar.set_actions(
            "1 Teilnehmer ausgewählt" if n == 1 else f"{n} Teilnehmer ausgewählt", actions)

    def _context_menu(self, _pid, pos):
        locked = self._locked()
        alocked = self._assignment_locked()
        checkin_phase = self.tournament.phase in ("checkin", "shooting")
        sel = self._selected()
        active = ("registered", "confirmed", "checked_in")
        all_withdrawn = all(p.registration_status == "withdrawn" for p in sel)
        entries = [
            ("Anmeldung bestätigen", self.confirm_selected,
             not locked and any(p.registration_status in ("registered", "waitlisted")
                                for p in sel)),
            ("Zahlung als eingegangen markieren", self.mark_paid_selected,
             not locked and any(p.payment_status != "paid" and p.entry_fee_id is not None
                                and p.registration_status != "withdrawn" for p in sel)),
        ]
        if checkin_phase:
            entries.append(("Einchecken", lambda: self._set_status("checked_in"),
                            not locked and any(p.registration_status in active
                                               and p.registration_status != "checked_in"
                                               for p in sel)))
            entries.append(("Einchecken rückgängig", lambda: self._set_status("confirmed"),
                            not locked and any(p.registration_status == "checked_in"
                                               for p in sel)))
        entries += [
            ("Als DNS markieren (nicht gestartet)", lambda: self._set_status("dns"),
             not locked and any(p.registration_status in active for p in sel)),
            ("Als zurückgezogen markieren", lambda: self._set_status("withdrawn"),
             not locked and any(p.registration_status in active for p in sel)),
            ('Auf „Gemeldet" zurücksetzen', lambda: self._set_status("registered"),
             not locked and any(p.registration_status in ("confirmed", "checked_in")
                                for p in sel)),
            ("Zahlung als ausstehend markieren", lambda: self._set_payment("unpaid"),
             not locked and not all_withdrawn),
            None,
            ("Gebühr zuweisen …", self.change_fee, not locked and not all_withdrawn),
            ("Klasse ändern …", self.change_class, not alocked and not all_withdrawn),
            ("Gruppe ändern …", self.change_group, not alocked and not all_withdrawn),
            None,
            ("Entfernen", self.remove_selected, not alocked),
        ]
        has_email = any(p.archer.email for p in sel)
        email_ok = has_email and not locked
        entries += [
            None,
            ("E-Mail: Anmeldebestätigung senden",
             lambda: self._send_email(ss.KEY_EMAIL_TPL_CONFIRMATION), email_ok),
            ("E-Mail: Zahlungserinnerung senden",
             lambda: self._send_email(ss.KEY_EMAIL_TPL_PAYMENT), email_ok),
            ("E-Mail: Startunterlagen senden",
             lambda: self._send_email(ss.KEY_EMAIL_TPL_DOCS), email_ok),
        ]
        menu(self, entries).exec(pos)

    def confirm_selected(self):
        sel = self._selected()
        if not sel:
            return
        first_fee_id = sel[0].entry_fee_id if sel else None
        dlg = _ConfirmPaymentDialog(self.tournament.fees, first_fee_id, self)
        if not dlg.exec():
            return
        n = ps.confirm_with_payment(
            [p.id for p in sel], dlg.fee_id(), dlg.payment_status(), dlg.amount(),
            dlg.payment_date())
        Toast.show(self, f"{n} Anmeldungen bestätigt", Toast.SUCCESS)
        self._reload()
        with_email = [p for p in sel if p.archer.email]
        if with_email and ConfirmDialog.ask(
                self, "Bestätigungsmail senden?",
                f"Bestätigungsmail an {len(with_email)} Teilnehmer senden?",
                "E-Mail senden", destructive=False):
            t = self.tournament
            for p in with_email:
                open_mailto(ss.KEY_EMAIL_TPL_CONFIRMATION, p.archer.email, {
                    "name": f"{p.archer.first_name} {p.archer.last_name}",
                    "verein": p.archer.club or "",
                    "klasse": p.bow_class.name if p.bow_class else "",
                    "turniername": t.name,
                    "datum": f"{t.date:%d.%m.%Y}",
                    **tournament_ctx(t, p),
                }, self)

    def mark_paid_selected(self):
        sel = self._selected()
        if not sel:
            return
        missing_fee = [p for p in sel if not p.entry_fee_id]
        if missing_fee and not ConfirmDialog.ask(
                self, "Gebühr nicht zugewiesen",
                f"Bei {len(missing_fee)} Teilnehmer"
                f"{'n' if len(missing_fee) > 1 else ''} ist noch keine Gebühr zugewiesen. "
                "Trotzdem als bezahlt markieren?",
                "Trotzdem markieren", destructive=False):
            return
        n = ps.bulk_mark_paid([p.id for p in sel])
        Toast.show(self, f"{n} Zahlungen als eingegangen markiert", Toast.SUCCESS)
        self._reload()

    def _set_status(self, status: str):
        sel = self._selected()
        if status == "registered" or status in ("dns", "withdrawn"):
            if status != "registered" and not ConfirmDialog.ask(
                    self, "Status ändern?",
                    f'{len(sel)} Teilnehmer werden als „{ps.REGISTRATION_LABELS[status]}" '
                    "markiert.", "Ändern", destructive=False):
                return
        try:
            for p in sel:
                ps.set_registration_status(p.id, status)
        except Exception as exc:
            show_error(self, exc)
        promoted = 0
        if status in ("withdrawn", "dsq"):
            promoted = ts.promote_from_waitlist(self.tournament.id)
        Toast.show(self, f"Status: {ps.REGISTRATION_LABELS[status]}", Toast.SUCCESS)
        self._reload()
        if promoted:
            self._show_promoted_toast(promoted)

    def _set_payment(self, status: str):
        for p in self._selected():
            ps.set_payment_status(p.id, status)
        Toast.show(self, f"Zahlung: {ps.PAYMENT_LABELS[status]}", Toast.SUCCESS)
        self._reload()

    def change_fee(self):
        sel = self._selected()
        if not sel:
            return
        fid = choose(self, "Gebühr zuweisen", f"Startgebühr für {len(sel)} Teilnehmer:",
                     self._fee_options(), sel[0].entry_fee_id or 0)
        if fid is choose.CANCELLED:
            return
        for p in sel:
            ps.set_entry_fee(p.id, fid or None)
        Toast.show(self, f"Gebühr für {len(sel)} Teilnehmer gesetzt", Toast.SUCCESS)
        self._reload()

    def change_class(self):
        sel = self._selected()
        if not sel:
            return
        cid = choose(self, "Klasse ändern", f"Bogenklasse für {len(sel)} Teilnehmer:",
                     self._class_options(), sel[0].bow_class_id)
        if cid is choose.CANCELLED:
            return
        with busy():
            for p in sel:
                ts.update_participant(p.id, {"bow_class_id": cid})
        Toast.show(self, f"Klasse für {len(sel)} Teilnehmer geändert", Toast.SUCCESS)
        self._reload()

    def change_group(self):
        sel = self._selected()
        if not sel:
            return
        group = choose(self, "Gruppe ändern", f"Startgruppe für {len(sel)} Teilnehmer:",
                       self._group_options()[1:] or [("", "")], sel[0].start_group,
                       editable=True)
        if group is choose.CANCELLED:
            return
        with busy():
            for p in sel:
                ts.update_participant(p.id, {"start_group": group or None})
        Toast.show(self, f"Startgruppe für {len(sel)} Teilnehmer geändert", Toast.SUCCESS)
        self._reload()

    def remove_selected(self):
        sel = self._selected()
        if not sel:
            return
        with_scores = [p for p in sel if ts.participant_has_scores(p.id)]
        text = (f"{sel[0].archer.first_name} {sel[0].archer.last_name} wird aus dem Turnier "
                "entfernt." if len(sel) == 1 else f"{len(sel)} Teilnehmer werden aus dem Turnier "
                "entfernt.")
        text += '\n\nTipp: „Als zurückgezogen markieren" behält die Anmeldung in der Historie.'
        if with_scores:
            text += f"\n\nAchtung: Für {len(with_scores)} davon sind bereits Ergebnisse " \
                    "erfasst. Diese werden gelöscht."
        if not ConfirmDialog.ask(self, "Teilnehmer entfernen?", text, "Entfernen"):
            return
        with busy():
            for p in sel:
                ts.remove_participant(p.id)
        promoted = ts.promote_from_waitlist(self.tournament.id)
        Toast.show(self, f"{len(sel)} Teilnehmer entfernt", Toast.SUCCESS)
        self._reload()
        if promoted:
            self._show_promoted_toast(promoted)

    def _show_promoted_toast(self, promoted: int):
        waitlisted = [p for p in self._parts.values()
                      if p.registration_status == "waitlisted"]
        action = (("Benachrichtigen",
                   lambda wl=waitlisted, fr=promoted: self._notify_waitlist(wl, fr))
                  if waitlisted else None)
        Toast.show(self, f"{promoted} Teilnehmer von Warteliste nachgerückt",
                   Toast.SUCCESS, action)

    def _notify_waitlist(self, waitlisted, freed_slots: int):
        dlg = _WaitlistNotifyDialog(waitlisted, freed_slots, self.tournament, self)
        dlg.exec()

    def _send_email(self, template_key: str):
        sel = self._selected()
        if not sel:
            return
        t = self.tournament
        if len(sel) > 1 and not ConfirmDialog.ask(
                self, "Mehrere E-Mails öffnen?",
                f"{len(sel)} Mail-Fenster werden geöffnet.", "Fortfahren",
                destructive=False):
            return
        for p in sel:
            open_mailto(template_key, p.archer.email, {
                "name": f"{p.archer.first_name} {p.archer.last_name}",
                "verein": p.archer.club or "",
                "klasse": p.bow_class.name if p.bow_class else "",
                "turniername": t.name,
                "datum": f"{t.date:%d.%m.%Y}",
                **tournament_ctx(t, p),
            }, self)

    # ------------------------------------------------------------ add / import
    def pick_archers(self):
        if self.tournament is None or self.tournament.status == "closed":
            return
        from bowtally.services.settings_service import get as _get_setting
        t = self.tournament
        cap = ts._capacity(t)
        waitlist_auto = _get_setting("waitlist_mode", "block") == "auto"
        if cap.is_full and not waitlist_auto:
            Toast.show(self, full_hint(cap), Toast.WARNING)
            return
        picker = ArcherPicker({p.archer_id for p in t.participants},
                              None if waitlist_auto else cap.free_slots, self)
        if not picker.exec() or not picker.selected_ids():
            return
        ids = picker.selected_ids()
        active = {bc.id for bc in t.bow_classes}
        unresolved = [picker.archers[i] for i in ids
                      if picker.archers[i].default_bow_class_id not in active]
        choices = {}
        if unresolved:
            dlg = ClassAssignDialog(unresolved, t.bow_classes, self)
            if not dlg.exec():
                return
            choices = dlg.choices()
        try:
            with busy():
                added = ts.add_participants(t.id, ids)
                if choices:
                    by_archer = {p.archer_id: p.id
                                 for p in ts.get_tournament(t.id).participants}
                    for aid, cid in choices.items():
                        ts.update_participant(by_archer[aid], {"bow_class_id": cid})
        except Exception as exc:
            show_error(self, exc)
            return
        Toast.show(self, f"{added} Teilnehmer zugewiesen", Toast.SUCCESS)
        self._reload()

    def _renumber(self):
        if ConfirmDialog.ask(self, "Startnummern neu vergeben?",
                             "Alle Startnummern werden neu von 1 an vergeben (sortiert nach "
                             "Klasse und Name), Startgruppen werden reihum verteilt.",
                             "Neu vergeben", destructive=False):
            ts.assign_start_numbers(self.tournament.id)
            Toast.show(self, "Startnummern neu vergeben", Toast.SUCCESS)
            self._reload()

    def _import(self):
        tid = self.tournament.id
        res = run_import(self, PARTICIPANT_IMPORT_FIELDS, "Teilnehmerliste importieren",
                         lambda records, strategy: ts.import_capacity_error(tid, records,
                                                                            strategy))
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = ts.import_participants(tid, records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"{r['added']} Teilnehmer hinzugefügt ({r['created']} Schützen neu "
                         f"angelegt, {r['updated']} aktualisiert)", Toast.SUCCESS)
        self._reload()

    def _run_draw(self):
        from bowtally.ui.dialogs.draw_dialog import DrawDialog
        DrawDialog(self).exec()
        self._reload()

    def _print_starter(self):
        from bowtally.reports.starter_list import build_starter_list
        try:
            with busy():
                path = build_starter_list(self.tournament.id, sort_by="group")
        except Exception as exc:
            show_error(self, exc)
            return
        Toast.show(self, "Starterfeld erstellt", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, path)))

    # global shortcuts
    def shortcut_new(self):
        self.pick_archers()

    def shortcut_find(self):
        self.search.setFocus()
        self.search.selectAll()

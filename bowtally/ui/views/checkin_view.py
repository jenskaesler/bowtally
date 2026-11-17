# -*- coding: utf-8 -*-
"""Check-in desk: search by name or start number, check in with Enter, register walk-ins."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout,
                               QWidget)

from bowtally.services import participant_service as ps
from bowtally.services import tournament_service as ts
from bowtally.ui import button, show_error
from bowtally.ui.components.capacity_bar import CapacityBar
from bowtally.ui.components.data_table import Cell, DataTable
from bowtally.ui.components.drawer import SideDrawer
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import Form
from bowtally.ui.components.search_bar import SearchBar
from bowtally.ui.components.status_chip import payment_chip, registration_chip
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.views import BAR_BOTTOM_MARGIN
from bowtally.ui.views.participants_view import money

HEADERS = ["Nr.", "Name", "Verein", "Klasse", "Anmeldung", "Zahlung"]
CHECKIN_PHASES = ("checkin", "shooting")
PAYMENT_WARNING = "Achtung: Startgebühr nicht als eingegangen markiert"


class CheckinView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self._results = {}
        self.search = SearchBar("Name oder Startnummer eingeben und Enter drücken …")
        self.search.searchChanged.connect(self._search)
        self.counter = QLabel(objectName="bigCounter")
        self.capacity = CapacityBar()
        self.capacity.setFixedWidth(320)
        self.phase_hint = QLabel(objectName="dangerText")
        self.btn_checkin = button("Einchecken", self.checkin_selected, "primary",
                                  "Ausgewählten Teilnehmer einchecken (Enter)")
        self.btn_walkin = button("Als Walk-in erfassen", self.open_walk_in, "danger",
                                 "Neuen Teilnehmer vor Ort erfassen und direkt einchecken")
        self.payment_warning = QLabel(PAYMENT_WARNING, objectName="dangerText")
        self.payment_warning.hide()
        self.not_found = QLabel(objectName="pageSubtitle")
        self.not_found.hide()               # an empty row would add a gap above the list

        empty = EmptyState("search", "Nicht gefunden",
                           "Kein Teilnehmer passt zur Suche. Neue Teilnehmer vor Ort als "
                           "Walk-in erfassen.", "Als Walk-in erfassen")
        empty.actionTriggered.connect(self.open_walk_in)
        self.empty = empty
        self.table = DataTable(HEADERS, empty)
        self.table.selectionChanged.connect(self._on_selection)
        self.table.activated.connect(lambda _id: self.checkin_selected())

        top = QHBoxLayout()
        top.addWidget(self.counter)
        top.addSpacing(20)
        top.addWidget(self.capacity)
        top.addStretch()
        top.addWidget(self.phase_hint)
        search_row = QHBoxLayout()
        search_row.addWidget(self.search)
        search_row.addWidget(self.btn_checkin)
        search_row.addWidget(self.btn_walkin)
        search_row.addStretch(1)
        actions = QHBoxLayout()
        actions.addWidget(self.payment_warning)
        actions.addStretch()
        actions.addWidget(self.not_found)

        search_row.setContentsMargins(0, 0, 0, BAR_BOTTOM_MARGIN)
        main = QVBoxLayout()
        main.setContentsMargins(0, 8, 0, 0)
        main.setSpacing(10)
        main.addLayout(top)
        main.addLayout(search_row)
        main.addLayout(actions)
        main.addWidget(self.table, 1)

        # simplified participant drawer for walk-ins
        self.form = Form()
        self.cls = QComboBox()
        self.fee = QComboBox()
        self.form.add("first_name", "Vorname", QLineEdit(), required=True)
        self.form.add("last_name", "Nachname", QLineEdit(), required=True)
        self.form.add("club", "Verein", QLineEdit())
        self.form.add("bow_class_id", "Bogenklasse", self.cls, required=True)
        self.form.add("entry_fee_id", "Startgebühr", self.fee)
        self.form.add("paid", "Bezahlt", QCheckBox("Startgebühr bar bezahlt"))
        self.drawer = SideDrawer(self.form)
        self.drawer.saveRequested.connect(self._save_walk_in)
        self.drawer.closed.connect(self.search.setFocus)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        lay.addLayout(main, 1)
        lay.addWidget(self.drawer)

    # ------------------------------------------------------------ data
    def set_tournament(self, t):
        self.tournament = t
        enabled = t.phase in CHECKIN_PHASES and t.status != "closed"
        self.phase_hint.setText("" if enabled else
                                "Einchecken ist in den Phasen „Einschreibung“ und „Schießen“ "
                                "möglich.")
        stats = ts.get_tournament_stats(t.id)
        self.counter.setText(f"Eingecheckt: {stats.by_status['checked_in']} / "
                             f"Erwartet: {stats.expected}")
        cap = stats.capacity
        self.capacity.set_capacity(cap)
        self.btn_walkin.setEnabled(enabled)  # Walk-ins also allowed when capacity is reached
        self.btn_walkin.setToolTip("Neuen Teilnehmer vor Ort erfassen und direkt einchecken")
        self.empty.cta.setEnabled(self.btn_walkin.isEnabled())
        self.empty.cta.setToolTip(self.btn_walkin.toolTip())
        self.cls.clear()
        for bc in t.bow_classes:
            self.cls.addItem(bc.name, bc.id)
        self.fee.clear()
        self.fee.addItem("– keine –", None)
        for f in t.fees:
            self.fee.addItem(f"{f.name} ({money(f.amount)})", f.id)
        self._search(self.search.term())
        if self.isVisible() and not self.drawer.is_open():
            self.search.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        self.search.setFocus()
        self.search.selectAll()

    def _search(self, term: str):
        if self.tournament is None:
            return
        results = ps.search_for_checkin(self.tournament.id, term)
        self._results = {p.id: p for p in results}
        self.table.set_rows([[p.start_number, f"{p.archer.last_name}, {p.archer.first_name}",
                              p.archer.club,
                              (p.bow_class.abbreviation or p.bow_class.name)
                              if p.bow_class else "",
                              Cell(p.registration_status,
                                   chip=registration_chip(p.registration_status)),
                              Cell(p.payment_status, chip=payment_chip(p.payment_status))]
                             for p in results], [p.id for p in results])
        if len(results) == 1 or (results and term):
            self.table.select_ids([results[0].id])
        self.not_found.setText("" if results or not term else f"„{term}“ nicht gefunden.")
        self.not_found.setVisible(bool(self.not_found.text()))
        self._on_selection(self.table.selected_ids())

    def _selected(self):
        return self._results.get(self.table.selected_id())

    def _on_selection(self, _ids):
        p = self._selected()
        enabled = self.tournament is not None and self.tournament.phase in CHECKIN_PHASES
        checked_in = p is not None and p.registration_status == "checked_in"
        self.btn_checkin.setEnabled(p is not None and enabled)
        self.btn_checkin.setText("Auschecken" if checked_in else "Einchecken")
        self.payment_warning.setVisible(p is not None and p.payment_status != "paid")

    # ------------------------------------------------------------ actions
    def _enter(self):
        if self.btn_checkin.isEnabled():
            self.checkin_selected()

    def checkin_selected(self):
        p = self._selected()
        if p is None or not self.btn_checkin.isEnabled():
            return
        undo = p.registration_status == "checked_in"
        try:
            if undo:
                ps.set_registration_status(p.id, "confirmed")
            else:
                ps.checkin(p.id)
        except Exception as exc:
            show_error(self, exc)
            return
        if undo:
            Toast.show(self, f"{p.archer.first_name} {p.archer.last_name} ausgecheckt",
                       Toast.SUCCESS)
        else:
            unpaid = p.payment_status != "paid"
            Toast.show(self, f"{p.archer.first_name} {p.archer.last_name} eingecheckt"
                       + (f" – {PAYMENT_WARNING}" if unpaid else ""),
                       Toast.WARNING if unpaid else Toast.SUCCESS)
        self.search.clear()
        context.notify()
        self.set_tournament(ts.get_tournament(self.tournament.id))
        self.search.setFocus()

    def open_walk_in(self):
        if not self.btn_walkin.isEnabled() or not self.drawer.request_close():
            return
        term = self.search.term()
        first, _, last = term.partition(" ") if term and not term.isdigit() else ("", "", "")
        self.form.set_values({"first_name": first, "last_name": last,
                              "bow_class_id": self.cls.itemData(0)})
        self.drawer.open("Walk-in erfassen")

    def _save_walk_in(self):
        if not self.form.validate():
            return
        v = self.form.values()
        try:
            p = ps.register_walk_in(self.tournament.id,
                                    {"first_name": v["first_name"], "last_name": v["last_name"],
                                     "club": v["club"]},
                                    v["bow_class_id"], v["entry_fee_id"], v["paid"])
        except Exception as exc:
            show_error(self, exc, "Walk-in konnte nicht erfasst werden")
            return
        self.drawer.mark_saved()
        Toast.show(self, f"{v['first_name']} {v['last_name']} erfasst und eingecheckt "
                         f"(Startnummer {p.start_number})", Toast.SUCCESS)
        self.search.clear()
        context.notify()
        self.set_tournament(ts.get_tournament(self.tournament.id))

    # global shortcuts
    def shortcut_find(self):
        self.search.setFocus()
        self.search.selectAll()

    def shortcut_new(self):
        self.open_walk_in()

    def shortcut_save(self):
        if self.drawer.is_open():
            self._save_walk_in()

    def close_drawer(self) -> bool:
        return self.drawer.request_close()

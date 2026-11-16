# -*- coding: utf-8 -*-
"""Preisverwaltung: Preise je Turnier anlegen, Platz und Klasse zuordnen, Preis-PDF drucken."""
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QLineEdit, QPlainTextEdit, QSpinBox

from bowtally.services import master_data_service as md
from bowtally.services import prize_service as ps
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Platz", "Name", "Bogenklasse", "Wert", "Beschreibung"]


class PrizeDialog(RecordDialog):
    _default_size = (560, 400)

    def __init__(self, record=None, tournament_id=None, parent=None):
        self._record = record
        self._tournament_id = tournament_id or context.tournament_id
        super().__init__("Neuer Preis" if record is None else "Preis bearbeiten", parent=parent)
        if record:
            self._class_combo.setCurrentIndex(
                next((i for i in range(self._class_combo.count())
                      if self._class_combo.itemData(i) == record.bow_class_id), 0))
            self.form.set_values({
                "rank": record.rank,
                "name": record.name,
                "description": record.description or "",
                "value": record.value or 0.0,
            })
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        rank_spin = QSpinBox()
        rank_spin.setRange(1, 999)
        val_spin = QDoubleSpinBox()
        val_spin.setRange(0, 9999)
        val_spin.setDecimals(2)
        val_spin.setSuffix(" €")
        val_spin.setSpecialValueText("–")
        desc = QPlainTextEdit()
        desc.setMinimumHeight(50)
        self._class_combo = QComboBox()
        self._class_combo.addItem("Alle Klassen", None)
        t_id = self._tournament_id
        if t_id:
            t = ts.get_tournament(t_id)
            for bc in (t.bow_classes if t else md.list_bow_classes()):
                self._class_combo.addItem(bc.name, bc.id)
        self.form.add("rank", "Platz", rank_spin, required=True)
        self.form.add("name", "Bezeichnung", QLineEdit(), required=True,
                      hint="z. B. Goldmedaille, Pokal, Gutschein")
        self.form.add("value", "Wert", val_spin)
        self.form.add("description", "Beschreibung", desc)
        self._body_layout.addWidget(self._class_combo)

    def _do_save(self) -> bool:
        vals = self.form.values()
        data = {
            "rank": int(vals["rank"]),
            "name": vals["name"],
            "description": vals["description"],
            "value": float(vals["value"]) if vals.get("value") else None,
            "bow_class_id": self._class_combo.currentData(),
        }
        try:
            p = ps.save_prize(data, self._record.id if self._record else None,
                              self._tournament_id)
        except Exception as exc:
            show_error(self, exc, "Preis konnte nicht gespeichert werden")
            return False
        self.saved_id = p.id
        return True


class PrizesView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("target", "Noch keine Preise",
                           "Lege Preise für die Siegerehrung an.", "Neuer Preis")
        super().__init__("Preise", HEADERS, empty,
                         search_placeholder="Bezeichnung oder Klasse …", parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self._btn_new = button("Neuer Preis", self.new_item, "primary",
                               "Neuen Preis anlegen (Strg+N)")
        self.header.add(self._btn_new,
                        button("Preis- und Siegerliste", self._print_prize_list,
                               tooltip="Preis- und Siegerliste als PDF drucken"))
        self.table.activated.connect(self.edit_item)
        self._prizes = {}

    def set_tournament(self, _t):
        self.refresh()

    def refresh(self):
        if not context.tournament_id:
            self.table.set_rows([], [])
            return
        prizes = ps.list_prizes(context.tournament_id)
        self._prizes = {p.id: p for p in prizes}
        self.table.set_rows([[
            p.rank,
            p.name,
            p.bow_class.name if p.bow_class else "Alle",
            Cell(p.value, text=f"{p.value:.2f} €".replace(".", ",") if p.value else "–"),
            p.description or "",
        ] for p in prizes], [p.id for p in prizes])
        n = len(prizes)
        self.header.set_subtitle(f"{n} Preis{'e' if n != 1 else ''}")
        self.on_selection(self.table.selected_ids())

    def on_selection(self, ids):
        p = self._prizes.get(self.table.selected_id())
        closed = self.tournament_closed
        self._btn_new.setEnabled(not closed)
        if p is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(p.name, [
            Action("Bearbeiten", self.edit_item, enabled=not closed),
            Action("Löschen", self.delete_item, "danger", enabled=not closed),
        ])

    def new_item(self):
        if not context.tournament_id or self.tournament_closed:
            return
        dlg = PrizeDialog(tournament_id=context.tournament_id, parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self):
        p = self._prizes.get(self.table.selected_id())
        if p is None or self.tournament_closed:
            return
        dlg = PrizeDialog(p, tournament_id=context.tournament_id, parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        p = self._prizes.get(self.table.selected_id())
        if p is None:
            return
        if not ConfirmDialog.ask(self, "Preis löschen?", p.name + " wird gelöscht."):
            return
        try:
            ps.delete_prize(p.id)
        except Exception as exc:
            show_error(self, exc, "Löschen fehlgeschlagen")
            return
        Toast.show(self, p.name + " gelöscht", Toast.SUCCESS)
        self.refresh()

    def context_entries(self, row_id):
        p = self._prizes.get(row_id)
        if p is None:
            return []
        closed = self.tournament_closed
        return [("Bearbeiten", self.edit_item, not closed),
                None,
                ("Löschen", self.delete_item, not closed)]

    def _print_prize_list(self):
        tid = context.tournament_id
        if not tid:
            return
        try:
            with busy():
                from bowtally.reports.prize_list import build_prize_list
                from bowtally.ui.dialogs.export_helper import open_path
                path = build_prize_list(tid)
            Toast.show(self, "Preis- und Siegerliste erstellt", Toast.SUCCESS,
                       ("Öffnen", lambda: open_path(self, path)))
        except Exception as exc:
            show_error(self, exc, "PDF konnte nicht erstellt werden")

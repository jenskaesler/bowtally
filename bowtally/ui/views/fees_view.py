# -*- coding: utf-8 -*-
"""Entry fees of the active tournament: drawer CRUD, delete protection, load templates."""
from PySide6.QtWidgets import QDoubleSpinBox, QLineEdit, QPlainTextEdit

from bowtally.services import tournament_service as ts
from bowtally.ui import button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import Form
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.views import ListView
from bowtally.ui.views.participants_view import money

HEADERS = ["Bezeichnung", "Betrag", "Teilnehmer", "Beschreibung"]
CLOSED_HINT = "Das Turnier ist abgeschlossen, Änderungen sind gesperrt."


class AmountField(QDoubleSpinBox):
    def __init__(self):
        super().__init__()
        self.setRange(0, 9999)
        self.setDecimals(2)
        self.setSuffix(" €")
        self.setSingleStep(1)

    def field_value(self):
        return self.value()

    def set_field_value(self, value):
        self.setValue(float(value or 0))


class FeesView(ListView):
    def __init__(self, parent=None):
        self.form = Form()
        self.form.add("name", "Bezeichnung", QLineEdit(), required=True)
        self.form.add("amount", "Betrag", AmountField(), required=True)
        desc = QPlainTextEdit()
        desc.setFixedHeight(70)
        self.form.add("description", "Beschreibung", desc)
        empty = EmptyState("file", "Keine Startgebühren",
                           "Lege Startgebühren an oder übernimm die Vorlagen.",
                           "Vorlagen laden")
        super().__init__("Startgebühren", HEADERS, empty, self.form, "Bezeichnung …")
        empty.actionTriggered.connect(self.load_templates)
        self.btn_templates = button("Vorlagen laden", self.load_templates,
                                    tooltip="Standard-Gebühren (Einstellungsvorlagen) kopieren")
        self.btn_new = button("Neue Gebühr", self.new_item, "primary",
                              "Neue Startgebühr anlegen (Strg+N)")
        self.header.add(self.btn_templates, self.btn_new)
        self.table.activated.connect(self.edit_item)
        self.tournament = None
        self._fees, self._usage = {}, {}
        self._editing_id = None

    def set_tournament(self, t):
        self.tournament = t
        self.refresh()

    def refresh(self):
        if self.tournament is None:
            return
        t = self.tournament = ts.get_tournament(self.tournament.id)
        fees = t.fees
        self._fees = {f.id: f for f in fees}
        self._usage = ts.fee_usage(t.id)
        self.table.set_rows([[f.name, Cell(f.amount, text=money(f.amount)),
                              self._usage.get(f.id, 0), f.description] for f in fees],
                            [f.id for f in fees])
        locked = t.status == "closed"
        for b in (self.btn_new, self.btn_templates):
            b.setEnabled(not locked)
        self.header.set_subtitle(f"{len(fees)} Gebühren · werden in der Ausschreibung und "
                                 "der Einnahmenübersicht verwendet")
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return self._fees.get(self.table.selected_id())

    def on_selection(self, ids):
        f = self._selected()
        if f is None:
            self.action_bar.set_actions("", [])
            return
        used = self._usage.get(f.id, 0)
        locked = self.tournament.status == "closed"
        self.action_bar.set_actions(f.name, [
            Action("Bearbeiten", self.edit_item, enabled=not locked,
                   tooltip=CLOSED_HINT if locked else "Im Seitenpanel bearbeiten"),
            Action("Löschen", self.delete_item, "danger", enabled=not used and not locked,
                   tooltip=f"Löschen nicht möglich: {used} Teilnehmern zugewiesen" if used
                   else CLOSED_HINT if locked else "Startgebühr löschen (mit Rückfrage)")])

    def context_entries(self, row_id):
        used = self._usage.get(row_id, 0)
        return [("Bearbeiten", self.edit_item),
                ("Löschen", self.delete_item, not used,
                 f"{used} Teilnehmern zugewiesen" if used else "")]

    def new_item(self):
        if self.tournament is None or not self.close_drawer():
            return
        self._editing_id = None
        self.form.set_values({"amount": 0})
        self.drawer.open("Neue Startgebühr")

    def edit_item(self, *_):
        f = self._selected()
        if f is None or not self.close_drawer():
            return
        self._editing_id = f.id
        self.form.set_values({"name": f.name, "amount": f.amount,
                              "description": f.description})
        self.drawer.open(f.name, read_only=self.tournament.status == "closed",
                         read_only_hint=CLOSED_HINT)

    def save_form(self):
        if not self.form.validate():
            return
        try:
            fee = ts.save_fee(self.tournament.id, self.form.values(), self._editing_id)
        except Exception as exc:
            show_error(self, exc, "Startgebühr konnte nicht gespeichert werden")
            return
        self.drawer.mark_saved()
        Toast.show(self, f"Startgebühr „{fee.name}“ gespeichert", Toast.SUCCESS)
        self.refresh()
        context.notify()

    def delete_item(self):
        f = self._selected()
        if f is None or not ConfirmDialog.ask(self, "Startgebühr löschen?",
                                              f"„{f.name}“ wird gelöscht."):
            return
        try:
            ts.delete_fee(f.id)
        except Exception as exc:
            show_error(self, exc)
            return
        Toast.show(self, f"Startgebühr „{f.name}“ gelöscht", Toast.SUCCESS)
        self.refresh()
        context.notify()

    def load_templates(self):
        if self.tournament is None:
            return
        if self._fees and not ConfirmDialog.ask(
                self, "Vorlagen laden?", "Es sind bereits Startgebühren vorhanden. Die Vorlagen "
                "werden zusätzlich angelegt.", "Vorlagen laden", destructive=False):
            return
        n = ts.load_fee_templates(self.tournament.id)
        Toast.show(self, f"{n} Vorlagen übernommen", Toast.SUCCESS)
        self.refresh()
        context.notify()

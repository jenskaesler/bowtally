# -*- coding: utf-8 -*-
"""Bow classes: drawer CRUD, clone, delete; order by drag and drop (sort_order persisted)."""
from PySide6.QtWidgets import QComboBox, QLineEdit, QPlainTextEdit

from bowtally.services import master_data_service as md
from bowtally.ui import button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import Form
from bowtally.ui.components.toast import Toast
from bowtally.ui.views import ListView

HEADERS = ["Bezeichnung", "Kürzel", "Altersgruppe", "Typ"]
AGE_GROUPS = ["Jugend", "Erwachsene", "Senioren", "Offen"]
READ_ONLY_HINT = "Schreibgeschützt. Klonen für anpassbare Kopie."


def builtin_chip(builtin: bool) -> Cell:
    return Cell(builtin, chip=("Eingebaut", "muted") if builtin
                else ("Benutzerdefiniert", "primary"))


class BowClassesView(ListView):
    def __init__(self, parent=None):
        self.form = Form()
        age = QComboBox()
        age.setEditable(True)
        age.addItems([""] + AGE_GROUPS)
        self.form.add("name", "Bezeichnung", QLineEdit(), required=True)
        self.form.add("abbreviation", "Kürzel", QLineEdit(), required=True,
                      hint="Kurzform für Tabellen und Ergebnislisten, z. B. RH")
        self.form.add("age_group", "Altersgruppe", age)
        desc = QPlainTextEdit()
        desc.setFixedHeight(90)
        self.form.add("description", "Beschreibung", desc)

        empty = EmptyState("layers", "Keine Bogenklassen",
                           "Lege eine Bogenklasse an, um Teilnehmer zuordnen zu können.",
                           "Neue Bogenklasse")
        super().__init__("Bogenklassen", HEADERS, empty, self.form,
                         "Bezeichnung oder Kürzel …", reorderable=True)
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neue Bogenklasse", self.new_item, "primary",
                               "Neue Bogenklasse anlegen (Strg+N)"))
        self.table.activated.connect(self.edit_item)
        self.table.reordered.connect(self._save_order)
        self._classes = {}
        self._editing_id = None

    def refresh(self):
        classes = md.list_bow_classes()
        self._classes = {bc.id: bc for bc in classes}
        self.table.set_rows([[Cell(bc.name, tooltip=READ_ONLY_HINT if bc.is_builtin else ""),
                              bc.abbreviation, bc.age_group, builtin_chip(bc.is_builtin)]
                             for bc in classes], [bc.id for bc in classes])
        custom = sum(not bc.is_builtin for bc in classes)
        self.header.set_subtitle(f"{len(classes)} Klassen | {custom} benutzerdefiniert | "
                                 "Reihenfolge per Drag-and-Drop")
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return self._classes.get(self.table.selected_id())

    def on_selection(self, ids):
        bc = self._selected()
        if bc is None:
            self.action_bar.set_actions("", [])
            return
        locked = bc.is_builtin
        self.action_bar.set_actions(bc.name, [
            Action("Bearbeiten", self.edit_item, enabled=not locked,
                   tooltip="Bearbeiten (eingebaute Einträge sind schreibgeschützt)" if locked
                   else "Im Seitenpanel bearbeiten"),
            Action("Klonen", self.clone_item, tooltip="Anpassbare Kopie anlegen"),
            Action("Löschen", self.delete_item, "danger", enabled=not locked,
                   tooltip="Löschen (eingebaute Einträge sind schreibgeschützt)" if locked
                   else "Bogenklasse löschen (mit Rückfrage)")])

    def context_entries(self, row_id):
        bc = self._classes.get(row_id)
        if bc is None:
            return []
        hint = "Eingebaute Einträge sind schreibgeschützt" if bc.is_builtin else ""
        return [("Bearbeiten", self.edit_item, not bc.is_builtin, hint),
                ("Klonen", self.clone_item),
                None,
                ("Löschen", self.delete_item, not bc.is_builtin, hint)]

    def new_item(self):
        if not self.close_drawer():
            return
        self._editing_id = None
        self.form.set_values({})
        self.drawer.open("Neue Bogenklasse")

    def edit_item(self, *_):
        bc = self._selected()
        if bc is None or not self.close_drawer():
            return
        self._editing_id = bc.id
        self.form.set_values({k: getattr(bc, k) for k in self.form.fields})
        self.drawer.open(bc.name, read_only=bc.is_builtin, read_only_hint=READ_ONLY_HINT)

    def save_form(self):
        if not self.form.validate():
            return
        try:
            bc = md.save_bow_class(self.form.values(), self._editing_id)
        except Exception as exc:
            show_error(self, exc, "Bogenklasse konnte nicht gespeichert werden")
            return
        self.drawer.mark_saved()
        Toast.show(self, f"Bogenklasse '{bc.name}' gespeichert", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([bc.id])

    def clone_item(self):
        bc = self._selected()
        if bc is None or not self.close_drawer():
            return
        clone = md.clone_bow_class(bc.id)
        Toast.show(self, f"Kopie '{clone.name}' angelegt", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([clone.id])
        self.edit_item()

    def delete_item(self):
        bc = self._selected()
        if bc is None or bc.is_builtin:
            return
        if not ConfirmDialog.ask(self, "Bogenklasse löschen?",
                                 f"'{bc.name}' wird endgültig gelöscht."):
            return
        try:
            md.delete_bow_class(bc.id)
        except Exception as exc:
            show_error(self, exc)
            return
        Toast.show(self, f"Bogenklasse '{bc.name}' gelöscht", Toast.SUCCESS)
        self.refresh()

    def _save_order(self, ids: list):
        md.reorder_bow_classes(ids)
        self.refresh()
        Toast.show(self, "Reihenfolge gespeichert", Toast.SUCCESS)

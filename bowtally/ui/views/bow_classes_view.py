# -*- coding: utf-8 -*-
"""Bow classes: modal CRUD, clone, delete; sortable columns (sort_order kept for other contexts)."""
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QWidget

from bowtally.io.importer import BOW_CLASS_IMPORT_FIELDS
from bowtally.services import master_data_service as md
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell, optional, optional_columns, optional_values
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.toast import Toast
from bowtally.ui.constants import SETTINGS_COMBO_W
from bowtally.ui.dialogs.export_helper import export_button
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Bezeichnung", "Kürzel", "Altersgruppe", "Typ"]
BOW_CLASS_OPTIONAL = [(optional("description", "Beschreibung"), lambda bc: bc.description)]
AGE_GROUPS = ["Jugend", "Erwachsene", "Senioren", "Offen"]
READ_ONLY_HINT = "Schreibgeschützt. Kopieren für anpassbare Kopie."


def builtin_chip(builtin: bool) -> Cell:
    return Cell(builtin, chip=("Standard", "muted") if builtin
                else ("Benutzerdefiniert", "primary"))


class BowClassDialog(RecordDialog):
    _default_size = (684, 448)

    def __init__(self, record=None, parent=None):
        self._record = record
        ro = bool(record and record.is_builtin)
        super().__init__(
            "Neue Bogenklasse" if record is None else "Bogenklasse bearbeiten",
            read_only=ro, read_only_hint=READ_ONLY_HINT if ro else "", parent=parent)
        if record:
            self.form.set_values({k: getattr(record, k) for k in self.form.fields})
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None
        self.saved_name: str = ""

    def _setup_form(self):
        age = QComboBox()
        age.setEditable(True)
        age.addItems([""] + AGE_GROUPS)
        desc = QPlainTextEdit()
        desc.setMinimumHeight(70)
        abbr = QLineEdit()
        self.form.add("name", "Bezeichnung", QLineEdit(), required=True)
        self.form.add("abbreviation", "Kürzel", abbr, required=True,
                      hint="Kurzform für Tabellen und Ergebnislisten, z. B. RH")
        abbr.setFixedWidth(SETTINGS_COMBO_W)
        self.form.add("age_group", "Altersgruppe", age)
        self.form.add("description", "Beschreibung", desc)

    def _do_save(self) -> bool:
        try:
            bc = md.save_bow_class(self.form.values(),
                                   self._record.id if self._record else None)
        except Exception as exc:
            show_error(self, exc, "Bogenklasse konnte nicht gespeichert werden")
            return False
        self.saved_id = bc.id
        self.saved_name = bc.name
        return True


class BowClassesView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("layers", "Keine Bogenklassen",
                           "Lege eine Bogenklasse an, um Teilnehmer zuordnen zu können.",
                           "Neue Bogenklasse")
        super().__init__("Bogenklassen", HEADERS + optional_columns(BOW_CLASS_OPTIONAL), empty,
                         search_placeholder="Bezeichnung oder Kürzel …")
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neue Bogenklasse", self.new_item, "primary",
                               "Neue Bogenklasse anlegen (Strg+N)"))
        self.table.activated.connect(self.edit_item)
        self._classes = {}
        self._show_mine = QCheckBox("Meine Bogenklassen anzeigen")
        _s = QSettings("BowTally", "BowTally")
        self._show_mine.setChecked(_s.value("bow_classes/show_mine", False, type=bool))
        self._show_mine.toggled.connect(self.refresh)
        self._show_mine.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("bow_classes/show_mine", v))
        _footer = QWidget()
        _fl = QHBoxLayout(_footer)
        _fl.setContentsMargins(0, 4, 0, 0)
        _fl.addWidget(self._show_mine)
        _fl.addStretch()
        _fl.addWidget(export_button(self, "bogenklassen", self._export_sheets))
        _fl.addWidget(button("Importieren", self._import,
                             tooltip="Bogenklassen aus CSV, Excel oder OpenDocument importieren"))
        self.main_layout.insertWidget(2, _footer)

    def refresh(self):
        classes = md.list_bow_classes()
        self._classes = {bc.id: bc for bc in classes}
        visible = ([bc for bc in classes if not bc.is_builtin]
                   if self._show_mine.isChecked() else classes)
        self.table.set_rows([[Cell(bc.name, tooltip=READ_ONLY_HINT if bc.is_builtin else ""),
                              bc.abbreviation, bc.age_group, builtin_chip(bc.is_builtin)]
                             + optional_values(BOW_CLASS_OPTIONAL, bc)
                             for bc in visible], [bc.id for bc in visible])
        custom = sum(not bc.is_builtin for bc in classes)
        self.header.set_subtitle(f"{len(classes)} Klassen | {custom} benutzerdefiniert")
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
                   tooltip="Bearbeiten (Standard-Einträge sind schreibgeschützt)" if locked
                   else "Bogenklasse bearbeiten"),
            Action("Kopieren", self.clone_item, tooltip="Anpassbare Kopie anlegen"),
            Action("Löschen", self.delete_item, "danger", enabled=not locked,
                   tooltip="Löschen (Standard-Einträge sind schreibgeschützt)" if locked
                   else "Bogenklasse löschen (mit Rückfrage)")])

    def context_entries(self, row_id):
        bc = self._classes.get(row_id)
        if bc is None:
            return []
        return [("Bearbeiten", self.edit_item, not bc.is_builtin),
                ("Kopieren", self.clone_item),
                None,
                ("Löschen", self.delete_item, not bc.is_builtin)]

    def new_item(self):
        dlg = BowClassDialog(parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"Bogenklasse '{dlg.saved_name}' gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self, *_):
        bc = self._selected()
        if bc is None:
            return
        dlg = BowClassDialog(record=bc, parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"Bogenklasse '{dlg.saved_name}' gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def clone_item(self):
        bc = self._selected()
        if bc is None:
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

    def _export_sheets(self, _filtered: bool):
        rows = [[bc.name, bc.abbreviation, bc.age_group, bc.description]
                for bc in self._classes.values()]
        return [("Bogenklassen", ["Bezeichnung", "Kürzel", "Altersgruppe", "Beschreibung"], rows)]

    def _import(self):
        res = run_import(self, BOW_CLASS_IMPORT_FIELDS, "Bogenklassen importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = md.import_bow_classes(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"Import abgeschlossen: {r['created']} neu, {r['updated']} "
                         f"aktualisiert, {r['skipped']} übersprungen", Toast.SUCCESS)
        self.refresh()


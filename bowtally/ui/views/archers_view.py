# -*- coding: utf-8 -*-
"""Archer master data: search, drawer CRUD, import / export, soft and hard delete."""
from PySide6.QtWidgets import QCheckBox, QComboBox, QCompleter, QLineEdit, QPlainTextEdit

from bowtally.io.importer import ARCHER_IMPORT_FIELDS
from bowtally.services import master_data_service as md
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog, choose
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import DateField, Form, email_validator
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.export_helper import export_button
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.views import ListView

HEADERS = ["Vorname", "Nachname", "Verein", "Klasse", "Mitgliedsnummer", "Status"]
EXPORT_HEADERS = ["Nachname", "Vorname", "Geburtsdatum", "Verein", "Mitgliedsnummer",
                  "Bogenklasse", "E-Mail", "Telefon", "Aktiv"]


class ArchersView(ListView):
    def __init__(self, parent=None):
        self.form = Form()
        self.club = QLineEdit()
        self.bow_class = QComboBox()
        f = self.form
        f.add("first_name", "Vorname", QLineEdit(), required=True)
        f.add("last_name", "Nachname", QLineEdit(), required=True)
        f.add("birth_date", "Geburtsdatum", DateField(), hint="Format TT.MM.JJJJ, optional")
        f.add("club", "Verein", self.club)
        f.add("member_number", "Mitgliedsnummer", QLineEdit())
        f.add("default_bow_class_id", "Standardklasse", self.bow_class)
        f.add("email", "E-Mail", QLineEdit(), validator=email_validator)
        f.add("phone", "Telefon", QLineEdit())
        notes = QPlainTextEdit()
        notes.setFixedHeight(80)
        f.add("notes", "Notizen", notes)
        f.add("active", "Aktiv", QCheckBox("Aktiv (in Auswahllisten sichtbar)"))

        empty = EmptyState("users", "Noch keine Schützen",
                           "Lege den ersten Schützen an oder importiere eine Mitgliederliste.",
                           "Neuer Schütze")
        super().__init__("Schützen", HEADERS, empty, self.form,
                         "Name, Verein oder Mitgliedsnummer …", multi_select=True)
        empty.actionTriggered.connect(self.new_item)
        self.header.add(
            export_button(self, "schuetzen", self._export_sheets,
                          lambda: len(self.table.visible_ids()) if self.table.is_filtered()
                          else None),
            button("Importieren", self._import,
                   tooltip="Schützen aus CSV, Excel oder OpenDocument importieren"),
            button("Neuer Schütze", self.new_item, "primary", "Neuen Schützen anlegen (Strg+N)"))
        self.table.activated.connect(self.edit_item)
        self._archers = {}
        self._editing_id = None

    # ------------------------------------------------------------ data
    def refresh(self):
        with busy():
            archers = md.list_archers(include_inactive=True)
            classes = md.list_bow_classes()
        self._archers = {a.id: a for a in archers}
        self.table.set_rows([[a.first_name, a.last_name, a.club,
                              a.default_bow_class.abbreviation or a.default_bow_class.name
                              if a.default_bow_class else None,
                              a.member_number,
                              Cell(a.active, chip=("Aktiv", "success") if a.active
                                   else ("Inaktiv", "neutral"))] for a in archers],
                            [a.id for a in archers])
        clubs = {a.club.strip().lower() for a in archers if a.club}
        active = sum(a.active for a in archers)
        self.header.set_subtitle(f"{len(archers)} Schützen | {active} aktiv | "
                                 f"{len(clubs)} Vereine")
        self.bow_class.clear()
        self.bow_class.addItem("(keine)", None)
        for bc in classes:
            self.bow_class.addItem(bc.name, bc.id)
        self.club.setCompleter(QCompleter(sorted({a.club for a in archers if a.club}), self))
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return [self._archers[i] for i in self.table.selected_ids() if i in self._archers]

    # ------------------------------------------------------------ actions
    def on_selection(self, ids):
        n = len(ids)
        if n == 0:
            actions = []
        elif n == 1:
            actions = [Action("Bearbeiten", self.edit_item, tooltip="Im Seitenpanel bearbeiten"),
                       Action("Löschen", self.delete_selected, "danger",
                              tooltip="Schützen löschen (mit Rückfrage)")]
        else:
            actions = [Action(f"{n} Schützen löschen", self.delete_selected, "danger",
                              tooltip="Alle ausgewählten Schützen löschen (mit Rückfrage)")]
        self.action_bar.set_actions(self.selection_info(n, "Schütze", "Schützen"), actions)

    def context_entries(self, row_id):
        a = self._archers.get(row_id)
        if a is None:
            return []
        return [("Bearbeiten", self.edit_item),
                ("Klasse ändern …", self.change_class),
                ("Als inaktiv markieren" if a.active else "Wieder aktivieren",
                 lambda: self.set_active(not a.active)),
                None,
                ("Löschen", self.delete_selected)]

    def new_item(self):
        if not self.close_drawer():
            return
        self._editing_id = None
        self.form.set_values({"active": True})
        self.drawer.open("Neuer Schütze")

    def edit_item(self, *_):
        sel = self._selected()
        if not sel or not self.close_drawer():
            return
        a = sel[0]
        self._editing_id = a.id
        self.form.set_values({k: getattr(a, k) for k in self.form.fields})
        self.drawer.open(f"{a.first_name} {a.last_name}")

    def save_form(self):
        if not self.form.validate():
            return
        try:
            with busy():
                archer = md.save_archer(self.form.values(), self._editing_id)
        except Exception as exc:
            show_error(self, exc, "Schütze konnte nicht gespeichert werden")
            return
        self.drawer.mark_saved()
        Toast.show(self, f"{archer.first_name} {archer.last_name} gespeichert", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([archer.id])

    def change_class(self):
        sel = self._selected()
        if not sel:
            return
        options = [("(keine)", None)] + [(bc.name, bc.id) for bc in md.list_bow_classes()]
        cid = choose(self, "Klasse ändern",
                     f"Standardklasse für {len(sel)} Schützen:" if len(sel) > 1
                     else f"Standardklasse für {sel[0].first_name} {sel[0].last_name}:",
                     options, sel[0].default_bow_class_id)
        if cid is choose.CANCELLED:
            return
        for a in sel:
            md.save_archer({"default_bow_class_id": cid}, a.id)
        Toast.show(self, "Klasse geändert", Toast.SUCCESS)
        self.refresh()

    def set_active(self, active: bool):
        sel = self._selected()
        for a in sel:
            md.set_archer_active(a.id, active)
        Toast.show(self, f"{len(sel)} Schützen {'aktiviert' if active else 'deaktiviert'}",
                   Toast.SUCCESS)
        self.refresh()

    def delete_selected(self):
        sel = self._selected()
        if not sel:
            return
        names = ", ".join(f"{a.first_name} {a.last_name}" for a in sel[:3]) + \
            (f" und {len(sel) - 3} weitere" if len(sel) > 3 else "")
        if not ConfirmDialog.ask(self, f"{len(sel)} Schützen löschen?" if len(sel) > 1
                                 else "Schützen löschen?",
                                 f"{names} wird endgültig gelöscht."):
            return
        with busy():
            blocked = [a for a in sel if md.archer_has_tournaments(a.id)]
            for a in sel:
                if a not in blocked:
                    md.delete_archer(a.id)
        deleted = len(sel) - len(blocked)
        if blocked and ConfirmDialog.ask(
                self, "Turnierdaten vorhanden",
                f"{len(blocked)} Schützen haben bereits an Turnieren teilgenommen und können "
                "nicht gelöscht werden, ohne Ergebnisse zu verlieren. Stattdessen als inaktiv "
                "markieren?", "Deaktivieren", destructive=False):
            for a in blocked:
                md.set_archer_active(a.id, False)
            Toast.show(self, f"{len(blocked)} Schützen deaktiviert", Toast.INFO)
        if deleted:
            Toast.show(self, f"{deleted} Schützen gelöscht", Toast.SUCCESS)
        self.refresh()

    # ------------------------------------------------------------ import / export
    def _import(self):
        res = run_import(self, ARCHER_IMPORT_FIELDS, "Schützen importieren")
        if res is None:
            return
        records, strategy = res
        try:
            with busy():
                r = md.import_archers(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        Toast.show(self, f"Import abgeschlossen: {r['created']} neu, {r['updated']} "
                         f"aktualisiert, {r['skipped']} übersprungen", Toast.SUCCESS)
        self.refresh()

    def _export_sheets(self, filtered: bool):
        ids = self.table.visible_ids() if filtered else list(self._archers)
        rows = []
        for i in ids:
            a = self._archers[i]
            rows.append([a.last_name, a.first_name, a.birth_date, a.club, a.member_number,
                         a.default_bow_class.name if a.default_bow_class else None, a.email,
                         a.phone, "Ja" if a.active else "Nein"])
        return [("Schützen", EXPORT_HEADERS, rows)]

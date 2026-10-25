# -*- coding: utf-8 -*-
"""Volunteer management for the active tournament: assign, edit, confirm, print, mailto."""
from PySide6.QtCore import Qt
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPlainTextEdit, QVBoxLayout,
                               QWidget)

from bowtally.services import helper_service as hs
from bowtally.services.settings_service import KEY_EMAIL_TPL_HELPER
from bowtally.ui import busy, button, show_error
from bowtally.ui.utils.mailto import open_mailto
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import Form, email_validator
from bowtally.ui.components.search_bar import SearchBar
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.views import ListView

HEADERS = ["Name", "Aufgabe", "Von", "Bis", "Bestätigt", "Telefon", "E-Mail"]


class _HelperPicker(QDialog):
    """Pick one or more helpers from the global master data to assign to a tournament."""

    def __init__(self, already_assigned_ids: set[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Helfer aus Stammdatei zuweisen")
        self.resize(500, 480)
        self.search = SearchBar("Name suchen …")
        self.list = QListWidget()
        helpers = hs.list_helpers()
        for h in helpers:
            text = f"{h.last_name}, {h.first_name}"
            details = " · ".join(x for x in (h.phone, h.email) if x)
            item = QListWidgetItem(f"{text}   {details}" if details else text)
            item.setData(Qt.ItemDataRole.UserRole, h.id)
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         f"{text} {h.email or ''} {h.phone or ''}".lower())
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self.search.searchChanged.connect(self._filter)
        self.list.itemActivated.connect(self._toggle)
        self.ok = button("Zuweisen (0)", self.accept, "primary",
                         "Ausgewählte Helfer dem Turnier zuweisen")
        self.list.itemChanged.connect(self._update_ok)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Abbrechen", self.reject, tooltip="Nichts zuweisen"))
        row.addWidget(self.ok)
        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addWidget(self.list, 1)
        lay.addLayout(row)
        self._update_ok()

    def _toggle(self, item):
        item.setCheckState(Qt.CheckState.Unchecked if item.checkState()
                           == Qt.CheckState.Checked else Qt.CheckState.Checked)

    def _filter(self, term: str):
        term = term.lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(term) and term not in item.data(Qt.ItemDataRole.UserRole + 1))

    def _update_ok(self, *_):
        n = len(self.selected_ids())
        self.ok.setText(f"Zuweisen ({n})")
        self.ok.setEnabled(n > 0)

    def selected_ids(self) -> list[int]:
        return [self.list.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]


class HelpersView(ListView):
    def __init__(self, parent=None):
        f = Form()
        f.add("first_name", "Vorname", QLineEdit(), required=True)
        f.add("last_name", "Nachname", QLineEdit(), required=True)
        f.add("phone", "Telefon", QLineEdit())
        f.add("email", "E-Mail", QLineEdit(), validator=email_validator)
        notes = QPlainTextEdit()
        notes.setFixedHeight(60)
        f.add("notes", "Notizen", notes)
        lbl = QLabel("Einsatz in diesem Turnier", objectName="fieldLabel")
        lbl.setContentsMargins(0, 8, 0, 0)
        f.add_widget(lbl)
        f.add("task", "Aufgabe", QLineEdit(),
              hint="z. B. Parcours-Aufbau, Einschreibung, Ergebnisse")
        f.add("time_from", "Zeit von", QLineEdit(), hint="z. B. 08:00")
        f.add("time_to", "Zeit bis", QLineEdit(), hint="z. B. 16:00")
        f.add("confirmed", "Bestätigt", QCheckBox("Bestätigung versendet"))
        self.form = f

        empty = EmptyState("users", "Keine Helfer zugewiesen",
                           "Lege neue Helfer an oder weise Helfer aus der Stammdatei zu.",
                           "Helfer anlegen")
        super().__init__("Helfer", HEADERS, empty, f, "Name oder Aufgabe …")
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Aus Stammdatei", self._pick_from_master,
                               tooltip="Helfer aus globaler Stammdatei zuweisen"))
        self.header.add(button("Neuer Helfer", self.new_item, "primary",
                               "Neuen Helfer anlegen und zuweisen (Strg+N)"))
        footer = QWidget()
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(0, 4, 0, 0)
        self._show_inactive = QCheckBox("Inaktive Helfer anzeigen")
        _s = QSettings("BowTally", "BowTally")
        self._show_inactive.setChecked(_s.value("helpers/show_inactive", False, type=bool))
        self._show_inactive.toggled.connect(self.refresh)
        self._show_inactive.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("helpers/show_inactive", v))
        fl.addWidget(self._show_inactive)
        fl.addStretch()
        fl.addWidget(button("Helferliste drucken", self._print_list,
                            tooltip="Helferliste als PDF erstellen"))
        self.main_layout.insertWidget(2, footer)
        self.table.activated.connect(self.edit_item)
        self._rows: dict[int, object] = {}
        self._editing_id: int | None = None

    # ---------------------------------------------------------------- data
    def refresh(self):
        tid = context.tournament_id
        if tid is None:
            self.table.set_rows([], [])
            self.header.set_subtitle("Kein Turnier geöffnet")
            return
        with busy():
            rows = hs.list_tournament_helpers(tid)
        if not self._show_inactive.isChecked():
            rows = [r for r in rows if r.helper.active]
        self._rows = {r.id: r for r in rows}
        self.table.set_rows([[
            f"{r.helper.last_name}, {r.helper.first_name}",
            r.task or "",
            r.time_from or "",
            r.time_to or "",
            Cell(r.confirmed, chip=("Ja", "success") if r.confirmed else ("Nein", "muted")),
            r.helper.phone or "",
            r.helper.email or "",
        ] for r in rows], [r.id for r in rows])
        confirmed = sum(1 for r in rows if r.confirmed)
        self.header.set_subtitle(f"{len(rows)} Helfer | {confirmed} bestätigt")
        self.on_selection(self.table.selected_ids())

    # ---------------------------------------------------------------- selection
    def on_selection(self, ids: list):
        n = len(ids)
        if n == 0:
            self.action_bar.set_actions("", [])
            return
        actions = [Action("Bearbeiten", self.edit_item,
                          tooltip="Im Seitenpanel bearbeiten")]
        if n == 1:
            th = self._rows.get(ids[0])
            if th and th.helper.email:
                actions.append(Action("Bestätigung senden", lambda: self._mailto(ids[0]),
                                      tooltip="E-Mail mit Bestätigungs-Vorlage öffnen"))
            actions.append(Action("Entfernen", self.delete_selected, "danger",
                                  tooltip="Helfer aus diesem Turnier entfernen"))
        else:
            actions.append(Action(f"{n} Helfer entfernen", self.delete_selected, "danger"))
        self.action_bar.set_actions(self.selection_info(n, "Helfer", "Helfer"), actions)

    def context_entries(self, row_id):
        th = self._rows.get(row_id)
        if th is None:
            return []
        entries = [("Bearbeiten", self.edit_item)]
        if th.helper.email:
            entries.append(("Bestätigung senden", lambda: self._mailto(row_id)))
        entries += [
            ("Als bestätigt markieren" if not th.confirmed else "Bestätigung zurücksetzen",
             lambda c=th.confirmed: self._toggle_confirmed(row_id, not c)),
            ("Als inaktiv markieren" if th.helper.active else "Wieder aktivieren",
             lambda a=th.helper.active: self._set_helper_active(row_id, not a)),
            None,
            ("Entfernen", self.delete_selected),
        ]
        return entries

    # ---------------------------------------------------------------- new / edit / save
    def new_item(self):
        if not self.close_drawer():
            return
        self._editing_id = None
        self.form.set_values({"confirmed": False})
        self.drawer.open("Neuer Helfer")

    def edit_item(self, *_):
        sel_ids = self.table.selected_ids()
        if not sel_ids or not self.close_drawer():
            return
        aid = sel_ids[0]
        th = self._rows.get(aid)
        if th is None:
            return
        self._editing_id = aid
        self.form.set_values({
            "first_name": th.helper.first_name,
            "last_name": th.helper.last_name,
            "phone": th.helper.phone,
            "email": th.helper.email,
            "notes": th.helper.notes,
            "task": th.task,
            "time_from": th.time_from,
            "time_to": th.time_to,
            "confirmed": th.confirmed,
        })
        self.drawer.open(f"{th.helper.first_name} {th.helper.last_name}")

    def save_form(self):
        if not self.form.validate():
            return
        tid = context.tournament_id
        if tid is None:
            return
        try:
            with busy():
                if self._editing_id is None:
                    th = hs.create_and_assign(tid, self.form.values())
                else:
                    th = hs.update_assignment(self._editing_id, self.form.values())
        except Exception as exc:
            show_error(self, exc, "Helfer konnte nicht gespeichert werden")
            return
        self.drawer.mark_saved()
        Toast.show(self, f"{th.helper.first_name} {th.helper.last_name} gespeichert",
                   Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([th.id])

    # ---------------------------------------------------------------- actions
    def delete_selected(self):
        ids = self.table.selected_ids()
        if not ids:
            return
        from bowtally.ui.components.confirm_dialog import ConfirmDialog
        names = ", ".join(f"{self._rows[i].helper.first_name} {self._rows[i].helper.last_name}"
                          for i in ids if i in self._rows)
        if not ConfirmDialog.ask(self, "Helfer entfernen?",
                                 f"{names}\n\nDer Einsatz wird aus diesem Turnier entfernt.",
                                 "Entfernen", destructive=True):
            return
        try:
            with busy():
                for aid in ids:
                    hs.remove_assignment(aid)
        except Exception as exc:
            show_error(self, exc, "Helfer konnte nicht entfernt werden")
            return
        Toast.show(self, f"{len(ids)} Helfer entfernt", Toast.SUCCESS)
        self.refresh()

    def _toggle_confirmed(self, assignment_id: int, confirmed: bool):
        try:
            hs.set_confirmed(assignment_id, confirmed)
        except Exception as exc:
            show_error(self, exc)
            return
        self.refresh()

    def _set_helper_active(self, assignment_id: int, active: bool):
        th = self._rows.get(assignment_id)
        if th is None:
            return
        try:
            hs.set_active(th.helper_id, active)
        except Exception as exc:
            show_error(self, exc)
            return
        self.refresh()

    def _pick_from_master(self):
        if not self.close_drawer():
            return
        tid = context.tournament_id
        if tid is None:
            return
        dlg = _HelperPicker(set(), self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        ids = dlg.selected_ids()
        if not ids:
            return
        try:
            with busy():
                added = [hs.assign_existing(tid, hid) for hid in ids]
        except Exception as exc:
            show_error(self, exc, "Helfer konnten nicht zugewiesen werden")
            return
        Toast.show(self, f"{len(added)} Helfer zugewiesen", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([a.id for a in added])

    def _print_list(self):
        tid = context.tournament_id
        if tid is None:
            return
        from bowtally.reports.helper_list import build_helper_list
        from bowtally.ui.dialogs.export_helper import open_path
        try:
            with busy():
                path = build_helper_list(tid)
        except Exception as exc:
            show_error(self, exc, "Helferliste konnte nicht erstellt werden")
            return
        Toast.show(self, "Helferliste erstellt", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, path)))

    def _mailto(self, assignment_id: int):
        th = self._rows.get(assignment_id)
        if th is None:
            return
        t = context.tournament()
        if t is None:
            return
        open_mailto(KEY_EMAIL_TPL_HELPER, th.helper.email, {
            "name": f"{th.helper.first_name} {th.helper.last_name}",
            "verein": "", "klasse": "",
            "turniername": t.name,
            "datum": f"{t.date:%d.%m.%Y}",
        }, self)

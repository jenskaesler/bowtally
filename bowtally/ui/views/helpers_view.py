# -*- coding: utf-8 -*-
"""Helpers of one tournament: members from the member register or manually entered persons."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QHBoxLayout, QLineEdit, QListWidget,
                               QListWidgetItem, QVBoxLayout)

from bowtally.services import helper_service as hs
from bowtally.services.settings_service import KEY_EMAIL_TPL_HELPER
from bowtally.ui import busy, button, show_error
from bowtally.ui.utils.mailto import open_mailto, tournament_ctx
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import TimeField, email_validator
from bowtally.ui.components.search_bar import SearchBar
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.dialogs.export_helper import export_button
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Name", "Aufgabe", "Von", "Bis", "Bestätigt", "Telefon", "E-Mail"]
LOCKED_HINT = ("Die Ergebnisliste ist erstellt oder das Turnier abgeschlossen – "
               "Helfer können nicht mehr geändert werden.")
NEW_TIP = "Neuen Helfer nur für dieses Turnier anlegen (Strg+N)"
PICK_TIP = "Helfer aus der Mitgliederkartei zuweisen"


class _MemberPicker(QDialog):
    """Pick one or more helpers from the member register to assign to a tournament."""

    def __init__(self, tournament_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Helfer aus Mitgliederkartei zuweisen")
        self.resize(500, 480)
        self.search = SearchBar("Name suchen …")
        self.list = QListWidget()
        for m in hs.list_assignable_members(tournament_id):
            details = " · ".join(x for x in (m.phone, m.email) if x)
            item = QListWidgetItem(f"{m.full_name}   {details}" if details else m.full_name)
            item.setData(Qt.ItemDataRole.UserRole, m.id)
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         f"{m.full_name} {m.email or ''} {m.phone or ''}".lower())
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


class HelperDialog(RecordDialog):
    """Create a manual helper or edit an assignment (member data stays read-only)."""
    _default_size = (698, 584)

    def __init__(self, record=None, tournament_id=None, parent=None):
        self._record = record
        self._tournament_id = tournament_id
        name = hs.display_contact(record)[0] if record else "Neuer Helfer"
        super().__init__(name, parent=parent)
        values: dict = {"confirmed": False}
        if record is not None:
            src = record.member or record
            values = {"first_name": src.first_name, "last_name": src.last_name,
                      "phone": src.phone, "email": src.email, "task": record.task,
                      "time_from": record.time_from, "time_to": record.time_to,
                      "confirmed": record.confirmed}
        self.form.set_values(values)
        if record is not None and record.member_id is not None:
            for key in ("first_name", "last_name", "phone", "email"):
                self.form.fields[key].set_read_only(True)
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None
        self.saved_name: str = ""

    def _setup_form(self):
        self.form.add("first_name", "Vorname", QLineEdit(), required=True)
        self.form.add("last_name", "Nachname", QLineEdit(), required=True)
        self.form.add("phone", "Telefon", QLineEdit(), short=True)
        self.form.add("email", "E-Mail", QLineEdit(), validator=email_validator)

        def _time_edit():
            return TimeField()
        self.form.add("task", "Aufgabe", QLineEdit(),
                      hint="z. B. Parcours-Aufbau, Einschreibung, Ergebnisse")
        self.form.add("time_from", "Zeit von", _time_edit())
        self.form.add("time_to", "Zeit bis", _time_edit())
        self.form.add("confirmed", "Bestätigt", QCheckBox("Bestätigung versendet"))

    def _do_save(self) -> bool:
        values = self.form.values()
        try:
            with busy():
                if self._record is None:
                    result = hs.create_manual(self._tournament_id, values)
                else:
                    result = hs.update_assignment(self._record.id, values)
            self.saved_id = result.id
            self.saved_name = hs.display_contact(result)[0]
        except Exception as exc:
            show_error(self, exc, "Helfer konnte nicht gespeichert werden")
            return False
        return True


class HelpersView(ListView):
    def __init__(self, tournament_mode: bool = True, parent=None):
        # tournament_mode only keeps the existing call signature; the view is tournament-only
        empty = EmptyState("users", "Keine Helfer",
                           "Weise Helfer aus der Mitgliederkartei zu oder lege einen neuen Helfer an.",
                           "Neuer Helfer")
        super().__init__("Helfer", HEADERS, empty, search_placeholder="Name oder Aufgabe …")
        empty.actionTriggered.connect(self.new_item)
        self._empty = empty
        self._locked = False

        # order in the header, left to right: search, export, print, from members, new helper
        self.header.add(export_button(self, "helfer", self._export_sheets,
                                      lambda: len(self.table.visible_ids())
                                      if self.table.is_filtered() else None))
        self.header.add(button("Helferliste drucken", self._print_list,
                              tooltip="Helferliste als PDF erstellen"))
        self.btn_pick = button("Aus Mitgliederkartei", self._pick_from_members,
                               tooltip=PICK_TIP)
        self.btn_new = button("Neuer Helfer", self.new_item, "primary", NEW_TIP)
        self.header.add(self.btn_pick)
        self.header.add(self.btn_new)
        self.table.activated.connect(self.edit_item)
        self._rows: dict[int, object] = {}

    @property
    def _tid(self):
        return context.tournament_id

    def set_tournament(self, _t):
        self.refresh()

    # ---------------------------------------------------------------- data
    def _apply_lock(self):
        """Helpers are frozen once the results list was created (like the score entry)."""
        from bowtally.services import tournament_service as ts
        t = context.tournament() if self._tid is not None else None
        self._locked = t is not None and ts.scoring_locked(t)
        for btn, tip in ((self.btn_new, NEW_TIP), (self.btn_pick, PICK_TIP)):
            btn.setEnabled(not self._locked)
            btn.setToolTip(LOCKED_HINT if self._locked else tip)
        self._empty.cta.setEnabled(not self._locked)
        self._empty.cta.setToolTip(LOCKED_HINT if self._locked else NEW_TIP)

    def refresh(self):
        self._apply_lock()
        tid = self._tid
        if tid is None:
            rows = []
        else:
            with busy():
                rows = hs.list_tournament_helpers(tid)
        self._rows = {r.id: r for r in rows}
        self.table.set_rows([self._table_row(r) for r in rows], [r.id for r in rows])
        confirmed = sum(1 for r in rows if r.confirmed)
        self.header.set_subtitle(f"{len(rows)} Helfer | {confirmed} bestätigt")
        self.on_selection(self.table.selected_ids())

    @staticmethod
    def _table_row(th) -> list:
        name, phone, email = hs.display_contact(th)
        return [name, th.task or "", th.time_from or "", th.time_to or "",
                Cell(th.confirmed, chip=("Ja", "success") if th.confirmed else ("Nein", "muted")),
                phone, email]

    # ---------------------------------------------------------------- selection
    def on_selection(self, ids: list):
        n = len(ids)
        if n == 0:
            self.action_bar.set_actions("", [])
            return
        locked = self._locked
        self.action_bar.set_actions(self.selection_info(n, "Helfer", "Helfer"), [
            Action("Bearbeiten", self.edit_item, enabled=not locked,
                   tooltip=LOCKED_HINT if locked else "Helfereinsatz bearbeiten"),
            Action(f"{n} Helfer entfernen" if n > 1 else "Entfernen",
                   self.delete_selected, "danger", enabled=not locked,
                   tooltip=LOCKED_HINT if locked else "")])

    def context_entries(self, row_id):
        th = self._rows.get(row_id)
        if th is None:
            return []
        if self._locked:
            return [("Bestätigung senden", lambda: self._mailto(row_id))]                 if hs.display_contact(th)[2] else []
        entries = [("Bearbeiten", self.edit_item)]
        if hs.display_contact(th)[2]:
            entries.append(("Bestätigung senden", lambda: self._mailto(row_id)))
        new_confirmed = not th.confirmed
        entries += [
            ("Als bestätigt markieren" if new_confirmed else "Bestätigung zurücksetzen",
             lambda: self._toggle_confirmed(row_id, new_confirmed)),
            None,
            ("Entfernen", self.delete_selected),
        ]
        return entries

    # ---------------------------------------------------------------- new / edit
    def new_item(self):
        if self._locked:
            return
        self._open_dialog(None)

    def edit_item(self, *_):
        if self._locked:
            return
        sel_ids = self.table.selected_ids()
        record = self._rows.get(sel_ids[0]) if sel_ids else None
        if record is not None:
            self._open_dialog(record)

    def _open_dialog(self, record):
        dlg = HelperDialog(record=record, tournament_id=self._tid, parent=self)
        if dlg.exec() and dlg.saved_id:
            Toast.show(self, f"{dlg.saved_name} gespeichert", Toast.SUCCESS)
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    # ---------------------------------------------------------------- actions
    def delete_selected(self):
        ids = self.table.selected_ids()
        if not ids or self._locked:
            return
        names = ", ".join(hs.display_contact(self._rows[i])[0] for i in ids if i in self._rows)
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

    def _pick_from_members(self):
        tid = self._tid
        if tid is None or self._locked:
            return
        dlg = _MemberPicker(tid, self)
        if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.selected_ids():
            return
        try:
            with busy():
                added = [hs.assign_member(tid, mid) for mid in dlg.selected_ids()]
        except Exception as exc:
            show_error(self, exc, "Helfer konnten nicht zugewiesen werden")
            return
        Toast.show(self, f"{len(added)} Helfer zugewiesen", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([a.id for a in added])

    def _print_list(self):
        tid = self._tid
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
        t = context.tournament()
        if th is None or t is None:
            return
        person = th.member or th
        open_mailto(KEY_EMAIL_TPL_HELPER, hs.display_contact(th)[2], {
            "name": f"{person.first_name} {person.last_name}",
            "turniername": t.name,
            "datum": f"{t.date:%d.%m.%Y}",
            "aufgabe": th.task or "",
            "von": th.time_from or "",
            "bis": th.time_to or "",
            **tournament_ctx(t),
        }, self)

    def _export_sheets(self, filtered: bool):
        ids = self.table.visible_ids() if filtered else list(self._rows)
        rows = []
        for i in ids:
            th = self._rows.get(i)
            if th:
                name, phone, email = hs.display_contact(th)
                rows.append([name, th.task, th.time_from, th.time_to,
                             "Ja" if th.confirmed else "Nein", phone, email])
        return [("Helfer", HEADERS, rows)]

# -*- coding: utf-8 -*-
"""Zeitplan-Verwaltung: start groups with times for the active tournament."""
from PySide6.QtWidgets import QLineEdit, QSpinBox

from bowtally.services import course_service as cs
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Gruppe", "Startzeit", "Dauer (min)", "Teilnehmer"]


class ScheduleGroupDialog(RecordDialog):
    _default_size = (520, 340)

    def __init__(self, record=None, parent=None):
        self._record = record
        super().__init__("Neue Gruppe" if record is None else "Gruppe bearbeiten", parent=parent)
        if record:
            self.form.set_values({
                "group_name": record.group_name,
                "start_time": record.start_time or "",
                "estimated_duration_min": record.estimated_duration_min or 0,
            })
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        dur = QSpinBox()
        dur.setRange(0, 600)
        dur.setSpecialValueText("–")
        dur.setSuffix(" min")
        time_edit = QLineEdit()
        time_edit.setPlaceholderText("HH:MM")
        self.form.add("group_name", "Gruppenname", QLineEdit(), required=True)
        self.form.add("start_time", "Startzeit", time_edit,
                      hint="Format HH:MM, z. B. 09:30")
        self.form.add("estimated_duration_min", "Geschätzte Dauer", dur)

    def _do_save(self) -> bool:
        vals = self.form.values()
        data = {
            "group_name": vals["group_name"],
            "start_time": vals["start_time"] or None,
            "estimated_duration_min": int(vals["estimated_duration_min"]) or None,
        }
        try:
            g = cs.save_group(data, self._record.id if self._record else None,
                              context.tournament_id)
        except Exception as exc:
            show_error(self, exc, "Gruppe konnte nicht gespeichert werden")
            return False
        self.saved_id = g.id
        return True


class ScheduleView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("target", "Noch keine Gruppen",
                           "Lege Startgruppen mit Zeiten an.", "Neue Gruppe")
        super().__init__("Zeitplan", HEADERS, empty,
                         search_placeholder="Gruppenname …", parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self._btn_new = button("Neue Gruppe", self.new_item, "primary",
                               "Neue Startgruppe anlegen (Strg+N)")
        self.header.add(self._btn_new,
                        button("Zeitplan drucken", self._print_schedule,
                               tooltip="Zeitplan-Aushang als PDF"))
        self.table.activated.connect(self.edit_item)
        self._groups = {}
        # participant start_group lookup for participant counts
        self._participant_counts: dict[str, int] = {}

    def set_tournament(self, _t):
        self.refresh()

    def refresh(self):
        if not context.tournament_id:
            self.table.set_rows([], [])
            return
        groups = cs.list_groups(context.tournament_id)
        self._groups = {g.id: g for g in groups}
        t = context.tournament()
        if t:
            self._participant_counts = {}
            for p in t.participants:
                if p.start_group:
                    self._participant_counts[p.start_group] = (
                        self._participant_counts.get(p.start_group, 0) + 1)
        self.table.set_rows([[
            g.group_name,
            g.start_time or "",
            g.estimated_duration_min or "",
            self._participant_counts.get(g.group_name, ""),
        ] for g in groups], [g.id for g in groups])
        n = len(groups)
        self.header.set_subtitle(f"{n} Gruppe{'n' if n != 1 else ''}"
                                 + (f" | Turnier: {t.name}" if t else ""))
        self.on_selection(self.table.selected_ids())

    def on_selection(self, ids):
        g = self._groups.get(self.table.selected_id())
        closed = self.tournament_closed
        self._btn_new.setEnabled(not closed)
        if g is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(g.group_name,
            [Action("Bearbeiten", self.edit_item, enabled=not closed),
             Action("Löschen", self.delete_item, "danger", enabled=not closed)])

    def new_item(self):
        if not context.tournament_id or self.tournament_closed:
            return
        dlg = ScheduleGroupDialog(parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self):
        g = self._groups.get(self.table.selected_id())
        if g is None or self.tournament_closed:
            return
        dlg = ScheduleGroupDialog(g, parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        g = self._groups.get(self.table.selected_id())
        if g is None:
            return
        if not ConfirmDialog.ask(self, "Gruppe löschen?", g.group_name + " wird gelöscht."):
            return
        try:
            cs.delete_group(g.id)
        except Exception as exc:
            show_error(self, exc, "Löschen fehlgeschlagen")
            return
        Toast.show(self, "Gruppe " + g.group_name + " gelöscht", Toast.SUCCESS)
        self.refresh()

    def context_entries(self, row_id):
        g = self._groups.get(row_id)
        if g is None:
            return []
        closed = self.tournament_closed
        return [("Bearbeiten", self.edit_item, not closed),
                None,
                ("Löschen", self.delete_item, not closed)]

    def _print_schedule(self):
        tid = context.tournament_id
        if not tid:
            return
        try:
            with busy():
                from bowtally.reports.course_plan import build_schedule_plan
                from bowtally.ui.dialogs.export_helper import open_path
                path = build_schedule_plan(tid)
            Toast.show(self, "Zeitplan erstellt", Toast.SUCCESS,
                       ("Öffnen", lambda: open_path(self, path)))
        except Exception as exc:
            show_error(self, exc, "PDF konnte nicht erstellt werden")

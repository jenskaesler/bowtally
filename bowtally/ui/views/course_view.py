# -*- coding: utf-8 -*-
"""Parcours-Planung: list of course targets for the active tournament, with drag-drop reorder."""
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QHBoxLayout, QLineEdit,
                               QPlainTextEdit, QPushButton, QSpinBox, QWidget)

from bowtally.services import course_service as cs
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.toast import Toast
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.confirm_dialog import choose
from bowtally.ui.context import context
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Nr.", "Tier / Scheibe", "Distanz (m)", "Pfeilstopp", "Gelände", "Max. Gruppe", "Helfernotiz"]
ARROW_STOPS = ["", "Klasse 1", "Klasse 2", "Klasse 3", "Klasse 4", "Klasse 5"]
TERRAIN_TYPES = ["", "Flach", "Hang", "Wald", "Wiese", "Wasser", "Hügel"]


class CourseTargetDialog(RecordDialog):
    _default_size = (600, 500)

    def __init__(self, record=None, parent=None):
        self._record = record
        super().__init__("Neue Scheibe" if record is None else "Scheibe bearbeiten", parent=parent)
        if record:
            self.form.set_values({
                "number": record.number,
                "animal_name": record.animal_name or "",
                "distance_m": record.distance_m or 0.0,
                "arrow_stop_class": record.arrow_stop_class or "",
                "terrain_type": record.terrain_type or "",
                "max_group_size": record.max_group_size or 0,
                "helper_note": record.helper_note or "",
            })
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        num = QSpinBox()
        num.setRange(1, 999)
        dist = QDoubleSpinBox()
        dist.setRange(0, 999)
        dist.setDecimals(1)
        dist.setSuffix(" m")
        arrow = QComboBox()
        arrow.setEditable(True)
        arrow.addItems(ARROW_STOPS)
        terrain = QComboBox()
        terrain.setEditable(True)
        terrain.addItems(TERRAIN_TYPES)
        grp = QSpinBox()
        grp.setRange(0, 20)
        grp.setSpecialValueText("–")
        note = QPlainTextEdit()
        note.setMinimumHeight(60)
        name_edit = QLineEdit()
        self._name_edit = name_edit
        inv_btn = QPushButton("Aus Inventar …")
        inv_btn.setToolTip("Bezeichnung aus aktivem Vereinsinventar übernehmen")
        inv_btn.clicked.connect(self._pick_from_inventory)
        self.form.add("number", "Scheiben-Nr.", num, required=True)
        self.form.add("animal_name", "Tier / Bezeichnung", name_edit)
        self.form.add_widget(inv_btn)
        self.form.add("distance_m", "Distanz", dist)
        self.form.add("arrow_stop_class", "Pfeilstoppklasse", arrow)
        self.form.add("terrain_type", "Geländetyp", terrain)
        self.form.add("max_group_size", "Max. Gruppengröße", grp)
        self.form.add("helper_note", "Helfernotiz", note)

    def _pick_from_inventory(self):
        from bowtally.services import inventory_service as inv
        items = inv.list_items(active_only=True)
        if not items:
            Toast.show(self, "Kein aktives Inventar vorhanden.", Toast.WARNING)
            return
        options = [(f"{i.name} ({inv.ITEM_TYPE_LABELS.get(i.item_type, '')})", i.name)
                   for i in items]
        result = choose(self, "Aus Inventar wählen", "Bezeichnung übernehmen:", options)
        if result is not choose.CANCELLED and result:
            self.form.set_values({"animal_name": result})

    def _do_save(self) -> bool:
        vals = self.form.values()
        data = {
            "number": int(vals["number"]),
            "animal_name": vals["animal_name"],
            "distance_m": float(vals["distance_m"]) or None,
            "arrow_stop_class": vals["arrow_stop_class"] or None,
            "terrain_type": vals["terrain_type"] or None,
            "max_group_size": int(vals["max_group_size"]) or None,
            "helper_note": vals["helper_note"],
        }
        try:
            t = cs.save_target(data, self._record.id if self._record else None,
                               context.tournament_id)
        except Exception as exc:
            show_error(self, exc, "Scheibe konnte nicht gespeichert werden")
            return False
        self.saved_id = t.id
        return True


class CourseView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("target", "Noch keine Scheiben",
                           "Lege Scheiben an, um den Parcours zu planen.", "Neue Scheibe")
        super().__init__("Parcours-Planung", HEADERS, empty,
                         search_placeholder="Tier, Pfeilstopp oder Gelände …",
                         reorderable=True, parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neue Scheibe", self.new_item, "primary",
                               "Neue Scheibe anlegen (Strg+N)"),
                        button("Aufbauplan", self._print_setup, tooltip="Aufbauplan mit Helfernotizen als PDF"),
                        button("Scheibenplan", self._print_layout, tooltip="Scheibenplan ohne Notizen als PDF"))
        self.table.activated.connect(self.edit_item)
        self.table.reordered.connect(self._save_order)
        self._targets = {}

    def set_tournament(self, _t):
        self.refresh()

    def refresh(self):
        if not context.tournament_id:
            self.table.set_rows([], [])
            return
        rows = cs.list_targets(context.tournament_id)
        self._targets = {r.id: r for r in rows}
        self.table.set_rows([[
            r.number,
            r.animal_name or "",
            f"{r.distance_m:.1f}" if r.distance_m else "",
            r.arrow_stop_class or "",
            r.terrain_type or "",
            r.max_group_size or "",
            Cell(r.helper_note or "", tooltip=r.helper_note or ""),
        ] for r in rows], [r.id for r in rows])
        t = context.tournament()
        n = len(rows)
        self.header.set_subtitle(f"{n} Scheibe{'n' if n != 1 else ''}"
                                 + (f" | Turnier: {t.name}" if t else ""))
        self.on_selection(self.table.selected_ids())

    def on_selection(self, ids):
        r = self._targets.get(self.table.selected_id())
        closed = context.tournament() and context.tournament().phase == "closed"
        if r is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(
            f"Scheibe {r.number}" + (f" – {r.animal_name}" if r.animal_name else ""),
            [Action("Bearbeiten", self.edit_item, enabled=not closed),
             Action("Löschen", self.delete_item, "danger", enabled=not closed)])

    def new_item(self):
        if not context.tournament_id:
            return
        max_num = max((r.number for r in self._targets.values()), default=0)
        dlg = CourseTargetDialog(parent=self)
        dlg.form.set_values({"number": max_num + 1})
        dlg._baseline = dlg.form.snapshot()
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self):
        r = self._targets.get(self.table.selected_id())
        if r is None:
            return
        dlg = CourseTargetDialog(r, parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        r = self._targets.get(self.table.selected_id())
        if r is None:
            return
        label = f"Scheibe {r.number}" + (f" – {r.animal_name}" if r.animal_name else "")
        if not ConfirmDialog.ask(self, "Scheibe löschen?", label + " wird gelöscht."):
            return
        try:
            cs.delete_target(r.id)
        except Exception as exc:
            show_error(self, exc, "Löschen fehlgeschlagen")
            return
        Toast.show(self, f"{label} gelöscht", Toast.SUCCESS)
        self.refresh()

    def context_entries(self, row_id):
        r = self._targets.get(row_id)
        if r is None:
            return []
        closed = context.tournament() and context.tournament().phase == "closed"
        return [("Bearbeiten", self.edit_item, not closed),
                None,
                ("Löschen", self.delete_item, not closed)]

    def _save_order(self, ordered_ids: list):
        if not context.tournament_id:
            return
        try:
            cs.reorder_targets(context.tournament_id, ordered_ids)
        except Exception as exc:
            show_error(self, exc, "Reihenfolge konnte nicht gespeichert werden")

    def _print_setup(self):
        self._print_pdf(with_notes=True)

    def _print_layout(self):
        self._print_pdf(with_notes=False)

    def _print_pdf(self, with_notes: bool):
        tid = context.tournament_id
        if not tid:
            return
        try:
            with busy():
                from bowtally.reports.course_plan import build_course_plan
                from bowtally.ui.dialogs.export_helper import open_path
                path = build_course_plan(tid, with_notes=with_notes)
            label = "Aufbauplan" if with_notes else "Scheibenplan"
            Toast.show(self, f"{label} erstellt", Toast.SUCCESS,
                       ("Öffnen", lambda: open_path(self, path)))
        except Exception as exc:
            show_error(self, exc, "PDF konnte nicht erstellt werden")

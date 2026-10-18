# -*- coding: utf-8 -*-
"""Scoring rules: drawer CRUD with zone editor, clone, delete. Builtin rules are read-only."""
import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QHeaderView, QLineEdit,
                               QPlainTextEdit, QSpinBox, QTableWidgetItem, QToolButton,
                               QVBoxLayout, QWidget)

from bowtally.services import scoring_service as sc
from bowtally.ui import button, show_error, theme
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import ROW_HEIGHT, Cell, ReorderTable
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import Form
from bowtally.ui.components.toast import Toast
from bowtally.ui.views import ListView
from bowtally.ui.views.bow_classes_view import READ_ONLY_HINT, builtin_chip

HEADERS = ["Bezeichnung", "Zonen", "Schüsse/Scheibe", "Nachschuss", "Typ"]
MAX_POINTS = 30
MAX_SHOTS = 3


def zone_summary(rule) -> str:
    return " / ".join(f"{z['zone']} {z['points']}" for z in rule.ring_values)


class ZoneEditor(QWidget):
    """Zone / points rows: inline editing, delete per row, drag handle to reorder."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zones: list[dict] = []
        self._read_only = False
        t = self.table = ReorderTable(0, 4)
        t.setHorizontalHeaderLabels(["", "Zone", "Punkte", ""])
        t.verticalHeader().hide()
        t.verticalHeader().setDefaultSectionSize(ROW_HEIGHT + 6)
        t.setShowGrid(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setDragEnabled(True)
        t.setAcceptDrops(True)
        t.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        t.setDropIndicatorShown(True)
        h = t.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c, w in ((0, 30), (2, 80), (3, 40)):
            h.setSectionResizeMode(c, QHeaderView.ResizeMode.Fixed)
            t.setColumnWidth(c, w)
        t.setMinimumHeight(240)
        t.rowsDropped.connect(self._on_drop)
        self.add_btn = button("Zone hinzufügen", self._add, tooltip="Neue Trefferzone anlegen")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(t)
        lay.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignLeft)

    # FormField protocol
    def field_value(self) -> list[dict]:
        return [dict(z) for z in self._zones]

    def set_field_value(self, zones) -> None:
        self._zones = [dict(z) for z in (zones or [])]
        self._rebuild()

    def setEnabled(self, enabled: bool) -> None:
        self._read_only = not enabled
        self.add_btn.setEnabled(enabled)
        self.table.setDragEnabled(enabled)
        self._rebuild()

    def _rebuild(self):
        t = self.table
        t.setRowCount(len(self._zones))
        muted = theme.current()["text2"]
        for r, z in enumerate(self._zones):
            grip = QTableWidgetItem()
            grip.setIcon(QIcon(theme.pixmap("grip", muted, 16)))
            grip.setToolTip("Ziehen, um die Reihenfolge zu ändern")
            grip.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                          | Qt.ItemFlag.ItemIsDragEnabled)
            t.setItem(r, 0, grip)
            name = QLineEdit(z["zone"])
            name.setPlaceholderText("Zonenname")
            name.setReadOnly(self._read_only)
            name.textChanged.connect(lambda text, i=r: self._set(i, "zone", text))
            t.setCellWidget(r, 1, name)
            pts = QSpinBox()
            pts.setRange(0, MAX_POINTS)
            pts.setValue(int(z["points"]))
            pts.setEnabled(not self._read_only)
            pts.valueChanged.connect(lambda v, i=r: self._set(i, "points", v))
            t.setCellWidget(r, 2, pts)
            delete = QToolButton(objectName="iconButton")
            delete.setIcon(QIcon(theme.pixmap("trash", theme.current()["accent"], 16)))
            delete.setToolTip("Zone löschen")
            delete.setEnabled(not self._read_only)
            delete.clicked.connect(lambda _=False, i=r: self._remove(i))
            t.setCellWidget(r, 3, delete)

    def _set(self, i, key, value):
        self._zones[i][key] = value.strip() if isinstance(value, str) else value
        self.changed.emit()

    def _add(self):
        self._zones.append({"zone": "", "points": 0})
        self._rebuild()
        self.table.cellWidget(len(self._zones) - 1, 1).setFocus()
        self.changed.emit()

    def _remove(self, i):
        del self._zones[i]
        self._rebuild()
        self.changed.emit()

    def _on_drop(self, rows: list, target: int):
        if self._read_only or not rows:
            return
        moving = self._zones.pop(rows[0])
        self._zones.insert(target if target <= rows[0] else target - 1, moving)
        self._rebuild()
        self.changed.emit()


def _zones_validator(zones) -> str | None:
    if not zones:
        return "Mindestens eine Zone ist erforderlich"
    names = [z["zone"].strip() for z in zones]
    if any(not n for n in names):
        return "Jede Zone braucht einen Namen"
    dup = {n for n in names if names.count(n) > 1}
    return f"Zone '{dup.pop()}' ist doppelt vorhanden" if dup else None


def _json_validator(text) -> str | None:
    try:
        value = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        return f"Kein gültiges JSON (Zeile {exc.lineno}, Spalte {exc.colno})"
    return None if isinstance(value, dict) else "Sonderregeln müssen ein JSON-Objekt sein"


class RulesView(ListView):
    def __init__(self, parent=None):
        self.form = Form()
        f = self.form
        f.add("name", "Bezeichnung", QLineEdit(), required=True)
        desc = QPlainTextEdit()
        desc.setFixedHeight(64)
        f.add("description", "Beschreibung", desc)
        shots = QSpinBox()
        shots.setRange(1, MAX_SHOTS)
        f.add("max_shots_per_target", "Max. Schüsse pro Scheibe", shots)
        f.add("allow_retry_shot", "Nachschuss", QCheckBox("Nachschuss erlaubt"))
        f.add("ring_values", "Zonen und Punkte", ZoneEditor(), required=True,
              validator=_zones_validator,
              required_message="Mindestens eine Zone ist erforderlich")
        rules = QPlainTextEdit()
        rules.setFixedHeight(80)
        f.add("rules_json", "Sonderregeln (JSON, optional)", rules, validator=_json_validator)

        empty = EmptyState("rules", "Keine Regelwerke",
                           "Lege ein Regelwerk mit Zonen und Punktwerten an.", "Neues Regelwerk")
        super().__init__("Regelwerke", HEADERS, empty, self.form, "Bezeichnung oder Zone …")
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neues Regelwerk", self.new_item, "primary",
                               "Neues Regelwerk anlegen (Strg+N)"))
        self.table.activated.connect(self.edit_item)
        self._rules = {}
        self._editing_id = None

    def refresh(self):
        rules = sc.list_rules()
        self._rules = {r.id: r for r in rules}
        self.table.set_rows([[Cell(r.name, tooltip=READ_ONLY_HINT if r.is_builtin else ""),
                              zone_summary(r), r.max_shots_per_target, r.allow_retry_shot,
                              builtin_chip(r.is_builtin)] for r in rules],
                            [r.id for r in rules])
        custom = sum(not r.is_builtin for r in rules)
        self.header.set_subtitle(f"{len(rules)} Regelwerke | {custom} benutzerdefiniert")
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return self._rules.get(self.table.selected_id())

    def on_selection(self, ids):
        r = self._selected()
        if r is None:
            self.action_bar.set_actions("", [])
            return
        locked = r.is_builtin
        self.action_bar.set_actions(r.name, [
            Action("Bearbeiten", self.edit_item, enabled=not locked,
                   tooltip="Bearbeiten (eingebaute Einträge sind schreibgeschützt)" if locked
                   else "Im Seitenpanel bearbeiten"),
            Action("Klonen", self.clone_item, tooltip="Anpassbare Kopie anlegen"),
            Action("Löschen", self.delete_item, "danger", enabled=not locked,
                   tooltip="Löschen (eingebaute Einträge sind schreibgeschützt)" if locked
                   else "Regelwerk löschen (mit Rückfrage)")])

    def context_entries(self, row_id):
        r = self._rules.get(row_id)
        if r is None:
            return []
        hint = "Eingebaute Einträge sind schreibgeschützt" if r.is_builtin else ""
        return [("Bearbeiten", self.edit_item, not r.is_builtin, hint),
                ("Klonen", self.clone_item),
                None,
                ("Löschen", self.delete_item, not r.is_builtin, hint)]

    def new_item(self):
        if not self.close_drawer():
            return
        self._editing_id = None
        self.form.set_values({"max_shots_per_target": 1,
                              "ring_values": [{"zone": "Miss", "points": 0}],
                              "rules_json": '{\n  "tiebreak": "most_top_scores"\n}'})
        self.drawer.open("Neues Regelwerk")

    def edit_item(self, *_):
        r = self._selected()
        if r is None or not self.close_drawer():
            return
        self._editing_id = r.id
        values = {k: getattr(r, k) for k in self.form.fields}
        values["rules_json"] = json.dumps(r.rules_json or {}, ensure_ascii=False, indent=2)
        self.form.set_values(values)
        self.drawer.open(r.name, read_only=r.is_builtin, read_only_hint=READ_ONLY_HINT)

    def save_form(self):
        if not self.form.validate():
            return
        data = self.form.values()
        data["rules_json"] = json.loads(data["rules_json"] or "{}")
        try:
            rule = sc.save_rule(data, self._editing_id)
        except Exception as exc:
            show_error(self, exc, "Regelwerk konnte nicht gespeichert werden")
            return
        self.drawer.mark_saved()
        Toast.show(self, f"Regelwerk '{rule.name}' gespeichert", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([rule.id])

    def clone_item(self):
        r = self._selected()
        if r is None or not self.close_drawer():
            return
        clone = sc.clone_rule(r.id)
        Toast.show(self, f"Kopie '{clone.name}' angelegt", Toast.SUCCESS)
        self.refresh()
        self.table.select_ids([clone.id])
        self.edit_item()

    def delete_item(self):
        r = self._selected()
        if r is None or r.is_builtin:
            return
        if not ConfirmDialog.ask(self, "Regelwerk löschen?",
                                 f"'{r.name}' wird endgültig gelöscht."):
            return
        try:
            sc.delete_rule(r.id)
        except Exception as exc:
            show_error(self, exc)
            return
        Toast.show(self, f"Regelwerk '{r.name}' gelöscht", Toast.SUCCESS)
        self.refresh()

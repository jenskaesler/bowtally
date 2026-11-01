# -*- coding: utf-8 -*-
"""Wertungszettel-Vorlagen: global erreichbar, Erstellen/Bearbeiten/Löschen, Spalten-Editor."""
import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
                               QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
                               QSpinBox, QSplitter, QVBoxLayout, QWidget)

from bowtally.services import score_sheet_service as sss
from bowtally.ui import button, show_error, theme
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Name", "Typ", "Spalten"]
TYPE_ITEMS = list(sss.TYPE_LABELS.items())    # [(key, label), ...]
READ_ONLY_HINT = "Eingebaut – Kopieren erzeugt eine bearbeitbare Vorlage."


class ColumnEditorDialog(QDialog):
    """Editor for column_config: list of {name, type, width_mm}."""
    _COL_TYPES = [("number", "Zahl"), ("text", "Text"), ("checkbox", "Checkbox")]

    def __init__(self, columns: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Spalten bearbeiten")
        self.resize(560, 420)
        self._cols = [dict(c) for c in columns]
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.currentRowChanged.connect(self._load_row)
        self._name_edit = QLineEdit()
        self._type_combo = QComboBox()
        for key, label in self._COL_TYPES:
            self._type_combo.addItem(label, key)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(6, 80)
        self._width_spin.setSuffix(" mm")
        form_lay = QVBoxLayout()
        for label, widget in [("Name:", self._name_edit), ("Typ:", self._type_combo),
                               ("Breite:", self._width_spin)]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(60)
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            form_lay.addLayout(row)
        form_lay.addStretch()
        form_widget = QWidget()
        form_widget.setLayout(form_lay)
        btn_row = QHBoxLayout()
        btn_row.addWidget(button("+ Spalte", self._add))
        btn_row.addWidget(button("Löschen", self._delete, "danger"))
        btn_row.addWidget(button("↑", self._move_up))
        btn_row.addWidget(button("↓", self._move_down))
        btn_row.addStretch()
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.addWidget(self._list, 1)
        left_lay.addLayout(btn_row)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(form_widget)
        splitter.setSizes([260, 260])
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._commit_and_accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(splitter, 1)
        lay.addWidget(buttons)
        self._rebuild_list()

    def _rebuild_list(self):
        muted = theme.current()["text2"]
        self._list.blockSignals(True)
        self._list.clear()
        for c in self._cols:
            item = QListWidgetItem(f"{c['name']}  ({c.get('width_mm', 14)} mm)")
            item.setIcon(QIcon(theme.pixmap("grip", muted, 16)))
            self._list.addItem(item)
        self._list.blockSignals(False)
        if self._cols:
            self._list.setCurrentRow(0)
            self._load_row(0)

    def _load_row(self, row: int):
        if row < 0 or row >= len(self._cols):
            return
        c = self._cols[row]
        self._name_edit.setText(c.get("name", ""))
        idx = next((i for i, (k, _) in enumerate(self._COL_TYPES) if k == c.get("type", "number")), 0)
        self._type_combo.setCurrentIndex(idx)
        self._width_spin.setValue(c.get("width_mm", 14))

    def _save_row(self):
        row = self._list.currentRow()
        if row < 0 or row >= len(self._cols):
            return
        self._cols[row] = {
            "name": self._name_edit.text(),
            "type": self._type_combo.currentData(),
            "width_mm": self._width_spin.value(),
        }

    def _add(self):
        self._save_row()
        self._cols.append({"name": "Neu", "type": "number", "width_mm": 14})
        self._rebuild_list()
        self._list.setCurrentRow(len(self._cols) - 1)

    def _delete(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._cols):
            self._cols.pop(row)
            self._rebuild_list()

    def _move_up(self):
        self._save_row()
        row = self._list.currentRow()
        if row > 0:
            self._cols[row - 1], self._cols[row] = self._cols[row], self._cols[row - 1]
            self._rebuild_list()
            self._list.setCurrentRow(row - 1)

    def _move_down(self):
        self._save_row()
        row = self._list.currentRow()
        if row < len(self._cols) - 1:
            self._cols[row], self._cols[row + 1] = self._cols[row + 1], self._cols[row]
            self._rebuild_list()
            self._list.setCurrentRow(row + 1)

    def _commit_and_accept(self):
        self._save_row()
        self.accept()

    def result_columns(self) -> list[dict]:
        return self._cols


class ScoreSheetTemplateDialog(RecordDialog):
    _default_size = (620, 400)

    def __init__(self, record=None, parent=None):
        self._record = record
        ro = bool(record and record.is_builtin)
        super().__init__(
            "Neue Vorlage" if record is None else "Vorlage bearbeiten",
            read_only=ro, read_only_hint=READ_ONLY_HINT if ro else "", parent=parent)
        self._columns: list[dict] = []
        if record:
            self._columns = sss.columns(record)
            type_key = record.tournament_type or "custom"
            idx = next((i for i, (k, _) in enumerate(TYPE_ITEMS) if k == type_key), 0)
            self._type_combo.setCurrentIndex(idx)
            self.form.set_values({"name": record.name})
            self._update_col_label()
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        self._type_combo = QComboBox()
        for key, label in TYPE_ITEMS:
            self._type_combo.addItem(label, key)
        self.form.add("name", "Bezeichnung", QLineEdit(), required=True)
        self.form.add("tournament_type", "Typ", self._type_combo)
        self._col_label = QLabel()
        self._col_btn = button("Spalten bearbeiten", self._edit_columns)
        row = QHBoxLayout()
        row.addWidget(self._col_label)
        row.addWidget(self._col_btn)
        row.addStretch()
        col_widget = QWidget()
        col_widget.setLayout(row)
        self._body_layout.addWidget(col_widget)

    def _update_col_label(self):
        n = len(self._columns)
        self._col_label.setText(f"{n} Spalte{'n' if n != 1 else ''}")

    def _edit_columns(self):
        dlg = ColumnEditorDialog(self._columns, self)
        if dlg.exec():
            self._columns = dlg.result_columns()
            self._update_col_label()

    def _do_save(self) -> bool:
        vals = self.form.values()
        data = {
            "name": vals["name"],
            "tournament_type": self._type_combo.currentData(),
            "column_config": self._columns,
        }
        try:
            t = sss.save_template(data, self._record.id if self._record else None)
        except Exception as exc:
            show_error(self, exc, "Vorlage konnte nicht gespeichert werden")
            return False
        self.saved_id = t.id
        return True


class ScoreSheetsView(ListView):
    def __init__(self, parent=None):
        empty = EmptyState("file", "Keine Vorlagen",
                           "Lege eine Wertungszettel-Vorlage an.", "Neue Vorlage")
        super().__init__("Wertungszettel-Vorlagen", HEADERS, empty,
                         search_placeholder="Name oder Typ …", parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neue Vorlage", self.new_item, "primary",
                               "Neue Vorlage anlegen (Strg+N)"))
        self.table.activated.connect(self.edit_item)
        self._templates = {}

    def refresh(self):
        rows = sss.list_templates()
        self._templates = {r.id: r for r in rows}
        self.table.set_rows([[
            Cell(r.name, bold=r.is_builtin),
            sss.TYPE_LABELS.get(r.tournament_type, r.tournament_type),
            Cell(len(sss.columns(r)), text=f"{len(sss.columns(r))} Spalten"),
        ] for r in rows], [r.id for r in rows])
        n = len(rows)
        self.header.set_subtitle(f"{n} Vorlage{'n' if n != 1 else ''}")
        self.on_selection(self.table.selected_ids())

    def on_selection(self, ids):
        r = self._templates.get(self.table.selected_id())
        if r is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(r.name, [
            Action("Bearbeiten" if not r.is_builtin else "Anzeigen", self.edit_item),
            Action("Kopieren", self.clone_item),
            Action("Löschen", self.delete_item, "danger", enabled=not r.is_builtin),
        ])

    def new_item(self):
        dlg = ScoreSheetTemplateDialog(parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def edit_item(self):
        r = self._templates.get(self.table.selected_id())
        if r is None:
            return
        dlg = ScoreSheetTemplateDialog(r, parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def clone_item(self):
        r = self._templates.get(self.table.selected_id())
        if r is None:
            return
        copy = ScoreSheetTemplate_copy(r)
        dlg = ScoreSheetTemplateDialog(copy, parent=self)
        if dlg.exec():
            self.refresh()
            self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        r = self._templates.get(self.table.selected_id())
        if r is None or r.is_builtin:
            return
        if not ConfirmDialog.ask(self, "Vorlage löschen?", r.name + " wird gelöscht."):
            return
        try:
            sss.delete_template(r.id)
        except Exception as exc:
            show_error(self, exc, "Löschen fehlgeschlagen")
            return
        Toast.show(self, r.name + " gelöscht", Toast.SUCCESS)
        self.refresh()

    def context_entries(self, row_id):
        r = self._templates.get(row_id)
        if r is None:
            return []
        return [("Bearbeiten", self.edit_item),
                ("Kopieren", self.clone_item),
                None,
                ("Löschen", self.delete_item, not r.is_builtin)]


class ScoreSheetTemplate_copy:
    """Lightweight proxy so RecordDialog sees a non-builtin copy to edit."""
    def __init__(self, src):
        self.id = None
        self.name = src.name + " (Kopie)"
        self.tournament_type = src.tournament_type
        self.is_builtin = False
        self.column_config = src.column_config
        self.header_fields = src.header_fields

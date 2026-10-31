# -*- coding: utf-8 -*-
"""Vereinsinventar: Scheiben und 3D-Ziele verwalten."""
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLineEdit,
                                QPlainTextEdit, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from bowtally.services import inventory_service as inv
from bowtally.ui import button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.views import ListView

HEADERS = ["Bezeichnung", "Hersteller", "Anzahl", "Zustand", "Aktiv"]
CONDITIONS = [("", ""), ("Gut", "gut"), ("Mittel", "mittel"), ("Schlecht", "schlecht")]
ITEM_TYPES = [("Scheibe", "target_face"), ("3D-Ziel", "3d_target")]


class InventoryItemDialog(RecordDialog):
    _default_size = (520, 380)

    def __init__(self, item_type: str, record=None, parent=None):
        self._record = record
        self._item_type = item_type
        type_label = inv.ITEM_TYPE_LABELS.get(item_type, item_type)
        super().__init__(
            f"Neue {type_label}" if record is None else f"{type_label} bearbeiten",
            parent=parent)
        if record:
            self.form.set_values({
                "name": record.name,
                "manufacturer": record.manufacturer or "",
                "quantity": record.quantity,
                "condition": record.condition or "",
                "notes": record.notes or "",
                "active": record.active,
            })
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        qty = QSpinBox()
        qty.setRange(1, 9999)
        cond = QComboBox()
        for label, val in CONDITIONS:
            cond.addItem(label, val)
        notes = QPlainTextEdit()
        notes.setMinimumHeight(60)
        active = QCheckBox("Aktiv")
        active.setChecked(True)
        self.form.add("name", "Bezeichnung", QLineEdit(), required=True)
        self.form.add("manufacturer", "Hersteller", QLineEdit())
        self.form.add("quantity", "Anzahl", qty)
        self.form.add("condition", "Zustand", cond)
        self.form.add("notes", "Notizen", notes)
        self.form.add("active", "Status", active)

    def _do_save(self) -> bool:
        vals = self.form.values()
        data = {
            "name": vals["name"],
            "item_type": self._item_type,
            "manufacturer": vals["manufacturer"] or None,
            "quantity": int(vals["quantity"]),
            "condition": vals["condition"] or None,
            "notes": vals["notes"] or None,
            "active": bool(vals["active"]),
        }
        try:
            item = inv.save_item(data, self._record.id if self._record else None)
        except Exception as exc:
            show_error(self, exc, "Inventareintrag konnte nicht gespeichert werden")
            return False
        self.saved_id = item.id
        return True


class _InventoryTab(ListView):
    def __init__(self, item_type: str, parent=None):
        self._item_type = item_type
        type_label = inv.ITEM_TYPE_LABELS.get(item_type, item_type)
        empty = EmptyState("inventory", f"Kein {type_label} vorhanden",
                           f"Lege {type_label}n an, um das Inventar zu verwalten.",
                           f"Neu")
        super().__init__(f"Inventar – {type_label}n", HEADERS, empty,
                         search_placeholder="Bezeichnung oder Hersteller …", parent=parent)
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button(f"Neuer Eintrag", self.new_item, "primary"))
        self.table.activated.connect(self.edit_item)
        self._items: dict = {}

    def refresh(self):
        items = inv.list_items(item_type=self._item_type)
        self._items = {i.id: i for i in items}
        self.table.set_rows([[
            i.name,
            i.manufacturer or "",
            i.quantity,
            inv.CONDITION_LABELS.get(i.condition or "", ""),
            "Ja" if i.active else "Nein",
        ] for i in items], [i.id for i in items])
        self.header.set_subtitle(f"{len(items)} Einträge")
        self.on_selection(self.table.selected_ids())

    def on_selection(self, ids):
        item = self._items.get(self.table.selected_id())
        if item is None:
            self.action_bar.set_actions("", [])
            return
        self.action_bar.set_actions(item.name, [
            Action("Bearbeiten", self.edit_item),
            Action("Löschen", self.delete_item, "danger"),
        ])

    def new_item(self):
        dlg = InventoryItemDialog(self._item_type, parent=self)
        if dlg.exec():
            self.refresh()
            if dlg.saved_id:
                self.table.select_ids([dlg.saved_id])

    def edit_item(self, *_):
        item = self._items.get(self.table.selected_id())
        if item is None:
            return
        dlg = InventoryItemDialog(self._item_type, item, parent=self)
        if dlg.exec():
            self.refresh()
            if dlg.saved_id:
                self.table.select_ids([dlg.saved_id])

    def delete_item(self):
        item = self._items.get(self.table.selected_id())
        if item is None:
            return
        if not ConfirmDialog.ask(self, "Eintrag löschen?", f"'{item.name}' wird gelöscht."):
            return
        try:
            inv.delete_item(item.id)
        except Exception as exc:
            show_error(self, exc, "Löschen fehlgeschlagen")
            return
        Toast.show(self, f"'{item.name}' gelöscht", Toast.SUCCESS)
        self.refresh()

    def context_entries(self, row_id):
        item = self._items.get(row_id)
        if item is None:
            return []
        return [("Bearbeiten", self.edit_item, True), None, ("Löschen", self.delete_item, True)]

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()


class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tab_faces = _InventoryTab("target_face")
        self._tab_3d = _InventoryTab("3d_target")
        tabs = QTabWidget()
        tabs.addTab(self._tab_faces, "Scheiben")
        tabs.addTab(self._tab_3d, "3D-Ziele")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(tabs)

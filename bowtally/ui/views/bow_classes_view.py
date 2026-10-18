# -*- coding: utf-8 -*-
"""Bow classes: CRUD, clone, drag-and-drop ordering (sort_order is persisted)."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from bowtally.services import master_data_service as md
from bowtally.ui import button, confirm, show_error
from bowtally.ui.dialogs.bow_class_dialog import BowClassDialog
from bowtally.ui.views import page_title

HEADERS = ["Name", "Abkürzung", "Altersgruppe", "Eingebaut", "Beschreibung"]


class _ReorderTree(QTreeWidget):
    """Flat list whose rows can be reordered by drag and drop."""
    reordered = Signal()

    def __init__(self):
        super().__init__()
        self.setRootIsDecorated(False)
        self.setAlternatingRowColors(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.reordered.emit()


class BowClassesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tree = _ReorderTree()
        self.tree.setHeaderLabels(HEADERS)
        self.tree.itemDoubleClicked.connect(lambda *_: self._edit())
        self.tree.reordered.connect(self._save_order)

        bar = QHBoxLayout()
        bar.addWidget(button("Neu", self._new, "primary"))
        bar.addWidget(button("Bearbeiten", self._edit))
        bar.addWidget(button("Klonen", self._clone))
        bar.addWidget(button("Löschen", self._delete, "danger"))
        bar.addStretch()
        hint = QLabel("Reihenfolge per Drag-and-Drop ändern.")
        hint.setProperty("secondary", True)

        lay = QVBoxLayout(self)
        lay.addWidget(page_title("Bogenklassen"))
        lay.addLayout(bar)
        lay.addWidget(self.tree, 1)
        lay.addWidget(hint)
        self._classes = {}

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        self.tree.clear()
        classes = md.list_bow_classes()
        self._classes = {bc.id: bc for bc in classes}
        for bc in classes:
            item = QTreeWidgetItem([bc.name, bc.abbreviation or "", bc.age_group or "",
                                    "Ja" if bc.is_builtin else "", bc.description or ""])
            item.setData(0, Qt.ItemDataRole.UserRole, bc.id)
            # no ItemIsDropEnabled -> items cannot be nested
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                          | Qt.ItemFlag.ItemIsDragEnabled)
            self.tree.addTopLevelItem(item)
        for c in range(len(HEADERS)):
            self.tree.resizeColumnToContents(c)

    def _selected(self):
        item = self.tree.currentItem()
        return self._classes.get(item.data(0, Qt.ItemDataRole.UserRole)) if item else None

    def _save_order(self):
        ids = [self.tree.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole)
               for i in range(self.tree.topLevelItemCount())]
        md.reorder_bow_classes(ids)

    def _new(self):
        if BowClassDialog(parent=self).exec():
            self.refresh()

    def _edit(self):
        bc = self._selected()
        if bc and BowClassDialog(bc, self).exec():
            self.refresh()

    def _clone(self):
        bc = self._selected()
        if bc is None:
            return
        clone = md.clone_bow_class(bc.id)
        self.refresh()
        if BowClassDialog(clone, self).exec():
            self.refresh()

    def _delete(self):
        bc = self._selected()
        if bc is None or not confirm(self, f"Bogenklasse '{bc.name}' löschen?"):
            return
        try:
            md.delete_bow_class(bc.id)
        except Exception as exc:
            show_error(self, exc)
        self.refresh()

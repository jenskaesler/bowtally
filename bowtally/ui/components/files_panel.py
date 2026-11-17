# -*- coding: utf-8 -*-
"""File list with add / open / remove buttons for the "Dokumente" tab of a record dialog."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from bowtally.ui import busy, button, show_error
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import ROW_HEIGHT
from bowtally.ui.dialogs.export_helper import open_path


def _size_text(size: int | None) -> str:
    if size is None:
        return "–"
    return f"{size / 1024:.0f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"


class FilesPanel(QWidget):
    """Without an owner_id (record not saved yet) only a hint is shown and `table` is None."""

    def __init__(self, owner_id, subject: str, list_fn, add_fn, remove_fn, path_fn,
                 hints_fn=None, parent=None):
        super().__init__(parent)
        self._owner_id, self._subject, self._hints = owner_id, subject, hints_fn
        self._list, self._add, self._remove, self._path = list_fn, add_fn, remove_fn, path_fn
        self.table = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        if owner_id is None:
            lay.addWidget(QLabel("Dateien können nach dem ersten Speichern hinzugefügt werden.",
                                 objectName="pageSubtitle"))
            lay.addStretch()
            return
        self.table = t = QTableWidget(0, 3)
        t.setHorizontalHeaderLabels(["Datei", "Größe", "Hinzugefügt"])
        t.verticalHeader().hide()
        t.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        t.setMinimumHeight(140)
        t.setShowGrid(False)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        t.setColumnWidth(0, 300)
        t.itemSelectionChanged.connect(self._update_buttons)
        t.itemDoubleClicked.connect(lambda _item: self.open_file())
        self._btn_open = button("Öffnen", self.open_file)
        self._btn_remove = button("Entfernen", self.remove_file)
        buttons = QHBoxLayout()
        buttons.addWidget(button("Datei hinzufügen …", self.add_files,
                                 tooltip="Dateien in den Datenordner von BowTally kopieren"))
        buttons.addWidget(self._btn_open)
        buttons.addWidget(self._btn_remove)
        buttons.addStretch()
        lay.addWidget(t, 1)
        lay.addLayout(buttons)
        self.reload()

    def reload(self):
        self._files = {f.id: f for f in self._list(self._owner_id)}
        hints = self._hints(self._owner_id) if self._hints else {}
        t = self.table
        t.setRowCount(len(self._files))
        for row, stored in enumerate(self._files.values()):
            added = f"{stored.added_at:%d.%m.%Y}" if stored.added_at else "–"
            for col, text in enumerate([stored.filename, _size_text(stored.size_bytes), added]):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, stored.id)
                item.setToolTip(hints.get(stored.id, ""))
                t.setItem(row, col, item)
        self._update_buttons()

    def _selected(self):
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return self._files[item.data(Qt.ItemDataRole.UserRole)] if item else None

    def _update_buttons(self):
        for btn in (self._btn_open, self._btn_remove):
            btn.setEnabled(self._selected() is not None)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, f"Dateien zum {self._subject} hinzufügen")
        try:
            with busy():
                for path in paths:
                    self._add(self._owner_id, Path(path))
        except Exception as exc:
            show_error(self, exc, "Datei konnte nicht hinzugefügt werden")
        self.reload()

    def open_file(self):
        stored = self._selected()
        if stored is not None:
            open_path(self, self._path(stored))

    def remove_file(self):
        stored = self._selected()
        if stored is None or not ConfirmDialog.ask(
                self, "Datei entfernen?", f"„{stored.filename}“ wird endgültig gelöscht."):
            return
        try:
            self._remove(stored.id)
        except Exception as exc:
            show_error(self, exc, "Datei konnte nicht entfernt werden")
        self.reload()

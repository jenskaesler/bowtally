# -*- coding: utf-8 -*-
"""Generic import dialog: column mapping, preview, validation report, duplicate strategy."""
from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QPlainTextEdit, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from bowtally.io import importer
from bowtally.services import ValidationError
from bowtally.ui import show_error
from bowtally.ui.components.data_table import display

UNMAPPED = "(nicht zuordnen)"


class ImportDialog(QDialog):
    def __init__(self, path: str, headers: list[str], rows: list[list],
                 fields: list[importer.ImportField], title: str, parent=None,
                 extra_check=None):
        """extra_check(records, strategy) -> error text or None (blocks the import)."""
        super().__init__(parent)
        self.extra_check = extra_check
        self.setWindowTitle(title)
        self.resize(900, 700)
        self.headers, self.rows, self.fields = headers, rows, fields
        self.records: list[dict] = []

        info = QLabel(f"Datei: {Path(path).name} · {len(rows)} Datenzeilen")
        info.setProperty("secondary", True)

        map_box = QGroupBox("Spalten-Zuordnung")
        form = QFormLayout(map_box)
        auto = importer.auto_mapping(headers, fields)
        self.combos: dict[str, QComboBox] = {}
        for f in fields:
            cb = QComboBox()
            cb.addItems([UNMAPPED] + headers)
            if auto.get(f.key) is not None:
                cb.setCurrentIndex(auto[f.key] + 1)
            cb.currentIndexChanged.connect(self._update)
            self.combos[f.key] = cb
            form.addRow(f.label + (" *" if f.required else ""), cb)

        prev_box = QGroupBox(f"Vorschau (erste {importer.PREVIEW_ROWS} Zeilen)")
        self.preview = QTableWidget()
        QVBoxLayout(prev_box).addWidget(self.preview)

        val_box = QGroupBox("Validierung")
        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setFixedHeight(110)
        QVBoxLayout(val_box).addWidget(self.report)

        self.strategy = QComboBox()
        for key, label in importer.DUPLICATE_STRATEGIES.items():
            self.strategy.addItem(label, key)
        self.strategy.currentIndexChanged.connect(self._update)
        strat_row = QHBoxLayout()
        strat_row.addWidget(QLabel("Duplikate:"))
        strat_row.addWidget(self.strategy)
        strat_row.addStretch()

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                        | QDialogButtonBox.StandardButton.Cancel)
        self.ok = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        self.ok.setText("Importieren")
        self.ok.setProperty("primary", True)
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        top = QHBoxLayout()
        top.addWidget(map_box, 1)
        right = QWidget()
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.addWidget(val_box)
        r_lay.addLayout(strat_row)
        r_lay.addStretch()
        top.addWidget(right, 1)

        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addLayout(top)
        lay.addWidget(prev_box, 1)
        lay.addWidget(self.buttons)
        self._update()

    def mapping(self) -> dict[str, int | None]:
        return {k: (cb.currentIndex() - 1 if cb.currentIndex() > 0 else None)
                for k, cb in self.combos.items()}

    def duplicate_strategy(self) -> str:
        return self.strategy.currentData()

    def _update(self):
        mapping = self.mapping()
        mapped = [f for f in self.fields if mapping[f.key] is not None]
        self.preview.clear()
        self.preview.setColumnCount(len(mapped))
        self.preview.setHorizontalHeaderLabels([f.label for f in mapped])
        sample = self.rows[:importer.PREVIEW_ROWS]
        self.preview.setRowCount(len(sample))
        for r, row in enumerate(sample):
            for c, f in enumerate(mapped):
                self.preview.setItem(r, c, QTableWidgetItem(display(row[mapping[f.key]])))
        self.preview.resizeColumnsToContents()

        missing = importer.missing_required(mapping, self.fields)
        if missing:
            self.records = []
            self.report.setPlainText("Pflichtfelder nicht zugeordnet: " + ", ".join(missing))
            self.ok.setEnabled(False)
            return
        self.records, errors = importer.convert_rows(self.rows, mapping, self.fields)
        lines = [f"{len(self.records)} gültige Zeilen, {len(errors)} fehlerhaft"
                 + (" (werden übersprungen)." if errors else ".")] + errors
        blocker = self.extra_check(self.records, self.duplicate_strategy()) \
            if self.extra_check and self.records else None
        if blocker:
            lines.insert(0, f"FEHLER: {blocker}. Import nicht möglich.")
        self.report.setPlainText("\n".join(lines))
        self.ok.setEnabled(bool(self.records) and not blocker)


def run_import(parent, fields, title: str, extra_check=None):
    """File dialog + mapping dialog. Returns (records, strategy) or None if cancelled."""
    path, _ = QFileDialog.getOpenFileName(parent, title, "", importer.FILE_FILTER)
    if not path:
        return None
    try:
        headers, rows = importer.read_table(path)
    except Exception as exc:
        show_error(parent, exc, "Datei konnte nicht gelesen werden")
        return None
    if not headers:
        show_error(parent, ValidationError("Die Datei enthält keine Daten."))
        return None
    dlg = ImportDialog(path, headers, rows, fields, title, parent, extra_check)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.records, dlg.duplicate_strategy()

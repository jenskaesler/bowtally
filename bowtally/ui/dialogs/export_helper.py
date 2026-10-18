# -*- coding: utf-8 -*-
"""Shared export flow: format dropdown, file dialog, write, success toast with 'Öffnen'."""
from typing import Callable

from PySide6.QtWidgets import QFileDialog, QMenu, QPushButton

from bowtally.io import exporter
from bowtally.ui import busy, button, show_error
from bowtally.ui.components.toast import Toast

FORMATS = [("Excel (.xlsx)", "Excel (*.xlsx)", ".xlsx"),
           ("OpenDocument (.ods)", "OpenDocument (*.ods)", ".ods"),
           ("CSV (.csv)", "CSV (*.csv)", ".csv")]


def export_button(parent, default_stem: str, sheets: Callable[[bool], list],
                  filtered_count: Callable[[], int | None] = lambda: None,
                  text: str = "Exportieren") -> QPushButton:
    """sheets(filtered) -> [(name, headers, rows)]. filtered_count() -> N if a filter is active."""
    btn = button(text, tooltip="Als CSV, Excel oder OpenDocument exportieren")
    m = QMenu(btn)

    def rebuild():
        m.clear()
        n = filtered_count()
        groups = [(False, "Alle Datensätze")] + ([(True, f"Nur gefilterte ({n})")] if n else [])
        for filtered, title in groups:
            if len(groups) > 1:
                m.addSection(title)
            for label, flt, ext in FORMATS:
                m.addAction(label).triggered.connect(
                    lambda _=False, f=filtered, fl=flt, e=ext: run_export(
                        parent, default_stem + e, fl, sheets(f)))

    m.aboutToShow.connect(rebuild)
    btn.setMenu(m)
    return btn


def run_export(parent, default_name: str, file_filter: str, sheets: list) -> None:
    path, _ = QFileDialog.getSaveFileName(parent, "Exportieren", default_name, file_filter)
    if not path:
        return
    path = exporter.ensure_suffix(path, file_filter)
    try:
        with busy():
            written = exporter.write_sheets(path, sheets)
    except Exception as exc:
        show_error(parent, exc, "Export fehlgeschlagen")
        return
    extra = f" (+{len(written) - 1} weitere Dateien)" if len(written) > 1 else ""
    Toast.show(parent, f"Exportiert: {written[0].name}{extra}", Toast.SUCCESS,
               ("Öffnen", lambda: open_path(parent, written[0])))


def open_path(parent, path) -> None:
    try:
        exporter.open_file(path)
    except OSError as exc:
        show_error(parent, exc, "Datei konnte nicht geöffnet werden")

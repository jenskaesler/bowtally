# -*- coding: utf-8 -*-
"""Shared export flow: file dialog with format filter, write, offer to open."""
from PySide6.QtWidgets import QFileDialog

from bowtally.io import exporter
from bowtally.ui import confirm, show_error


def run_export(parent, default_name: str, sheets: list) -> None:
    path, selected = QFileDialog.getSaveFileName(parent, "Exportieren", default_name,
                                                 exporter.FILE_FILTER)
    if not path:
        return
    path = exporter.ensure_suffix(path, selected)
    try:
        written = exporter.write_sheets(path, sheets)
    except Exception as exc:
        show_error(parent, exc, "Export fehlgeschlagen")
        return
    files = "\n".join(str(p) for p in written)
    if confirm(parent, f"Export erfolgreich:\n{files}\n\nDatei jetzt öffnen?", "Export"):
        try:
            exporter.open_file(written[0])
        except OSError as exc:
            show_error(parent, exc, "Datei konnte nicht geöffnet werden")

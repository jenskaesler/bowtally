# -*- coding: utf-8 -*-
"""Archer master data: list, search, CRUD (soft delete), import and export."""
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from bowtally.io.importer import ARCHER_IMPORT_FIELDS
from bowtally.services import master_data_service as md
from bowtally.ui import button, confirm, show_error
from bowtally.ui.dialogs.archer_dialog import ArcherDialog
from bowtally.ui.dialogs.export_helper import run_export
from bowtally.ui.dialogs.import_dialog import run_import
from bowtally.ui.views import page_title
from bowtally.ui.widgets.sortable_table import SortableTable

HEADERS = ["Nachname", "Vorname", "Geburtsdatum", "Verein", "Mitgliedsnr.", "Bogenklasse",
           "E-Mail", "Telefon", "Aktiv"]


class ArchersView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = SortableTable(HEADERS)
        self.table.search.setPlaceholderText("Suche nach Name, Verein, Mitgliedsnummer ...")
        self.table.activated.connect(lambda _id: self._edit())
        self.table.selectionChanged.connect(self._update_buttons)
        self.show_inactive = QCheckBox("Inaktive anzeigen")
        self.show_inactive.toggled.connect(self.refresh)

        self.btn_toggle = button("Deaktivieren", self._toggle_active, "danger")
        bar = QHBoxLayout()
        bar.addWidget(button("Neu", self._new, "primary"))
        bar.addWidget(button("Bearbeiten", self._edit))
        bar.addWidget(self.btn_toggle)
        bar.addStretch()
        bar.addWidget(self.show_inactive)
        bar.addWidget(button("Import ...", self._import))
        bar.addWidget(button("Export ...", self._export))

        lay = QVBoxLayout(self)
        lay.addWidget(page_title("Schützen"))
        lay.addLayout(bar)
        lay.addWidget(self.table, 1)
        self._archers = {}

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        archers = md.list_archers(include_inactive=self.show_inactive.isChecked())
        self._archers = {a.id: a for a in archers}
        self.table.set_rows([[a.last_name, a.first_name, a.birth_date, a.club,
                              a.member_number,
                              a.default_bow_class.name if a.default_bow_class else None,
                              a.email, a.phone, a.active] for a in archers],
                            [a.id for a in archers])
        self._update_buttons()

    def _update_buttons(self):
        a = self._archers.get(self.table.selected_id())
        self.btn_toggle.setText("Reaktivieren" if a and not a.active else "Deaktivieren")
        self.btn_toggle.setEnabled(a is not None)

    def _new(self):
        if ArcherDialog(parent=self).exec():
            self.refresh()

    def _edit(self):
        a = self._archers.get(self.table.selected_id())
        if a and ArcherDialog(a, self).exec():
            self.refresh()

    def _toggle_active(self):
        a = self._archers.get(self.table.selected_id())
        if a is None:
            return
        if a.active and not confirm(self, f"{a.first_name} {a.last_name} deaktivieren?\n"
                                          "Turnierdaten bleiben erhalten."):
            return
        md.set_archer_active(a.id, not a.active)
        self.refresh()

    def _import(self):
        res = run_import(self, ARCHER_IMPORT_FIELDS, "Schützen importieren")
        if res is None:
            return
        records, strategy = res
        try:
            r = md.import_archers(records, strategy)
        except Exception as exc:
            show_error(self, exc, "Import fehlgeschlagen")
            return
        QMessageBox.information(self, "Import", f"Neu angelegt: {r['created']}\n"
                                f"Aktualisiert: {r['updated']}\nÜbersprungen: {r['skipped']}")
        self.refresh()

    def _export(self):
        rows = self.table.visible_rows()
        if self.table.search.text() and len(rows) < self.table.model.rowCount():
            if not confirm(self, f"Nur die {len(rows)} gefilterten Schützen exportieren?\n"
                                 "(Nein = alle exportieren)", "Export"):
                rows = [[self.table.model.item(r, c).text()
                         for c in range(self.table.model.columnCount())]
                        for r in range(self.table.model.rowCount())]
        run_export(self, "schuetzen.xlsx", [("Schützen", HEADERS, rows)])

# -*- coding: utf-8 -*-
"""Rankings per bow class (tabs), export and PDF result list."""
import logging

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from bowtally.io import exporter
from bowtally.reports.result_list import build_result_list, temp_pdf_path
from bowtally.services import ranking_service as rs
from bowtally.services import settings_service as ss
from bowtally.ui import button, show_error
from bowtally.ui.dialogs.export_helper import run_export
from bowtally.ui.widgets.sortable_table import SortableTable

log = logging.getLogger(__name__)


class ResultsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self._ranked_for = None
        self.tabs = QTabWidget()
        self.btn_print = button("Ergebnisliste drucken", self._print, "primary")
        self.btn_pdf = button("Als PDF speichern ...", self._save_pdf)
        self.print_hint = QLabel("Ergebnisliste erst ab Status 'Aktiv' verfügbar.")
        self.print_hint.setProperty("secondary", True)
        bar = QHBoxLayout()
        bar.addWidget(button("Neu berechnen", self.recalculate))
        bar.addStretch()
        bar.addWidget(self.print_hint)
        bar.addWidget(self.btn_print)
        bar.addWidget(self.btn_pdf)
        bar.addWidget(button("Export ...", self._export))
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.tabs, 1)

    def headers(self) -> list[str]:
        return (["Rang", "St.-Nr.", "Name", "Verein", "Klasse"]
                + [str(i) for i in range(1, self.tournament.num_targets + 1)] + ["Gesamt"])

    @staticmethod
    def _row(r) -> list:
        return [r.rank, r.start_number, r.name, r.club, r.bow_class] + r.target_totals + [r.total]

    def set_tournament(self, t):
        first_time = self.tournament is None or self.tournament.id != t.id
        self.tournament = t
        printable = t.status in ("active", "closed")
        self.btn_print.setEnabled(printable)
        self.btn_pdf.setEnabled(printable)
        self.print_hint.setVisible(not printable)
        if first_time or ss.get_bool(ss.KEY_RESULT_AUTO_RANK):
            self.recalculate()

    def recalculate(self):
        t = self.tournament
        current = self.tabs.currentIndex()
        self.tabs.clear()
        self.sheets = []
        names = {bc.id: bc.name for bc in t.bow_classes}
        overall = rs.compute_ranking(t.id, overall=True)[rs.OVERALL]
        per_class = rs.compute_ranking(t.id)
        for title, rows in [("Gesamt", overall)] + [
                (names.get(cid, "Ohne Klasse"), rows) for cid, rows in per_class.items()]:
            table = SortableTable(self.headers())
            table.set_rows([self._row(r) for r in rows], [r.participant_id for r in rows])
            self.tabs.addTab(table, f"{title} ({len(rows)})")
            self.sheets.append((title, self.headers(), [self._row(r) for r in rows]))
        self.tabs.setCurrentIndex(max(0, current))

    def _export(self):
        run_export(self, f"Rangliste_{self.tournament.name}.xlsx", self.sheets)

    def _print(self):
        try:
            path = build_result_list(self.tournament.id, temp_pdf_path(self.tournament.id))
            exporter.open_file(path)
        except Exception as exc:
            show_error(self, exc, "Ergebnisliste konnte nicht erstellt werden")

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ergebnisliste speichern",
                                              f"Ergebnisliste_{self.tournament.name}.pdf",
                                              "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            build_result_list(self.tournament.id, path)
        except Exception as exc:
            show_error(self, exc, "Ergebnisliste konnte nicht gespeichert werden")

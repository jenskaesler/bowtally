# -*- coding: utf-8 -*-
"""Rankings per bow class (tabs), podium highlight, export dropdown, PDF in background."""
from collections import Counter

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QTabWidget, QVBoxLayout, QWidget

from bowtally.reports.result_list import build_result_list, temp_pdf_path
from bowtally.services import ranking_service as rs
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, show_error, theme
from bowtally.ui.components.data_table import Cell, DataTable
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.spinner import Spinner
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.export_helper import export_button, open_path

PODIUM = {1: "gold_soft", 2: "silver_soft", 3: "bronze_soft"}
NOT_PRINTABLE = "Ergebnisliste erst ab der Phase „Schießen“ verfügbar"


class _PdfWorker(QThread):
    finished_with = Signal(object)    # Path or Exception

    def __init__(self, tournament_id: int, path, parent=None):
        super().__init__(parent)
        self.tournament_id, self.path = tournament_id, path

    def run(self):
        try:
            self.finished_with.emit(build_result_list(self.tournament_id, self.path))
        except Exception as exc:   # reported in the UI thread
            self.finished_with.emit(exc)


def rank_text(rank: int, counts: Counter) -> str:
    return f"{rank} (ex aequo)" if counts[rank] > 1 else str(rank)


class ResultsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.sheets = []
        self._worker = None
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.spinner = Spinner()
        self.btn_pdf = button("Ergebnisliste erstellen", self._create_pdf, "primary",
                              "Druckfertige Ergebnisliste als PDF erstellen")
        self.btn_save_pdf = button("Als PDF speichern", self._save_pdf,
                                   tooltip="Ergebnisliste an einem beliebigen Ort speichern")
        self.btn_export = export_button(self, "rangliste", lambda _f: self.sheets)
        self.info = QLabel(objectName="pageSubtitle")
        bar = QHBoxLayout()
        bar.addWidget(button("Neu berechnen", self.recalculate,
                             tooltip="Rangliste neu berechnen (F5)"))
        bar.addWidget(self.info)
        bar.addStretch()
        bar.addWidget(self.btn_export)
        bar.addWidget(self.btn_save_pdf)
        bar.addWidget(self.spinner)
        bar.addWidget(self.btn_pdf)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.tabs, 1)
        theme.notifier.changed.connect(lambda: self.tournament and self.recalculate())

    def headers(self) -> list[str]:
        return (["Rang", "Nr.", "Name", "Verein", "Klasse"]
                + [str(i) for i in range(1, self.tournament.num_targets + 1)] + ["Gesamt"])

    def set_tournament(self, t):
        first_time = self.tournament is None or self.tournament.id != t.id
        self.tournament = t
        printable = ts.phase_index(t.phase) >= ts.phase_index("shooting")
        for b in (self.btn_pdf, self.btn_save_pdf):
            b.setEnabled(printable and self._worker is None)
            b.setToolTip(b.toolTip() if printable else NOT_PRINTABLE)
        if first_time or ss.get_bool(ss.KEY_RESULT_AUTO_RANK):
            self.recalculate()

    def refresh(self):
        self.recalculate()

    def recalculate(self):
        t = self.tournament
        if t is None:
            return
        colors = theme.current()
        current = self.tabs.currentIndex()
        self.tabs.clear()
        self.sheets = []
        names = {bc.id: bc.name for bc in t.bow_classes}
        with busy():
            overall = rs.compute_ranking(t.id, overall=True)[rs.OVERALL]
            per_class = rs.compute_ranking(t.id)
        for title, rows in [("Gesamt", overall)] + [
                (names.get(cid, "Ohne Klasse"), rows) for cid, rows in per_class.items() if rows]:
            counts = Counter(r.rank for r in rows)
            table_rows, export_rows = [], []
            for r in rows:
                bg = colors[PODIUM[r.rank]] if r.rank in PODIUM and r.total > 0 else None
                values = [Cell(r.rank, text=rank_text(r.rank, counts), sort=r.rank),
                          r.start_number, r.name, r.club, r.bow_class] + \
                    [Cell(v, text="" if v is None else str(v), sort=-1 if v is None else v)
                     for v in r.target_totals] + [Cell(r.total, bold=True)]
                if bg:
                    values = [(v if isinstance(v, Cell) else Cell(v)) for v in values]
                    for v in values:
                        v.background = bg
                table_rows.append(values)
                export_rows.append([rank_text(r.rank, counts), r.start_number, r.name, r.club,
                                    r.bow_class] + r.target_totals + [r.total])
            empty = EmptyState("target", "Noch keine Teilnehmer",
                               "Sobald Teilnehmer zugewiesen sind, erscheint hier die Rangliste.")
            table = DataTable(self.headers(), empty)
            table.set_rows(table_rows, [r.participant_id for r in rows])
            self.tabs.addTab(table, f"{title} ({len(rows)})")
            self.sheets.append((title, self.headers(), export_rows))
        self.tabs.setCurrentIndex(max(0, min(current, self.tabs.count() - 1)))
        scored = sum(r.total > 0 for r in overall)
        self.info.setText(f"{scored} von {len(overall)} Teilnehmern mit Ergebnissen")

    # ------------------------------------------------------------ PDF
    def _create_pdf(self):
        self._start_pdf(temp_pdf_path(self.tournament.id))

    def _save_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Ergebnisliste speichern",
                                              f"Ergebnisliste_{self.tournament.name}.pdf",
                                              "PDF (*.pdf)")
        if path:
            self._start_pdf(path if path.lower().endswith(".pdf") else path + ".pdf")

    def _start_pdf(self, path):
        if self._worker is not None:
            return
        self.btn_pdf.setEnabled(False)
        self.btn_save_pdf.setEnabled(False)
        self.btn_pdf.setText("PDF wird erstellt …")
        self.spinner.start()
        self._worker = _PdfWorker(self.tournament.id, path, self)
        self._worker.finished_with.connect(self._pdf_done)
        self._worker.start()

    def _pdf_done(self, result):
        self._worker.wait()
        self._worker = None
        self.spinner.stop()
        self.btn_pdf.setText("Ergebnisliste erstellen")
        self.set_tournament(self.tournament)
        if isinstance(result, Exception):
            show_error(self, result, "Ergebnisliste konnte nicht erstellt werden")
            return
        ts.mark_results_generated(self.tournament.id)
        Toast.show(self, f"Ergebnisliste erstellt: {result.name}", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, result)))

    # global shortcuts
    def shortcut_save(self):
        if self.btn_save_pdf.isEnabled():
            self._save_pdf()

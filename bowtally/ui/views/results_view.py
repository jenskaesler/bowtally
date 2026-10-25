# -*- coding: utf-8 -*-
"""Rankings per bow class (tabs), podium highlight, export dropdown, PDF in background."""
from collections import Counter

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QCheckBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QTabWidget, QVBoxLayout, QWidget)

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
from bowtally.ui.utils.mailto import open_mailto

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


_ACTIVE_FOR_RESULTS = {"registered", "confirmed", "checked_in", "dnf", "dsq"}


class _SendResultsDialog(QDialog):
    """Select participants to notify about their results via mailto."""

    def __init__(self, tournament_id, pid_to_rank: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ergebnisse versenden")
        self.resize(520, 420)
        t = ts.get_tournament(tournament_id)
        self._t = t
        self._pid_to_rank = pid_to_rank
        info = QLabel(f"Ergebnisse für {t.name} ({t.date:%d.%m.%Y}) per E-Mail versenden.",
                      objectName="pageSubtitle")
        info.setWordWrap(True)
        self.lst = QListWidget()
        parts = sorted(
            [p for p in t.participants if p.registration_status in _ACTIVE_FOR_RESULTS],
            key=lambda p: (p.archer.last_name, p.archer.first_name)
        )
        for p in parts:
            has_email = bool(p.archer.email)
            r = pid_to_rank.get(p.id)
            rank_info = f"   Rang {r.rank}, {r.total} Pkt." if r else ""
            text = (f"{p.archer.last_name}, {p.archer.first_name}"
                    + rank_info
                    + (f"   {p.archer.email}" if has_email else "   (keine E-Mail)"))
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, p)
            if has_email:
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setToolTip("Keine E-Mail-Adresse hinterlegt")
            self.lst.addItem(item)
        self.lst.itemChanged.connect(self._update_btn)
        self._select_all_chk = QCheckBox("Alle auswählen")
        self._select_all_chk.setTristate(True)
        self._select_all_chk.clicked.connect(self._toggle_all)
        self.btn = button("E-Mail senden (0)", self._send, "primary")
        self.btn.setEnabled(False)
        row = QHBoxLayout()
        row.addWidget(self._select_all_chk)
        row.addStretch()
        row.addWidget(button("Schließen", self.reject))
        row.addWidget(self.btn)
        lay = QVBoxLayout(self)
        lay.addWidget(info)
        lay.addWidget(self.lst, 1)
        lay.addLayout(row)

    def _eligible(self):
        return [self.lst.item(i) for i in range(self.lst.count())
                if bool(self.lst.item(i).flags() & Qt.ItemFlag.ItemIsEnabled)]

    def _toggle_all(self):
        eligible = self._eligible()
        state = (Qt.CheckState.Unchecked
                 if all(it.checkState() == Qt.CheckState.Checked for it in eligible)
                 else Qt.CheckState.Checked)
        for it in eligible:
            it.setCheckState(state)

    def _update_btn(self, *_):
        eligible = self._eligible()
        n = sum(1 for it in eligible if it.checkState() == Qt.CheckState.Checked)
        self.btn.setText(f"E-Mail senden ({n})")
        self.btn.setEnabled(n > 0)
        self._select_all_chk.blockSignals(True)
        if n == 0:
            self._select_all_chk.setCheckState(Qt.CheckState.Unchecked)
        elif n == len(eligible):
            self._select_all_chk.setCheckState(Qt.CheckState.Checked)
        else:
            self._select_all_chk.setCheckState(Qt.CheckState.PartiallyChecked)
        self._select_all_chk.blockSignals(False)

    def _send(self):
        t = self._t
        for i in range(self.lst.count()):
            item = self.lst.item(i)
            if item.checkState() != Qt.CheckState.Checked:
                continue
            p = item.data(Qt.ItemDataRole.UserRole)
            r = self._pid_to_rank.get(p.id)
            open_mailto(ss.KEY_EMAIL_TPL_RESULTS, p.archer.email, {
                "name": f"{p.archer.first_name} {p.archer.last_name}",
                "verein": p.archer.club or "",
                "klasse": p.bow_class.name if p.bow_class else "",
                "turniername": t.name,
                "datum": f"{t.date:%d.%m.%Y}",
                "platz": str(r.rank) if r else "",
                "punkte": str(r.total) if r else "",
            }, self)
        self.accept()


class ResultsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self.sheets = []
        self._worker = None
        self._pid_to_rank: dict = {}
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.spinner = Spinner()
        self.btn_pdf = button("Ergebnisliste erstellen", self._create_pdf, "primary",
                              "Druckfertige Ergebnisliste als PDF erstellen")
        self.btn_save_pdf = button("Als PDF speichern", self._save_pdf,
                                   tooltip="Ergebnisliste an einem beliebigen Ort speichern")
        self.btn_send = button("Ergebnisse versenden", self._send_results,
                               tooltip="Ergebnisse per E-Mail an Teilnehmer versenden")
        self.btn_export = export_button(self, "rangliste", lambda _f: self.sheets)
        self.info = QLabel(objectName="pageSubtitle")
        bar = QHBoxLayout()
        bar.addWidget(button("Neu berechnen", self.recalculate,
                             tooltip="Rangliste neu berechnen (F5)"))
        bar.addWidget(self.info)
        bar.addStretch()
        bar.addWidget(self.btn_export)
        bar.addWidget(self.btn_save_pdf)
        bar.addWidget(self.btn_send)
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
        sendable = t.phase in ("scoring", "closed")
        self.btn_send.setEnabled(sendable)
        self.btn_send.setToolTip(
            "Ergebnisse per E-Mail an Teilnehmer versenden" if sendable
            else "Nur in der Phase „Auswertung“ oder „Abgeschlossen“ verfügbar"
        )
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
        self._pid_to_rank = {r.participant_id: r
                             for rows in per_class.values() for r in rows}
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

    def _send_results(self):
        if self.tournament is None:
            return
        dlg = _SendResultsDialog(self.tournament.id, self._pid_to_rank, self)
        dlg.exec()

    # global shortcuts
    def shortcut_save(self):
        if self.btn_save_pdf.isEnabled():
            self._save_pdf()

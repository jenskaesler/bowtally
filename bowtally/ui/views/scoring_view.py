# -*- coding: utf-8 -*-
"""Score entry grid: rows = participants, columns = targets (x shots)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QLineEdit,
                               QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from bowtally.services import scoring_service as sc
from bowtally.ui import show_error

FIXED_COLS = 3          # start number, name, class
CELL_ROLE = Qt.ItemDataRole.UserRole + 1   # (participant_id, target, shot)


class ZoneDelegate(QStyledItemDelegate):
    """Editable combo: pick a zone or type a number directly."""

    def __init__(self, zones: list[dict], parent=None):
        super().__init__(parent)
        self.zones = zones

    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        cb.setEditable(True)
        cb.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        cb.addItem("")
        cb.addItems([f"{z['zone']} ({z['points']})" for z in self.zones])
        return cb

    def setEditorData(self, editor, index):
        editor.setCurrentText(index.data() or "")
        editor.lineEdit().selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText())


class ScoringView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self._loading = False
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.itemChanged.connect(self._on_changed)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Teilnehmer filtern (Name / Startnummer) ...")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        self.status = QLabel()
        self.status.setProperty("secondary", True)
        top = QHBoxLayout()
        top.addWidget(self.filter, 1)
        hint = QLabel("Eingabe: Zahl oder Zone wählen. Jede Eingabe wird sofort gespeichert.")
        hint.setProperty("secondary", True)
        top.addWidget(hint)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table, 1)
        lay.addWidget(self.status)

    def set_tournament(self, t):
        self.tournament = t
        self.zones = t.scoring_rule.ring_values if t.scoring_rule else []
        self.table.setItemDelegate(ZoneDelegate(self.zones, self.table))
        shots = t.shots_per_target
        self.cols = [(tg, s) for tg in range(1, t.num_targets + 1) for s in range(1, shots + 1)]
        headers = ["St.-Nr.", "Name", "Klasse"] + [
            str(tg) if shots == 1 else f"{tg}.{s}" for tg, s in self.cols] + ["Gesamt"]
        scores = sc.get_scores(t.id)
        parts = sorted(t.participants, key=lambda p: (p.start_number or 10**9,
                                                      p.archer.last_name))
        self._loading = True
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(parts))
        locked = t.status == "closed"
        for r, p in enumerate(parts):
            for c, text in enumerate([str(p.start_number or ""),
                                      f"{p.archer.last_name}, {p.archer.first_name}",
                                      p.bow_class.abbreviation or p.bow_class.name
                                      if p.bow_class else "-"]):
                it = QTableWidgetItem(text)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                it.setData(CELL_ROLE, p.id)
                self.table.setItem(r, c, it)
            for c, (tg, s) in enumerate(self.cols, start=FIXED_COLS):
                score = scores.get((p.id, tg, s))
                it = QTableWidgetItem("" if score is None else str(score.points))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it.setData(CELL_ROLE, (p.id, tg, s))
                if score is not None and score.zone_hit:
                    it.setToolTip(score.zone_hit)
                if locked:
                    it.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(r, c, it)
            total = QTableWidgetItem()
            total.setFlags(Qt.ItemFlag.ItemIsEnabled)
            total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            f = total.font()
            f.setBold(True)
            total.setFont(f)
            self.table.setItem(r, len(headers) - 1, total)
            self._update_total(r)
        self._loading = False
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers if locked else
                                   QAbstractItemView.EditTrigger.AllEditTriggers)
        self.table.resizeColumnsToContents()
        for c in range(FIXED_COLS, len(headers) - 1):
            self.table.setColumnWidth(c, max(self.table.columnWidth(c), 44))
        self.status.setText("Turnier abgeschlossen – Eingaben gesperrt." if locked else
                            f"{len(parts)} Teilnehmer · {t.num_targets} Scheiben")
        self._apply_filter(self.filter.text())

    def _update_total(self, row: int):
        total = 0
        for c in range(FIXED_COLS, FIXED_COLS + len(self.cols)):
            text = self.table.item(row, c).text()
            total += int(text) if text.lstrip("-").isdigit() else 0
        self.table.item(row, FIXED_COLS + len(self.cols)).setText(str(total))

    def _on_changed(self, item: QTableWidgetItem):
        if self._loading or item.column() < FIXED_COLS or \
                item.column() >= FIXED_COLS + len(self.cols):
            return
        pid, target, shot = item.data(CELL_ROLE)
        self._loading = True
        try:
            entry = sc.parse_entry(item.text(), self.zones)
            sc.set_score(pid, target, shot, entry)
            item.setText("" if entry is None else str(entry[0]))
            item.setToolTip(entry[1] or "" if entry else "")
            item.setBackground(QBrush())
        except Exception as exc:
            item.setBackground(QBrush(QColor("#FDE2E2")))
            show_error(self, exc)
            # restore the persisted value
            stored = sc.get_scores(self.tournament.id).get((pid, target, shot))
            item.setText("" if stored is None else str(stored.points))
        finally:
            self._loading = False
        self._update_total(item.row())

    def _apply_filter(self, text: str):
        text = text.strip().lower()
        for r in range(self.table.rowCount()):
            hay = " ".join(self.table.item(r, c).text().lower() for c in range(FIXED_COLS))
            self.table.setRowHidden(r, bool(text) and text not in hay)

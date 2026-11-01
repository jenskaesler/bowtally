# -*- coding: utf-8 -*-
"""Logbuch: chronological list of all app activity with filtering and pagination."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from bowtally.services import logbuch_service as ls
from bowtally.ui import theme
from bowtally.ui.components.page_header import PageHeader

# log_type -> (label, bg_color)
TYPE_META: dict[str, tuple[str, str]] = {
    "score":        ("Aktivität",     "#2563EB"),
    "phase":        ("Phasenwechsel", "#7C3AED"),
    "backup":       ("Backup",        "#16A34A"),
    "checkin":      ("Eincheck",      "#16A34A"),
    "score_change": ("Änderung",      "#EA580C"),
    "protest":      ("Einspruch",     "#DC2626"),
}
PLACEHOLDER_TYPES = {"score_change", "protest"}

PERIODS = [
    (None, "Gesamter Zeitraum"),
    (1,    "Heute"),
    (7,    "Letzte 7 Tage"),
    (30,   "Letzte 30 Tage"),
]


class _EntryRow(QFrame):
    def __init__(self, entry: ls.LogEntry, parent=None):
        super().__init__(parent)
        t = theme.current()
        label, color = TYPE_META.get(entry.log_type, ("Unbekannt", t["text2"]))

        chip = QLabel(f"  {label}  ")
        chip.setStyleSheet(
            f"background:{color}; color:#FFFFFF; border-radius:3px;"
            f"font-size:11px; font-weight:600;"
        )
        chip.setFixedHeight(18)
        chip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        desc = QLabel(entry.description)
        desc.setStyleSheet("font-weight:500;")

        ts_text = f"{entry.created_at:%d.%m. %H:%M}" if entry.created_at else ""
        ts_lbl = QLabel(ts_text)
        ts_lbl.setStyleSheet(f"color:{t['text2']}; font-size:12px;")
        ts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ts_lbl.setMinimumWidth(90)

        ctx = QLabel(entry.context)
        ctx.setStyleSheet(f"color:{t['text2']}; font-size:12px;")

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)
        top_row.addWidget(chip)
        top_row.addWidget(desc, 1)
        top_row.addWidget(ts_lbl)

        inner = QVBoxLayout()
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(2)
        inner.addLayout(top_row)
        inner.addWidget(ctx)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.addLayout(inner)


class LogbuchView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.header = PageHeader("Logbuch", "Protokoll aller Aktivitäten")

        # ---- filter bar ----
        self._t_combo = QComboBox()
        self._t_combo.setMinimumWidth(180)
        self._period_combo = QComboBox()
        for _days, label in PERIODS:
            self._period_combo.addItem(label)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Suche …")
        self._search.setMaximumWidth(200)

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        filter_bar.addWidget(self._t_combo)
        filter_bar.addWidget(self._period_combo)
        filter_bar.addStretch(1)
        filter_bar.addWidget(self._search)

        # ---- type chips ----
        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        self._all_chip = QPushButton("Alle", objectName="chip")
        self._all_chip.setCheckable(True)
        self._all_chip.setChecked(True)
        self._all_chip.setFixedHeight(28)
        self._all_chip.clicked.connect(self._on_all_chip)
        chips_row.addWidget(self._all_chip)

        self._type_chips: dict[str, QPushButton] = {}
        for log_type, (label, _color) in TYPE_META.items():
            btn = QPushButton(label, objectName="chip")
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            if log_type in PLACEHOLDER_TYPES:
                btn.setEnabled(False)
                btn.setToolTip("Verfügbar ab nächstem Update")
            else:
                btn.clicked.connect(self._on_type_chip)
            self._type_chips[log_type] = btn
            chips_row.addWidget(btn)
        chips_row.addStretch(1)

        # ---- scroll area for entries ----
        self._container = QWidget()
        self._container_lay = QVBoxLayout(self._container)
        self._container_lay.setContentsMargins(0, 0, 0, 0)
        self._container_lay.setSpacing(1)
        self._container_lay.addStretch(1)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setWidget(self._container)

        self._load_more_btn = QPushButton("Ältere laden …")
        self._load_more_btn.clicked.connect(self._load_more)
        self._load_more_btn.hide()

        # ---- main layout ----
        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self.header)

        controls = QWidget()
        ctrl_lay = QVBoxLayout(controls)
        ctrl_lay.setContentsMargins(20, 12, 20, 8)
        ctrl_lay.setSpacing(8)
        ctrl_lay.addLayout(filter_bar)
        ctrl_lay.addLayout(chips_row)
        main.addWidget(controls)
        main.addWidget(self._scroll, 1)
        main.addWidget(self._load_more_btn)

        self._offset = 0
        self._total = 0
        self._tournaments: list[tuple[int | None, str]] = []

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._reload)
        self._search.textChanged.connect(lambda: self._search_timer.start())
        self._t_combo.currentIndexChanged.connect(self._reload)
        self._period_combo.currentIndexChanged.connect(self._reload)

    # ---------------------------------------------------------------- chips
    def _on_all_chip(self):
        for btn in self._type_chips.values():
            if btn.isEnabled():
                btn.setChecked(False)
        self._all_chip.setChecked(True)
        self._reload()

    def _on_type_chip(self):
        any_checked = any(b.isChecked() for b in self._type_chips.values() if b.isEnabled())
        self._all_chip.setChecked(not any_checked)
        self._reload()

    def _active_types(self) -> set | None:
        if self._all_chip.isChecked():
            return None
        types = {k for k, b in self._type_chips.items() if b.isChecked() and b.isEnabled()}
        return types or None

    # ---------------------------------------------------------------- data
    def _selected_tournament(self) -> int | None:
        return self._t_combo.currentData()

    def _selected_period(self) -> int | None:
        idx = self._period_combo.currentIndex()
        return PERIODS[idx][0] if 0 <= idx < len(PERIODS) else None

    def _reload(self):
        self._offset = 0
        self._clear_entries()
        self._fetch_and_render()

    def _load_more(self):
        self._offset += ls.PAGE_SIZE
        self._fetch_and_render()

    def _fetch_and_render(self):
        entries, self._total = ls.list_entries(
            tournament_id=self._selected_tournament(),
            log_types=self._active_types(),
            period_days=self._selected_period(),
            search=self._search.text(),
            offset=self._offset,
            limit=ls.PAGE_SIZE,
        )
        for entry in entries:
            row = _EntryRow(entry)
            self._container_lay.insertWidget(self._container_lay.count() - 1, row)

        shown = self._offset + len(entries)
        self._load_more_btn.setVisible(shown < self._total)
        if shown < self._total:
            self._load_more_btn.setText(f"Ältere laden … ({self._total - shown} weitere)")
        self.header.set_subtitle(
            f"{self._total} Einträge" if self._total else "Keine Einträge")

    def _clear_entries(self):
        while self._container_lay.count() > 1:
            item = self._container_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ---------------------------------------------------------------- lifecycle
    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        self._populate_tournament_combo()
        self._reload()

    def _populate_tournament_combo(self):
        self._t_combo.blockSignals(True)
        prev = self._t_combo.currentData()
        self._t_combo.clear()
        self._t_combo.addItem("Alle Turniere", None)
        self._tournaments = ls.list_tournaments_with_log()
        for tid, name in self._tournaments:
            self._t_combo.addItem(name, tid)
        idx = self._t_combo.findData(prev)
        self._t_combo.setCurrentIndex(max(0, idx))
        self._t_combo.blockSignals(False)

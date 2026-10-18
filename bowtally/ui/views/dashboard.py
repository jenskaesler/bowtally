# -*- coding: utf-8 -*-
"""Overview: active tournaments, quick access to the latest tournament, archer count."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QVBoxLayout, QWidget)

from bowtally.services import master_data_service as md
from bowtally.services import tournament_service as ts
from bowtally.ui import button
from bowtally.ui.views import page_title


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 12, 16, 12)
    head = QLabel(title)
    head.setObjectName("sectionTitle")
    lay.addWidget(head)
    return frame, lay


class DashboardView(QWidget):
    open_tournament = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_id = None
        lay = QVBoxLayout(self)
        lay.addWidget(page_title("Dashboard"))
        grid = QGridLayout()
        grid.setSpacing(16)

        card, c_lay = _card("Schützen (aktiv)")
        self.archer_count = QLabel("0")
        self.archer_count.setObjectName("cardValue")
        c_lay.addWidget(self.archer_count)
        grid.addWidget(card, 0, 0)

        card, c_lay = _card("Aktive Turniere")
        self.active_count = QLabel("0")
        self.active_count.setObjectName("cardValue")
        c_lay.addWidget(self.active_count)
        grid.addWidget(card, 0, 1)

        card, c_lay = _card("Letztes Turnier")
        self.last_label = QLabel("-")
        self.last_label.setWordWrap(True)
        self.last_btn = button("Öffnen", self._open_last, "primary")
        row = QHBoxLayout()
        row.addWidget(self.last_btn)
        row.addStretch()
        c_lay.addWidget(self.last_label)
        c_lay.addLayout(row)
        grid.addWidget(card, 0, 2)

        card, c_lay = _card("Laufende Turniere")
        self.active_list = QListWidget()
        self.active_list.itemDoubleClicked.connect(
            lambda it: self.open_tournament.emit(it.data(Qt.ItemDataRole.UserRole)))
        hint = QLabel("Doppelklick öffnet das Turnier.")
        hint.setProperty("secondary", True)
        c_lay.addWidget(self.active_list)
        c_lay.addWidget(hint)
        grid.addWidget(card, 1, 0, 1, 3)
        grid.setRowStretch(1, 1)
        lay.addLayout(grid, 1)

    def refresh(self):
        self.archer_count.setText(str(md.count_active_archers()))
        active = ts.list_tournaments("active")
        self.active_count.setText(str(len(active)))
        self.active_list.clear()
        for t in active:
            item = QListWidgetItem(f"{t.date:%d.%m.%Y}  {t.name}  ({t.location or '-'}, "
                                   f"{len(t.participants)} Teilnehmer)")
            item.setData(Qt.ItemDataRole.UserRole, t.id)
            self.active_list.addItem(item)
        last = ts.last_tournament()
        self._last_id = last.id if last else None
        self.last_btn.setEnabled(last is not None)
        self.last_label.setText(
            f"{last.name}\n{last.date:%d.%m.%Y} · {ts.STATUS_LABELS[last.status]}"
            if last else "Noch kein Turnier angelegt.")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def _open_last(self):
        if self._last_id is not None:
            self.open_tournament.emit(self._last_id)

# -*- coding: utf-8 -*-
"""Overview: active tournaments, archers, next tournament, recent score activity."""
from datetime import date

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QVBoxLayout, QWidget)

from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts
from bowtally.ui import button
from bowtally.ui.components.data_table import Cell, DataTable
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.status_chip import StatusChip

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
ACTIVE_LINKS = 3


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(objectName="card")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 14, 18, 16)
    lay.setSpacing(6)
    lay.addWidget(QLabel(title, objectName="sectionTitle"))
    return frame, lay


def _link(text: str, slot, tooltip: str) -> QPushButton:
    b = QPushButton(text, objectName="link")
    b.setToolTip(tooltip)
    b.clicked.connect(slot)
    return b


class DashboardView(QWidget):
    open_tournament = Signal(int, str)     # id, tab ('' | 'scoring' | ...)
    new_tournament = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        today = date.today()
        self.header = PageHeader("Dashboard", f"{WEEKDAYS[today.weekday()]}, "
                                              f"{today:%d.%m.%Y}")
        grid = QGridLayout()
        grid.setSpacing(16)

        card, c = _card("Aktive Turniere")
        self.active_count = QLabel("0", objectName="cardValue")
        self.active_links = QVBoxLayout()
        self.active_links.setSpacing(0)
        c.addWidget(self.active_count)
        c.addLayout(self.active_links)
        c.addStretch()
        grid.addWidget(card, 0, 0)

        card, c = _card("Schützen")
        self.archer_count = QLabel("0", objectName="cardValue")
        self.club_count = QLabel(objectName="pageSubtitle")
        c.addWidget(self.archer_count)
        c.addWidget(self.club_count)
        c.addStretch()
        grid.addWidget(card, 0, 1)

        card, c = _card("Nächstes Turnier")
        self.next_name = QLabel(objectName="emptyTitle")
        self.next_name.setWordWrap(True)
        self.next_meta = QLabel(objectName="pageSubtitle")
        self.next_chip = StatusChip()
        self.next_btn = button("Zum Turnier", self._open_next, "primary",
                               "Turnier öffnen")
        row = QHBoxLayout()
        row.addWidget(self.next_btn)
        row.addWidget(self.next_chip)
        row.addStretch()
        c.addWidget(self.next_name)
        c.addWidget(self.next_meta)
        c.addStretch()
        c.addLayout(row)
        grid.addWidget(card, 0, 2)

        card, c = _card("Letzte Aktivität")
        empty = EmptyState("clock", "Noch keine Ergebnisse erfasst",
                           "Hier erscheinen die zuletzt eingegebenen Wertungen.")
        self.activity = DataTable(["Zeit", "Turnier", "Schütze", "Scheibe", "Punkte"], empty)
        self.activity.activated.connect(self._open_activity)
        self.activity.setToolTip("Doppelklick öffnet die Ergebniseingabe")
        c.addWidget(self.activity, 1)
        grid.addWidget(card, 1, 0, 1, 3)
        grid.setRowStretch(1, 1)
        for col in range(3):
            grid.setColumnStretch(col, 1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        lay.addLayout(grid, 1)
        self._next_id = None
        self._activity = []

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        tournaments = ts.list_tournaments()
        active = [t for t in tournaments if t.status == "active"]
        self.active_count.setText(str(len(active)))
        while self.active_links.count():
            w = self.active_links.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for t in active[:ACTIVE_LINKS]:
            self.active_links.addWidget(_link(
                f"{t.name}  →", lambda _=False, tid=t.id: self.open_tournament.emit(tid, "scoring"),
                "Zur Ergebniseingabe"))
        if not active:
            self.active_links.addWidget(QLabel("Kein Turnier aktiv", objectName="pageSubtitle"))

        archers = md.list_archers()
        clubs = {a.club.strip().lower() for a in archers if a.club}
        self.archer_count.setText(str(len(archers)))
        self.club_count.setText(f"aus {len(clubs)} Vereinen" if clubs else "noch keine Vereine")

        upcoming = sorted((t for t in tournaments
                           if t.status != "closed" and t.date >= date.today()),
                          key=lambda t: t.date)
        nxt = upcoming[0] if upcoming else None
        self._next_id = nxt.id if nxt else None
        if nxt:
            self.next_name.setText(nxt.name)
            self.next_meta.setText(f"{nxt.date:%d.%m.%Y} · {nxt.location or 'Ort offen'}")
            self.next_chip.set_tournament_status(nxt.status)
            self.next_btn.setText("Zum Turnier")
            self.next_btn.setToolTip("Turnier öffnen")
        else:
            self.next_name.setText("Kein Turnier geplant")
            self.next_meta.setText("Lege ein neues Turnier an.")
            self.next_btn.setText("Neues Turnier")
            self.next_btn.setToolTip("Neues Turnier mit dem Assistenten anlegen")
        self.next_chip.setVisible(nxt is not None)

        self._activity = sc.recent_scores()
        self.activity.set_rows(
            [[Cell(a["entered_at"], text=f"{a['entered_at']:%d.%m. %H:%M}"
                   if a["entered_at"] else "", sort=str(a["entered_at"])),
              a["tournament"], a["archer"],
              a["target"] if a["shot"] == 1 else f"{a['target']}.{a['shot']}",
              Cell(a["points"], tooltip=a["zone"] or "")] for a in self._activity],
            list(range(len(self._activity))))
        self.header.set_subtitle(
            f"{WEEKDAYS[date.today().weekday()]}, {date.today():%d.%m.%Y} · "
            f"{len(tournaments)} Turniere · {len(archers)} aktive Schützen")

    def _open_next(self):
        if self._next_id is None:
            self.new_tournament.emit()
        else:
            self.open_tournament.emit(self._next_id, "")

    def _open_activity(self, index):
        if index is not None and index < len(self._activity):
            self.open_tournament.emit(self._activity[index]["tournament_id"], "scoring")

    # global shortcuts
    def shortcut_new(self):
        self.new_tournament.emit()

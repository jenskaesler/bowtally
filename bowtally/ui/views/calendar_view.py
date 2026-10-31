# -*- coding: utf-8 -*-
"""Turnierkalender: Monat-, Wochen- und Tagesansicht mit Badge-Navigation und Hover-Vorschau.
BUG-01 fix: Tageszellen erhalten eindeutige Rasterpositionen (Wochenzeile × Wochentag).
BUG-02 fix: openTournament-Signal war bereits verdrahtet; Klick auf Badges funktioniert jetzt
            korrekt, da keine Zellen mehr überlagert werden.
CHG-09: Ansichtsmodi Monat / Woche / Tag mit Navigationsleiste.
CHG-10: Hover-Vorschaukarte mit 400 ms Verzögerung und Fade-out.
"""
import calendar
import re
from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import button
from bowtally.ui import theme
from bowtally.ui.components.status_chip import PHASE_KINDS

_MODE_KEY = "calendar_view_mode"
_MONTH_NAMES = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                "Juli", "August", "September", "Oktober", "November", "Dezember"]
_DAY_ABBR = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
_KIND_TOKEN = {
    "muted": "text2", "neutral": "text2", "primary": "primary",
    "success": "success", "warning": "warning", "danger": "accent",
}
_MAX_BADGES = 3  # max badges shown per day cell before "+N weitere"


def _phase_color(phase: str) -> str:
    return _KIND_TOKEN.get(PHASE_KINDS.get(phase, "neutral"), "text2")


# ---------------------------------------------------------------------------
# Badge widget
# ---------------------------------------------------------------------------

class _Badge(QPushButton):
    """Compact coloured strip for one tournament inside a day cell."""
    hovered = Signal(object, object)   # tournament obj, global QPoint
    unhovered = Signal()

    def __init__(self, tournament, parent=None):
        super().__init__(parent)
        self.t = tournament
        self.setText(tournament.name)
        self.setObjectName("tournamentBadge")
        self._apply_color()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMaximumHeight(20)
        f = self.font()
        f.setPointSize(max(7, f.pointSize() - 2))
        self.setFont(f)

    def _apply_color(self):
        t = theme.current()
        tok = _phase_color(self.t.phase)
        c = t.get(tok, t["text"])
        s = t.get(tok + "_soft", t["surface"])
        self.setStyleSheet(
            f"QPushButton#tournamentBadge{{background:{s};color:{c};"
            f"border:1px solid {c};border-radius:3px;padding:1px 4px;text-align:left;}}"
            f"QPushButton#tournamentBadge:hover{{background:{c};color:{t['bg']};}}"
        )

    def enterEvent(self, e):
        super().enterEvent(e)
        self.hovered.emit(self.t, self.mapToGlobal(self.rect().center()))

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.unhovered.emit()


# ---------------------------------------------------------------------------
# Hover card
# ---------------------------------------------------------------------------

class _HoverCard(QFrame):
    """Floating detail card shown on badge hover (child of CalendarView)."""
    openRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tid = None
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self.setObjectName("hoverCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(280)

        eff = QGraphicsDropShadowEffect(self)
        eff.setBlurRadius(12)
        eff.setOffset(0, 4)
        eff.setColor(QColor(0, 0, 0, 38))
        self.setGraphicsEffect(eff)

        self._phase_lbl = QLabel(objectName="pageSubtitle")
        self._name_lbl = QLabel()
        f = self._name_lbl.font()
        f.setBold(True)
        self._name_lbl.setFont(f)
        self._name_lbl.setWordWrap(True)
        sep = QFrame(frameShape=QFrame.Shape.HLine)
        self._detail_lbl = QLabel(objectName="pageSubtitle")
        self._detail_lbl.setWordWrap(True)
        self._open_btn = button("Turnier öffnen →", self._do_open, "primary")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        for w in (self._phase_lbl, self._name_lbl, sep, self._detail_lbl, self._open_btn):
            lay.addWidget(w)

        self.hide()

    def _do_open(self):
        if self._tid:
            self.openRequested.emit(self._tid)
        self.hide()

    def show_for(self, t, global_pos):
        """Position and show the card. Must be called on a child of CalendarView."""
        self._tid = t.id
        self._phase_lbl.setText(ts.PHASE_LABELS.get(t.phase, t.phase))
        self._name_lbl.setText(t.name)
        lines = [f"Datum: {t.date:%d.%m.%Y}"]
        if getattr(t, "location", None):
            lines.append(f"Ort: {t.location}")
        n_parts = sum(1 for p in t.participants
                      if p.registration_status not in ("withdrawn", "waitlisted"))
        lines.append(f"Teilnehmer: {n_parts}")
        self._detail_lbl.setText("\n".join(lines))
        self.adjustSize()

        # Convert global → parent-local coords, clip to parent bounds
        parent = self.parentWidget()
        if parent:
            lp = parent.mapFromGlobal(global_pos)
            x = lp.x() + 12
            y = lp.y() - self.height() // 2
            x = max(4, min(x, parent.width() - self.width() - 4))
            y = max(4, min(y, parent.height() - self.height() - 4))
            self.move(x, y)

        self.show()
        self.raise_()
        self._hide_timer.stop()

    def schedule_hide(self):
        self._hide_timer.start(150)

    def cancel_hide(self):
        self._hide_timer.stop()

    def enterEvent(self, e):
        super().enterEvent(e)
        self.cancel_hide()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.schedule_hide()


# ---------------------------------------------------------------------------
# Day cell
# ---------------------------------------------------------------------------

class _DayCell(QFrame):
    tournamentClicked = Signal(int)
    badgeHovered = Signal(object, object)
    badgeUnhovered = Signal()

    def __init__(self, d: date, tournaments: list, is_other_month: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("dayCell")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(3, 2, 3, 2)
        lay.setSpacing(1)

        num = QLabel(str(d.day))
        num.setObjectName("dayNumber")
        if is_other_month:
            num.setProperty("otherMonth", True)
        elif d == date.today():
            num.setProperty("today", True)
        lay.addWidget(num, 0, Qt.AlignmentFlag.AlignRight)

        for t in tournaments[:_MAX_BADGES]:
            badge = _Badge(t)
            badge.clicked.connect(lambda _=False, tid=t.id: self.tournamentClicked.emit(tid))
            badge.hovered.connect(self.badgeHovered)
            badge.unhovered.connect(self.badgeUnhovered)
            lay.addWidget(badge)

        if len(tournaments) > _MAX_BADGES:
            more = QLabel(f"+{len(tournaments) - _MAX_BADGES} weitere",
                          objectName="pageSubtitle")
            lay.addWidget(more)

        lay.addStretch()


# ---------------------------------------------------------------------------
# Main calendar view
# ---------------------------------------------------------------------------

class CalendarView(QWidget):
    openTournament = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tournaments: list = []
        self._by_date: dict = {}
        self._anchor = date.today()
        self._mode = ss.get(_MODE_KEY, "month") or "month"

        # hover-card is a direct child so it floats over the scroll area
        self._hover_card = _HoverCard(self)
        self._hover_card.openRequested.connect(self._on_badge_click)
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._do_show_hover)
        self._pending_hover = None   # (tournament, global_pos)

        # --- nav bar -------------------------------------------------------
        self._btn_back = button("◀", self._go_back, tooltip="Zurück")
        self._btn_today = button("Heute", self._go_today, tooltip="Zum aktuellen Datum")
        self._btn_fwd = button("▶", self._go_forward, tooltip="Vor")
        self._title_lbl = QLabel()
        f = self._title_lbl.font()
        f.setBold(True)
        f.setPointSize(f.pointSize() + 1)
        self._title_lbl.setFont(f)

        self._btn_month = QPushButton("Monat")
        self._btn_week = QPushButton("Woche")
        self._btn_day = QPushButton("Tag")
        self._mode_grp = QButtonGroup(self)
        for i, (name, btn_w) in enumerate([("month", self._btn_month),
                                            ("week", self._btn_week),
                                            ("day", self._btn_day)]):
            btn_w.setCheckable(True)
            btn_w.setObjectName("calModeBtn")
            self._mode_grp.addButton(btn_w, i)
        {"month": self._btn_month, "week": self._btn_week,
         "day": self._btn_day}.get(self._mode, self._btn_month).setChecked(True)
        self._mode_grp.idClicked.connect(self._on_mode_id)

        mode_bar = QHBoxLayout()
        mode_bar.setSpacing(0)
        mode_bar.setContentsMargins(0, 0, 0, 0)
        for btn_w in (self._btn_month, self._btn_week, self._btn_day):
            mode_bar.addWidget(btn_w)

        nav = QHBoxLayout()
        nav.addWidget(self._btn_back)
        nav.addWidget(self._btn_today)
        nav.addWidget(self._btn_fwd)
        nav.addSpacing(12)
        nav.addWidget(self._title_lbl, 1)
        nav.addLayout(mode_bar)
        nav.addSpacing(8)
        nav.addWidget(button("ICS exportieren", self._export_ics,
                             tooltip="Alle Turniere als Kalender-Datei exportieren"))

        # --- scroll area ---------------------------------------------------
        self._content = QWidget()
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 4, 0, 4)
        self._content_lay.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._content)

        main = QVBoxLayout(self)
        main.setContentsMargins(12, 8, 12, 8)
        main.setSpacing(8)
        main.addLayout(nav)
        main.addWidget(scroll, 1)

    # ── lifecycle ───────────────────────────────────────────────────────────

    def showEvent(self, e):
        super().showEvent(e)
        self.refresh()

    def refresh(self):
        self._tournaments = ts.list_tournaments()
        self._by_date = {}
        for t in self._tournaments:
            self._by_date.setdefault(t.date, []).append(t)
        self._rebuild()

    # ── navigation ──────────────────────────────────────────────────────────

    def _go_back(self):
        self._anchor = self._step(-1)
        self._rebuild()

    def _go_forward(self):
        self._anchor = self._step(1)
        self._rebuild()

    def _go_today(self):
        self._anchor = date.today()
        self._rebuild()

    def _step(self, n: int) -> date:
        a = self._anchor
        if self._mode == "month":
            m = a.month + n
            y = a.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            last = calendar.monthrange(y, m)[1]
            return date(y, m, min(a.day, last))
        if self._mode == "week":
            return a + timedelta(weeks=n)
        return a + timedelta(days=n)

    def _on_mode_id(self, idx: int):
        self._mode = ["month", "week", "day"][idx]
        try:
            ss.set_value(_MODE_KEY, self._mode)
        except Exception:
            pass
        self._rebuild()

    # ── rebuild ─────────────────────────────────────────────────────────────

    def _rebuild(self):
        self._hover_card.hide()
        while self._content_lay.count():
            item = self._content_lay.takeAt(0)
            if w := item.widget():
                w.deleteLater()
        if self._mode == "month":
            self._build_month()
        elif self._mode == "week":
            self._build_week()
        else:
            self._build_day()

    def _build_month(self):
        a = self._anchor
        self._title_lbl.setText(f"{_MONTH_NAMES[a.month - 1]} {a.year}")
        count = sum(1 for t in self._tournaments if t.date.year == a.year and t.date.month == a.month)
        if count:
            self._title_lbl.setText(
                f"{_MONTH_NAMES[a.month - 1]} {a.year}  ·  {count} Turnier{'e' if count != 1 else ''}")
        self._content_lay.addWidget(self._month_panel(a.year, a.month))
        self._content_lay.addStretch()

    def _build_week(self):
        a = self._anchor
        monday = a - timedelta(days=a.weekday())
        sunday = monday + timedelta(6)
        self._title_lbl.setText(
            f"KW {monday.isocalendar()[1]}  ·  {monday:%d.%m.} – {sunday:%d.%m.%Y}")
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setSpacing(4)
        for col, name in enumerate(_DAY_ABBR):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setObjectName("calDayHeader")
            f = lbl.font()
            f.setBold(True)
            lbl.setFont(f)
            grid.addWidget(lbl, 0, col)
        for col in range(7):
            d = monday + timedelta(days=col)
            cell = _DayCell(d, self._by_date.get(d, []))
            self._connect_cell(cell)
            grid.addWidget(cell, 1, col)
            grid.setColumnStretch(col, 1)
        grid.setRowStretch(1, 1)
        self._content_lay.addWidget(panel)
        self._content_lay.addStretch()

    def _build_day(self):
        d = self._anchor
        self._title_lbl.setText(
            f"{_DAY_ABBR[d.weekday()]}, {d.day}. {_MONTH_NAMES[d.month - 1]} {d.year}")
        t_list = self._by_date.get(d, [])
        if not t_list:
            from bowtally.ui.components.empty_state import EmptyState
            self._content_lay.addWidget(
                EmptyState("calendar", "Kein Turnier", "Kein Turnier an diesem Tag."))
        else:
            for t in t_list:
                self._content_lay.addWidget(self._day_card(t))
        self._content_lay.addStretch()

    def _month_panel(self, year: int, month: int) -> QWidget:
        """Proper week-based grid: each day gets a unique (week_row, weekday) position."""
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setSpacing(2)
        for col, name in enumerate(_DAY_ABBR):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setObjectName("calDayHeader")
            f = lbl.font()
            f.setBold(True)
            lbl.setFont(f)
            grid.addWidget(lbl, 0, col)
        first_wd = date(year, month, 1).weekday()   # 0 = Mon
        _, num_days = calendar.monthrange(year, month)
        for day in range(1, num_days + 1):
            slot = first_wd + day - 1
            row = slot // 7 + 1       # unique row per week
            col = slot % 7            # column = weekday
            d = date(year, month, day)
            cell = _DayCell(d, self._by_date.get(d, []))
            self._connect_cell(cell)
            grid.addWidget(cell, row, col)
        for c in range(7):
            grid.setColumnStretch(c, 1)
        return panel

    def _day_card(self, t) -> QFrame:
        """Full-width card for day-view (one per tournament)."""
        card = QFrame(frameShape=QFrame.Shape.StyledPanel, objectName="dayCell")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        name = QLabel(t.name)
        f = name.font()
        f.setBold(True)
        name.setFont(f)
        lay.addWidget(name)
        if getattr(t, "location", None):
            lay.addWidget(QLabel(t.location, objectName="pageSubtitle"))
        badge = _Badge(t)
        badge.clicked.connect(lambda _=False, tid=t.id: self._on_badge_click(tid))
        badge.hovered.connect(self._on_badge_hover)
        badge.unhovered.connect(self._on_badge_unhover)
        lay.addWidget(badge)
        return card

    def _connect_cell(self, cell: _DayCell):
        cell.tournamentClicked.connect(self._on_badge_click)
        cell.badgeHovered.connect(self._on_badge_hover)
        cell.badgeUnhovered.connect(self._on_badge_unhover)

    # ── hover card ──────────────────────────────────────────────────────────

    def _on_badge_hover(self, t, pos):
        self._pending_hover = (t, pos)
        self._hover_card.cancel_hide()
        self._hover_timer.start(400)

    def _on_badge_unhover(self):
        self._hover_timer.stop()
        self._hover_card.schedule_hide()

    def _do_show_hover(self):
        if self._pending_hover:
            t, pos = self._pending_hover
            self._hover_card.show_for(t, pos)

    def _on_badge_click(self, tid: int):
        self._hover_card.hide()
        self._hover_timer.stop()
        self.openTournament.emit(tid)

    # ── ICS export ──────────────────────────────────────────────────────────

    def _export_ics(self):
        from bowtally import config
        from bowtally.ui.components.toast import Toast
        from bowtally.ui.dialogs.export_helper import open_path
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//BowTally//BowTally//DE",
                 "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
        for t in self._tournaments:
            dtstart = t.date.strftime("%Y%m%d")
            dtend = (t.date + timedelta(1)).strftime("%Y%m%d")
            label = ts.PHASE_LABELS.get(t.phase, t.phase)
            lines += ["BEGIN:VEVENT",
                      f"UID:bowtally-{t.id}@bowtally",
                      f"DTSTART;VALUE=DATE:{dtstart}",
                      f"DTEND;VALUE=DATE:{dtend}",
                      f"SUMMARY:{_ics_esc(t.name)}",
                      f"DESCRIPTION:{_ics_esc(label + (' | ' + t.location if t.location else ''))}",
                      f"LOCATION:{_ics_esc(t.location or '')}",
                      "END:VEVENT"]
        lines.append("END:VCALENDAR")
        path = config.export_dir() / f"BowTally_Turniere_{datetime.now():%Y%m%d_%H%M%S}.ics"
        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        Toast.show(self, "ICS-Datei erstellt", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, path)))


def _ics_esc(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))

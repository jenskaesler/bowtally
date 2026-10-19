# -*- coding: utf-8 -*-
"""Dashboard: global overview, or - with an active tournament - the tournament dashboard."""
import os
from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import settings_service as svc
from bowtally.services import tournament_service as ts
from bowtally.ui import button
from bowtally.ui.components.capacity_bar import CapacityBar, ProgressBar
from bowtally.ui.components.data_table import Cell, DataTable
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.status_chip import StatusChip
from bowtally.ui.context import context
from bowtally.ui.views.guide_view import next_open_task
from bowtally.ui.views.participants_view import money

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
ACTIVE_LINKS = 3


def countdown(d: date) -> str:
    days = (d - date.today()).days
    if days == 0:
        return "heute"
    if days == 1:
        return "morgen"
    if days == -1:
        return "gestern"
    return f"in {days} Tagen" if days > 0 else f"vor {-days} Tagen"


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


def _clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear(item.layout())


class GlobalDashboard(QWidget):
    open_tournament = Signal(int, str)
    new_tournament = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        today = date.today()
        self.header = PageHeader("Dashboard", f"{WEEKDAYS[today.weekday()]}, {today:%d.%m.%Y}")
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
        self.no_club_lbl = QLabel(objectName="pageSubtitle")
        c.addWidget(self.archer_count)
        c.addWidget(self.club_count)
        c.addWidget(self.no_club_lbl)
        c.addStretch()
        grid.addWidget(card, 0, 1)

        card, c = _card("Nächstes Turnier")
        self.next_name = QLabel(objectName="emptyTitle")
        self.next_name.setWordWrap(True)
        self.next_meta = QLabel(objectName="pageSubtitle")
        self.next_chip = StatusChip()
        self.next_btn = button("Turnier öffnen", self._open_next, "primary", "Turnier öffnen")
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
        self._logo_lbl = QLabel()
        self._logo_lbl.setFixedSize(56, 56)
        self._logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_lbl.hide()
        self.header.add(self._logo_lbl)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        lay.addLayout(grid, 1)
        self._next_id = None
        self._activity = []

    def refresh(self):
        tournaments = ts.list_tournaments()
        active = [t for t in tournaments if t.phase != "closed"]
        self.active_count.setText(str(len(active)))
        _clear(self.active_links)
        for t in sorted(active, key=lambda t: t.date)[:ACTIVE_LINKS]:
            active_count = sum(ts.is_active_participant(p) for p in t.participants)
            cap = f"{active_count}/{t.max_participants}" if t.max_participants else str(active_count)
            self.active_links.addWidget(_link(
                f"{t.date:%d.%m.%Y}  {t.name}  ({cap})  →",
                lambda _=False, tid=t.id: self.open_tournament.emit(tid, ""),
                f"Turnier öffnen ({ts.PHASE_LABELS[t.phase]})  ·  {cap} Teilnehmer"))
        if not active:
            self.active_links.addWidget(QLabel("Kein laufendes Turnier", objectName="pageSubtitle"))
        archers = md.list_archers()
        clubs = {a.club.strip().lower() for a in archers if a.club and a.club.strip()}
        no_club = sum(1 for a in archers if not (a.club and a.club.strip()))
        self.archer_count.setText(str(len(archers)))
        self.club_count.setText(f"aktive Schützen aus {len(clubs)} Vereinen" if clubs
                                else "noch keine Vereine")
        self.no_club_lbl.setText(f"{no_club} ohne Vereinszugehörigkeit")
        self.no_club_lbl.setVisible(no_club > 0)
        logo_path = svc.get_club_profile().get("logo_path") or ""
        if logo_path and os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            self._logo_lbl.setPixmap(pix)
            self._logo_lbl.show()
        else:
            self._logo_lbl.clear()
            self._logo_lbl.hide()
        upcoming = sorted((t for t in active if t.date >= date.today()), key=lambda t: t.date)
        nxt = upcoming[0] if upcoming else None
        self._next_id = nxt.id if nxt else None
        if nxt:
            self.next_name.setText(nxt.name)
            self.next_meta.setText(f"{nxt.date:%d.%m.%Y} ({countdown(nxt.date)}) · "
                                   f"{nxt.location or 'Ort offen'}")
            self.next_chip.set_tournament_status(nxt.phase)
            self.next_btn.setText("Turnier öffnen")
            self.next_btn.setToolTip("Als aktives Turnier öffnen")
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


class TournamentDashboard(QWidget):
    action = Signal(str)       # direct links, handled by the main window

    def __init__(self, parent=None):
        super().__init__(parent)
        self.header = PageHeader("")
        self._logo_lbl = QLabel()
        self._logo_lbl.setFixedSize(56, 56)
        self._logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_lbl.hide()
        self.header.add(self._logo_lbl)
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        for col in range(3):
            self.grid.setColumnStretch(col, 1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        lay.addLayout(self.grid)
        lay.addStretch()

    def refresh(self):
        _clear(self.grid)
        t = context.tournament()
        if t is None:
            return
        logo_path = svc.get_club_profile().get("logo_path") or ""
        if logo_path and os.path.exists(logo_path):
            pix = QPixmap(logo_path).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            self._logo_lbl.setPixmap(pix)
            self._logo_lbl.show()
        else:
            self._logo_lbl.clear()
            self._logo_lbl.hide()
        self.header.set_title(t.name)
        self.header.set_subtitle(f"{t.date:%d.%m.%Y} ({countdown(t.date)}) · "
                                 f"{t.location or 'Ort offen'} · Phase "
                                 f"{ts.PHASE_LABELS[t.phase]}")
        stats = ts.get_tournament_stats(t.id)
        self.grid.addWidget(self._participants_card(t, stats), 0, 0)
        self.grid.addWidget(self._revenue_card(t), 0, 1)
        self.grid.addWidget(self._phase_card(t), 0, 2)
        show_progress = ts.phase_index(t.phase) >= ts.phase_index("shooting")
        if show_progress:
            self.grid.addWidget(self._progress_card(t), 1, 0)
        self.grid.addWidget(self._classes_card(t), 1, 1 if show_progress else 0,
                            1, 1 if show_progress else 2)
        self.grid.addWidget(self._schedule_card(t), 1, 2)

    def _participants_card(self, t, stats):
        card, c = _card("Teilnehmer")
        s = stats.by_status
        c.addWidget(QLabel(str(stats.total), objectName="cardValue"))
        c.addWidget(QLabel(f"{s['registered']} gemeldet · {s['confirmed']} bestätigt · "
                           f"{stats.paid} bezahlt · {s['checked_in']} eingecheckt",
                           objectName="pageSubtitle"))
        bar = CapacityBar()
        bar.set_capacity(stats.capacity)
        c.addWidget(bar)
        if s["registered"]:
            c.addWidget(QLabel(f"{s['registered']} Anmeldungen noch nicht bestätigt",
                               objectName="dangerText"))
        if ts.announcement_outdated(t):
            row = QHBoxLayout()
            row.addWidget(StatusChip("Ausschreibung veraltet", "warning"))
            row.addWidget(_link("Neu generieren", lambda: self.action.emit("announcement"),
                                "Ausschreibungs-PDF mit den aktuellen Daten erstellen"))
            row.addStretch()
            c.addLayout(row)
        c.addWidget(_link("Teilnehmerverwaltung →", lambda: self.action.emit("participants"),
                          "Teilnehmer öffnen"))
        c.addStretch()
        return card

    def _revenue_card(self, t):
        rev = ts.get_revenue_summary(t.id)
        card, c = _card("Einnahmen")
        c.addWidget(QLabel(money(rev.received), objectName="cardValue"))
        c.addWidget(QLabel(f"eingegangen von {money(rev.expected)} erwartet",
                           objectName="pageSubtitle"))
        c.addWidget(QLabel(f"Ausstehend: {money(rev.outstanding)}",
                           objectName="dangerText" if rev.outstanding > 0 else "successText"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(4)
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for col, head in enumerate(["Gebühr", "Anzahl", "Betrag", "Summe"]):
            grid.addWidget(QLabel(head, objectName="sectionTitle"), 0, col,
                           right if col else Qt.AlignmentFlag.AlignLeft)
        for r, row in enumerate(rev.rows, start=1):
            grid.addWidget(QLabel(row.name), r, 0)
            grid.addWidget(QLabel(str(row.count)), r, 1, right)
            grid.addWidget(QLabel(money(row.amount)), r, 2, right)
            total = QLabel(f"<b>{money(row.total)}</b>")
            grid.addWidget(total, r, 3, right)
        grid.setColumnStretch(0, 1)
        c.addLayout(grid)
        hint = QLabel("Erwartet: bestätigte und eingecheckte Teilnehmer mit Gebühr",
                      objectName="pageSubtitle")
        hint.setWordWrap(True)
        c.addWidget(hint)
        c.addStretch()
        return card

    def _progress_card(self, t):
        prog = ts.get_completion_progress(t.id)
        card, c = _card("Ergebnisfortschritt")
        c.addWidget(QLabel(f"{prog.percentage:.0f} %", objectName="cardValue"))
        bar = ProgressBar()
        bar.set_value(prog.percentage)
        c.addWidget(bar)
        c.addWidget(QLabel(f"{prog.entered} von {prog.needed} Wertungen",
                           objectName="pageSubtitle"))
        for cp in prog.per_class:
            row = QHBoxLayout()
            name = QLabel(cp.bow_class)
            name.setMinimumWidth(130)
            row.addWidget(name)
            cls_bar = ProgressBar()
            total = cp.checked_in or cp.participants
            cls_bar.set_value(cp.complete / total * 100 if total else 0)
            row.addWidget(cls_bar, 1)
            row.addWidget(QLabel(f"{cp.complete}/{total}"))
            c.addLayout(row)
        if prog.incomplete_ids:
            c.addWidget(_link(f"{len(prog.incomplete_ids)} unvollständige Teilnehmer anzeigen →",
                              lambda: self.action.emit("scoring_incomplete"),
                              "Ergebniseingabe gefiltert auf unvollständige Teilnehmer"))
        c.addStretch()
        return card

    def _phase_card(self, t):
        card, c = _card("Aktuelle Phase")
        chip = StatusChip()
        chip.set_tournament_status(t.phase)
        f = chip.font()
        f.setPointSize(12)
        chip.setFont(f)
        c.addWidget(chip)
        task = next_open_task(t.id)
        c.addWidget(QLabel("Nächste Aufgabe:", objectName="fieldLabel"))
        text = QLabel(task.text if task else "Alle Aufgaben dieser Phase sind erledigt.")
        text.setWordWrap(True)
        c.addWidget(text)
        c.addStretch()
        row = QHBoxLayout()
        row.addWidget(button("Zum Leitfaden", lambda: self.action.emit("guide"), "primary",
                             "Aufgaben und Voraussetzungen der aktuellen Phase"))
        row.addStretch()
        c.addLayout(row)
        return card

    def _classes_card(self, t):
        prog = ts.get_completion_progress(t.id)
        card, c = _card("Klassen")
        table = DataTable(["Klasse", "Angemeldet", "Eingecheckt", "Vollst. Ergebnisse"],
                          searchable_empty())
        table.set_rows([[cp.bow_class, cp.participants, cp.checked_in, cp.complete]
                        for cp in prog.per_class], list(range(len(prog.per_class))))
        c.addWidget(table, 1)
        return card

    def _schedule_card(self, t):
        card, c = _card("Zeitplan")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        rows = []
        if t.registration_deadline:
            open_ = t.registration_deadline >= date.today()
            rows.append(("Anmeldefrist", f"{t.registration_deadline:%d.%m.%Y}",
                         countdown(t.registration_deadline),
                         "successText" if open_ else "dangerText"))
        else:
            rows.append(("Anmeldefrist", "nicht gesetzt", "", "dangerText"))
        rows.append(("Turnierdatum", f"{t.date:%d.%m.%Y}", countdown(t.date), "successText"
                     if t.date >= date.today() else "pageSubtitle"))
        rows.append(("Einschreibung ab", f"{t.checkin_start_time or '–'} Uhr", "", ""))
        rows.append(("Schießbeginn", f"{t.shooting_start_time or '–'} Uhr", "", ""))
        for r, (label, value, hint, style) in enumerate(rows):
            grid.addWidget(QLabel(label, objectName="fieldLabel"), r, 0)
            grid.addWidget(QLabel(value), r, 1)
            if hint:
                grid.addWidget(QLabel(hint, objectName=style), r, 2)
        grid.setColumnStretch(2, 1)
        c.addLayout(grid)
        c.addStretch()
        return card


def searchable_empty() -> EmptyState:
    return EmptyState("inbox", "Noch keine Daten", "")


class DashboardView(QWidget):
    open_tournament = Signal(int, str)
    new_tournament = Signal()
    action = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.global_view = GlobalDashboard()
        self.tournament_view = TournamentDashboard()
        self.global_view.open_tournament.connect(self.open_tournament)
        self.global_view.new_tournament.connect(self.new_tournament)
        self.tournament_view.action.connect(self.action)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.global_view)
        self.stack.addWidget(self.tournament_view)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.stack)
        context.changed.connect(lambda _id: self.isVisible() and self.refresh())
        context.dataChanged.connect(lambda: self.isVisible() and self.refresh())

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        if context.tournament_id:
            self.stack.setCurrentWidget(self.tournament_view)
            self.tournament_view.refresh()
        else:
            self.stack.setCurrentWidget(self.global_view)
            self.global_view.refresh()

    def shortcut_new(self):
        self.new_tournament.emit()

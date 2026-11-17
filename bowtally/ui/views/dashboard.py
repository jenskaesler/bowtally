# -*- coding: utf-8 -*-
"""Dashboard: global overview, or - with an active tournament - the tournament dashboard."""
import json
import os
from datetime import date

from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QDrag, QPixmap
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from bowtally.services import course_service as cs
from bowtally.services import member_service as ms
from bowtally.services import inventory_service as inv_svc
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
CARD_DEFAULT_ORDER = [
    "active", "next", "archive",
    "archers", "rules", "bow_classes",
    "helpers", "inventory", "calendar",
]


class _DraggableCard(QFrame):
    swap = Signal(str)   # emits source key when this card is the drop target

    def __init__(self, key: str, parent=None):
        super().__init__(parent, objectName="card")
        self._key = key
        self._drag_pos = None
        self._did_drag = False
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.pos()
            self._did_drag = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_pos is not None
                and (event.pos() - self._drag_pos).manhattanLength() > 8):
            self._did_drag = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self._key)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._drag_pos = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        src = event.mimeData().text()
        if src != self._key:
            self.swap.emit(src)
        event.acceptProposedAction()


def countdown(d: date) -> str:
    days = (d - date.today()).days
    if days == 0:
        return "heute"
    if days == 1:
        return "morgen"
    if days == -1:
        return "gestern"
    return f"in {days} Tagen" if days > 0 else f"vor {-days} Tagen"


def _card(title: str, on_click=None) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame(objectName="card")
    if on_click is not None:
        frame.setCursor(Qt.CursorShape.PointingHandCursor)
        frame.mousePressEvent = lambda _e: on_click()
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 14, 18, 16)
    lay.setSpacing(6)
    lay.addWidget(QLabel(title, objectName="sectionTitle"))
    return frame, lay


def _dcard(key: str, title: str) -> tuple["_DraggableCard", QVBoxLayout]:
    frame = _DraggableCard(key)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(18, 14, 18, 16)
    lay.setSpacing(6)
    lay.addWidget(QLabel(title, objectName="sectionTitle"))
    return frame, lay


def _link(text: str, slot, tooltip: str) -> QPushButton:
    b = QPushButton(text, objectName="link")
    b.setToolTip(tooltip)
    b.clicked.connect(slot)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
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
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        today = date.today()
        self.header = PageHeader("Dashboard", f"{WEEKDAYS[today.weekday()]}, {today:%d.%m.%Y}")

        self._grid = QGridLayout()
        self._grid.setSpacing(16)
        self._cards: dict[str, _DraggableCard] = {}

        c, lay = _dcard("active", "Aktive Turniere")
        self.active_count = QLabel("0", objectName="cardValue")
        self.active_links = QVBoxLayout()
        self.active_links.setSpacing(0)
        lay.addWidget(self.active_count)
        lay.addLayout(self.active_links)
        lay.addStretch()
        self._cards["active"] = c

        c, lay = _dcard("next", "Nächstes Turnier")
        self.next_name = QLabel(objectName="emptyTitle")
        self.next_name.setWordWrap(True)
        self.next_meta = QLabel(objectName="pageSubtitle")
        self.next_chip = StatusChip()
        self.next_btn = button("Turnier öffnen", self._open_next, "primary", "Turnier öffnen")
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.next_btn)
        btn_row.addWidget(self.next_chip)
        btn_row.addStretch()
        lay.addWidget(self.next_name)
        lay.addWidget(self.next_meta)
        lay.addStretch()
        lay.addLayout(btn_row)
        self._cards["next"] = c

        c, lay = _dcard("archive", "Turnierarchiv")
        self.archive_count = QLabel("0", objectName="cardValue")
        lay.addWidget(self.archive_count)
        lay.addWidget(_link("Alle Turniere →", lambda: self.navigate.emit("tournaments"),
                            "Turnierliste öffnen"))
        lay.addStretch()
        self._cards["archive"] = c

        c, lay = _dcard("archers", "Schützen")
        self.archer_count = QLabel("0", objectName="cardValue")
        self.club_count = QLabel(objectName="pageSubtitle")
        self.no_club_lbl = QLabel(objectName="pageSubtitle")
        lay.addWidget(self.archer_count)
        lay.addWidget(self.club_count)
        lay.addWidget(self.no_club_lbl)
        lay.addWidget(_link("Schützen öffnen →", lambda: self.navigate.emit("archers"),
                            "Schützen verwalten"))
        lay.addStretch()
        self._cards["archers"] = c

        c, lay = _dcard("rules", "Regelwerke")
        self.rules_count = QLabel("0", objectName="cardValue")
        lay.addWidget(self.rules_count)
        lay.addWidget(_link("Regelwerke öffnen →", lambda: self.navigate.emit("rules"),
                            "Regelwerke verwalten"))
        lay.addStretch()
        self._cards["rules"] = c

        c, lay = _dcard("bow_classes", "Bogenklassen")
        self.bow_count = QLabel("0", objectName="cardValue")
        lay.addWidget(self.bow_count)
        lay.addWidget(_link("Bogenklassen öffnen →", lambda: self.navigate.emit("bow_classes"),
                            "Bogenklassen verwalten"))
        lay.addStretch()
        self._cards["bow_classes"] = c

        c, lay = _dcard("helpers", "Mitglieder")
        self.helpers_count = QLabel("0", objectName="cardValue")
        lay.addWidget(self.helpers_count)
        lay.addWidget(_link("Mitglieder öffnen →", lambda: self.navigate.emit("helpers"),
                            "Mitglieder verwalten"))
        lay.addStretch()
        self._cards["helpers"] = c

        c, lay = _dcard("inventory", "Inventar")
        self.inventory_count = QLabel("0", objectName="cardValue")
        self.inventory_value = QLabel(objectName="pageSubtitle")
        lay.addWidget(self.inventory_count)
        lay.addWidget(self.inventory_value)
        lay.addWidget(_link("Inventar öffnen →", lambda: self.navigate.emit("inventory"),
                            "Inventar verwalten"))
        lay.addStretch()
        self._cards["inventory"] = c

        c, lay = _dcard("calendar", "Kalender")
        self.upcoming_count = QLabel("0", objectName="cardValue")
        self.upcoming_lbl = QLabel(objectName="pageSubtitle")
        lay.addWidget(self.upcoming_count)
        lay.addWidget(self.upcoming_lbl)
        lay.addWidget(_link("Kalender öffnen →", lambda: self.navigate.emit("calendar"),
                            "Kalender öffnen"))
        lay.addStretch()
        self._cards["calendar"] = c

        for key, card in self._cards.items():
            card.swap.connect(lambda src, dst=key: self._on_card_swap(src, dst))

        saved = svc.get("dashboard_card_order")
        if saved:
            saved_order = [k for k in json.loads(saved) if k in self._cards]
            saved_order += [k for k in CARD_DEFAULT_ORDER if k not in saved_order]
            self._card_order = saved_order
        else:
            self._card_order = list(CARD_DEFAULT_ORDER)

        self._logo_lbl = QLabel()
        self._logo_lbl.setFixedSize(56, 56)
        self._logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo_lbl.hide()
        self.header.add(self._logo_lbl)

        self._last_label = QLabel(objectName="pageSubtitle")
        self._logbuch_btn = QPushButton("Logbuch →", objectName="link")
        self._logbuch_btn.clicked.connect(lambda: self.navigate.emit("logbuch"))
        act_row = QHBoxLayout()
        act_row.setContentsMargins(20, 4, 20, 8)
        act_row.addWidget(self._last_label, 1)
        act_row.addWidget(self._logbuch_btn)

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)
        main_lay.addWidget(self.header)
        main_lay.addLayout(self._grid, 1)
        main_lay.addLayout(act_row)

        self._rebuild_grid()
        self._next_id = None
        self._activity = []

    def refresh(self):
        tournaments = ts.list_tournaments()
        active = [t for t in tournaments if t.phase not in ("closed", "draft")]
        self.active_count.setText(str(len(active)))
        self.archive_count.setText(str(sum(t.phase == "closed" for t in tournaments)))
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
        self.rules_count.setText(str(len(sc.list_rules())))
        self.bow_count.setText(str(len(md.list_bow_classes())))
        helpers = ms.list_members(include_inactive=False, only_helpers=True)
        self.helpers_count.setText(str(len(helpers)))
        self.inventory_count.setText(str(len(inv_svc.list_items())))
        self.inventory_value.setText(f"Gesamtwert {money(inv_svc.inventory_total_value())}")
        upcoming_cal = [t for t in tournaments if t.date >= date.today()]
        self.upcoming_count.setText(str(len(upcoming_cal)))
        self.upcoming_lbl.setText(upcoming_cal[0].name if upcoming_cal
                                  else "Keine anstehenden Turniere")
        self._activity = sc.recent_scores()
        if self._activity:
            a = self._activity[0]
            ts_str = f"{a['entered_at']:%H:%M}" if a.get("entered_at") else ""
            self._last_label.setText(
                f"Zuletzt: Score Scheibe {a['target']}, {a['archer']}  – {ts_str}")
        else:
            self._last_label.setText("Noch keine Aktivität.")
        self.header.set_subtitle(
            f"{WEEKDAYS[date.today().weekday()]}, {date.today():%d.%m.%Y} · "
            f"{len(tournaments)} Turniere · {len(archers)} aktive Schützen")

    def _open_next(self):
        if self._next_id is None:
            self.new_tournament.emit()
        else:
            self.open_tournament.emit(self._next_id, "")

    def _rebuild_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().hide()
        for i, key in enumerate(self._card_order):
            card = self._cards.get(key)
            if card:
                self._grid.addWidget(card, i // 3, i % 3)
                card.show()
        for col in range(3):
            self._grid.setColumnStretch(col, 1)

    def _on_card_swap(self, src_key: str, dst_key: str):
        i = self._card_order.index(src_key)
        j = self._card_order.index(dst_key)
        self._card_order[i], self._card_order[j] = self._card_order[j], self._card_order[i]
        self._rebuild_grid()
        svc.set_value("dashboard_card_order", json.dumps(self._card_order))


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
        self.grid.addWidget(self._costs_card(t), 2, 0, 1, 3)
        if t.internal_notes:
            self.grid.addWidget(self._notes_card(t), 3, 0, 1, 3)

    def _costs_card(self, t):
        card, c = _card("Material", on_click=lambda: self.action.emit("course"))
        row = QHBoxLayout()
        for title, value, hint in (
                ("Kosten Einmalartikel", cs.one_off_cost(t.id),
                 "Für dieses Turnier angelegte Einmalposten, echte Zusatzkosten"),
                ("Warenwert Bestandsinventar", cs.stock_goods_value(t.id),
                 "Angeforderte Menge × Einzelpreis der verwendeten Inventarartikel, "
                 "bereits vorhanden")):
            col = QVBoxLayout()
            col.addWidget(QLabel(title, objectName="sectionTitle"))
            col.addWidget(QLabel(money(value), objectName="cardValue"))
            hint_label = QLabel(hint, objectName="pageSubtitle")
            hint_label.setWordWrap(True)
            col.addWidget(hint_label)
            row.addLayout(col, 1)
        c.addLayout(row)
        return card

    def _notes_card(self, t):
        card, c = _card("Notizen")
        text = QLabel(t.internal_notes)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        c.addWidget(text)
        return card

    def _participants_card(self, t, stats):
        card, c = _card("Teilnehmer", on_click=lambda: self.action.emit("participants"))
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
        card, c = _card("Einnahmen", on_click=lambda: self.action.emit("fees"))
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
        card, c = _card("Ergebnisfortschritt", on_click=lambda: self.action.emit("scoring"))
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
        card, c = _card("Aktuelle Phase", on_click=lambda: self.action.emit("guide"))
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
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.global_view = GlobalDashboard()
        self.tournament_view = TournamentDashboard()
        self.global_view.open_tournament.connect(self.open_tournament)
        self.global_view.new_tournament.connect(self.new_tournament)
        self.global_view.navigate.connect(self.navigate)
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

    def show_global(self):
        self.stack.setCurrentWidget(self.global_view)
        self.global_view.refresh()

    def show_tournament(self):
        if context.tournament_id:
            self.stack.setCurrentWidget(self.tournament_view)
            self.tournament_view.refresh()
        else:
            self.show_global()

    def refresh(self):
        if context.tournament_id:
            self.stack.setCurrentWidget(self.tournament_view)
            self.tournament_view.refresh()
        else:
            self.stack.setCurrentWidget(self.global_view)
            self.global_view.refresh()

    def shortcut_new(self):
        self.new_tournament.emit()

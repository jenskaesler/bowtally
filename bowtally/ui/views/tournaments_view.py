# -*- coding: utf-8 -*-
"""Tournament list and tournament detail (participants, check-in, score entry, results,
entry fees). Opening a tournament makes it the active tournament context."""
from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QStackedWidget, QTabWidget, QVBoxLayout, QWidget

from bowtally.services import tournament_service as ts
from bowtally.ui import button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.status_chip import StatusChip, tournament_chip
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.dialogs.tournament_wizard import TournamentWizard
from bowtally.ui.views import ListView
from bowtally.ui.views.checkin_view import CHECKIN_PHASES, CheckinView
from bowtally.ui.views.course_view import CourseView
from bowtally.ui.views.fees_view import FeesView
from bowtally.ui.views.participants_view import ParticipantsView
from bowtally.ui.views.prizes_view import PrizesView
from bowtally.ui.views.results_view import ResultsView
from bowtally.ui.views.schedule_view import ScheduleView
from bowtally.ui.views.scoring_view import ScoringView

HEADERS = ["Datum", "Name", "Ort", "Phase", "Teilnehmer", "Regelwerk"]
TABS = ["participants", "course", "schedule", "checkin", "scoring", "results", "prizes", "fees"]
TAB_LABELS = ["Teilnehmer", "Parcours", "Zeitplan", "Einschreibung",
              "Ergebniseingabe", "Auswertung", "Preise", "Startgebühren"]
CLOSED_HINT = "Abgeschlossene Turniere sind gesperrt"


class TournamentList(ListView):
    openRequested = Signal(int)
    changed = Signal()

    def __init__(self, parent=None):
        empty = EmptyState("target", "Noch keine Turniere",
                           "Der Assistent führt Schritt für Schritt durch die Anlage.",
                           "Neues Turnier")
        super().__init__("Turniere", HEADERS, empty, None, "Name, Ort oder Phase …")
        empty.actionTriggered.connect(self.new_item)
        self._show_closed = QCheckBox("Abgeschlossene Turniere anzeigen")
        _s = QSettings("BowTally", "BowTally")
        self._show_closed.setChecked(_s.value("tournaments/show_closed", False, type=bool))
        self._show_closed.toggled.connect(self.refresh)
        self._show_closed.toggled.connect(
            lambda v: QSettings("BowTally", "BowTally").setValue("tournaments/show_closed", v))
        self.header.add(button("Neues Turnier", self.new_item, "primary",
                               "Neues Turnier mit dem Assistenten anlegen (Strg+N)"))
        _footer = QWidget()
        _fl = QHBoxLayout(_footer)
        _fl.setContentsMargins(0, 4, 0, 0)
        _fl.addWidget(self._show_closed)
        _fl.addStretch()
        self.main_layout.insertWidget(2, _footer)
        self.table.activated.connect(self.openRequested.emit)
        self._items = {}

    def refresh(self):
        all_items = ts.list_tournaments()
        items = all_items if self._show_closed.isChecked() else [
            t for t in all_items if t.phase != "closed"]
        self._items = {t.id: t for t in all_items}
        self.table.set_rows([[t.date, Cell(t.name, bold=t.id == context.tournament_id),
                              t.location, Cell(t.phase, chip=tournament_chip(t.phase)),
                              len(t.participants),
                              t.scoring_rule.name if t.scoring_rule else None] for t in items],
                            [t.id for t in items])
        running = sum(t.phase != "closed" for t in all_items)
        self.header.set_subtitle(f"{len(all_items)} Turniere | {running} laufend"
                                 + (" | fett = geöffnet" if context.tournament_id else ""))
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return self._items.get(self.table.selected_id())

    def on_selection(self, ids):
        t = self._selected()
        if t is None:
            self.action_bar.set_actions("", [])
            return
        edit_locked = ts.phase_index(t.phase) >= ts.phase_index("checkin")
        self.action_bar.set_actions(t.name, [
            Action("Turnier öffnen", lambda: self.openRequested.emit(t.id),
                   tooltip="Als aktives Turnier öffnen: Leitfaden, Teilnehmer, Ergebnisse "
                           "(Enter)"),
            Action("Bearbeiten", self.edit_item, enabled=not edit_locked,
                   tooltip=CLOSED_HINT if t.status == "closed"
                   else ("Gesperrt ab Einschreibungsphase" if edit_locked
                         else "Turnierdaten im Assistenten bearbeiten")),
            Action("Kopieren", self.clone_item,
                   tooltip="Turnier als Vorlage kopieren (ohne Teilnehmer und Ergebnisse)"),
            Action("Löschen", self.delete_item, "danger",
                   tooltip="Turnier mit allen Teilnehmern und Ergebnissen löschen")])

    def context_entries(self, row_id):
        t = self._items.get(row_id)
        if t is None:
            return []
        edit_locked = ts.phase_index(t.phase) >= ts.phase_index("checkin")
        return [("Turnier öffnen", lambda: self.openRequested.emit(t.id)),
                ("Bearbeiten", self.edit_item, not edit_locked),
                ("Kopieren", self.clone_item),
                None,
                ("Löschen", self.delete_item)]

    def new_item(self):
        wiz = TournamentWizard(parent=self)
        if wiz.exec() and wiz.created_id:
            self.changed.emit()
            self.openRequested.emit(wiz.created_id)

    def edit_item(self):
        t = self._selected()
        if t is not None and ts.phase_index(t.phase) < ts.phase_index("checkin") and \
                TournamentWizard(ts.get_tournament(t.id), self).exec():
            self.refresh()
            self.changed.emit()

    def clone_item(self):
        t = self._selected()
        if t is None:
            return
        wiz = TournamentWizard(ts.get_tournament(t.id), clone=True, parent=self)
        if wiz.exec() and wiz.created_id:
            self.changed.emit()
            self.openRequested.emit(wiz.created_id)

    def delete_item(self):
        t = self._selected()
        if t is None:
            return
        text = f"„{t.name}“ wird endgültig gelöscht."
        if t.participants:
            text += f"\n\nDabei werden {len(t.participants)} Teilnehmer und alle erfassten " \
                    "Ergebnisse gelöscht."
        if not ConfirmDialog.ask(self, "Turnier löschen?", text):
            return
        try:
            ts.delete_tournament(t.id)
        except Exception as exc:
            show_error(self, exc)
            return
        if context.tournament_id == t.id:
            context.set(None)
        Toast.show(self, f"Turnier „{t.name}“ gelöscht", Toast.SUCCESS)
        self.refresh()
        self.changed.emit()


class TournamentDetail(QWidget):
    backRequested = Signal()
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = None
        self.header = PageHeader("")
        self.chip = StatusChip()
        self.header.add_title_widget(self.chip)
        self.btn_edit = button("Turnierdaten bearbeiten", self.edit,
                               tooltip="Alle Turnierdaten im Assistenten bearbeiten")
        self.header.add(button("Alle Turniere", self.backRequested.emit,
                               tooltip="Turnierliste anzeigen (das Turnier bleibt geöffnet)"),
                        self.btn_edit)
        self.pages = {"participants": ParticipantsView(), "course": CourseView(),
                      "schedule": ScheduleView(), "checkin": CheckinView(),
                      "scoring": ScoringView(), "results": ResultsView(),
                      "prizes": PrizesView(), "fees": FeesView()}
        self.participants, self.scoring = self.pages["participants"], self.pages["scoring"]
        self.results = self.pages["results"]
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        for key, label in zip(TABS, TAB_LABELS):
            self.tabs.addTab(self.pages[key], label)
        self.tabs.currentChanged.connect(lambda _i: self.reload())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        lay.addWidget(self.tabs, 1)
        context.dataChanged.connect(self._external_change)

    def open(self, tournament_id: int, tab: str | None = None) -> bool:
        self.current = ts.get_tournament(tournament_id)
        if self.current is None:
            return False
        self._update_tab_visibility()
        if tab in TABS and self.tabs.currentIndex() != TABS.index(tab):
            self.tabs.setCurrentIndex(TABS.index(tab))   # triggers reload
        else:
            self.reload()
        return True

    def _update_tab_visibility(self):
        phase = self.current.phase
        in_prep = ts.phase_index(phase) >= ts.phase_index("preparation")
        rules = {
            "course":   in_prep,
            "schedule": in_prep and not getattr(self.current, "use_draw", False),
            "checkin":  phase in CHECKIN_PHASES,
            "scoring":  phase in ("shooting", "scoring", "closed"),
            "results":  phase in ("scoring", "closed"),
            "prizes":   True,
            "fees":     phase in ("draft", "announcement"),
        }
        for key, visible in rules.items():
            self.tabs.setTabVisible(TABS.index(key), visible)
            if not visible and self.tabs.currentIndex() == TABS.index(key):
                self.tabs.setCurrentIndex(0)

    def _external_change(self):
        if self.current is not None and self.isVisible():
            self.reload(refresh_tab=False)

    def reload(self, refresh_tab: bool = True):
        if self.current is None:
            return
        t = self.current = ts.get_tournament(self.current.id)
        if t is None:
            return
        self._update_tab_visibility()
        self.header.set_title(t.name)
        self.chip.set_tournament_status(t.phase)
        self.header.set_subtitle(
            f"{t.date:%d.%m.%Y} · {t.location or 'Ort offen'} · "
            f"{t.scoring_rule.name if t.scoring_rule else '–'} · "
            f"{t.num_targets} Scheiben × {t.shots_per_target} Schuss · "
            f"{len(t.participants)} Teilnehmer")
        edit_locked = ts.phase_index(t.phase) >= ts.phase_index("checkin")
        self.btn_edit.setVisible(not edit_locked)
        if refresh_tab:
            self.tabs.currentWidget().set_tournament(t)

    def edit(self):
        self.edit_at_page(0)

    def edit_at_page(self, page: int):
        if self.current is not None and \
                TournamentWizard(ts.get_tournament(self.current.id),
                                 start_page=page, parent=self).exec():
            self.reload()
            self.changed.emit()


class TournamentsView(QWidget):
    changed = Signal()                # tournaments created / deleted / edited
    openRequested = Signal(int)       # make this tournament the active context

    def __init__(self, parent=None):
        super().__init__(parent)
        self.list = TournamentList()
        self.detail = TournamentDetail()
        self.list.openRequested.connect(self.openRequested)
        self.detail.backRequested.connect(self.show_list)
        self.list.changed.connect(self.changed)
        self.detail.changed.connect(self.changed)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.list)
        self.stack.addWidget(self.detail)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.stack)

    def showEvent(self, event):
        super().showEvent(event)
        if self.stack.currentWidget() is self.detail:
            self.detail.reload()

    def open_tournament(self, tournament_id, tab: str | None = None):
        if tournament_id is not None and self.detail.open(tournament_id, tab):
            self.stack.setCurrentWidget(self.detail)

    def show_list(self):
        self.stack.setCurrentWidget(self.list)
        self.list.refresh()

    def refresh(self):
        if self.stack.currentWidget() is self.detail:
            self.detail.reload()
        else:
            self.list.refresh()

    def _active_page(self):
        """Target for global shortcuts: the list, or the visible tab of the detail page."""
        if self.stack.currentWidget() is self.detail:
            return self.detail.tabs.currentWidget()
        return self.list

    def shortcut_new(self):
        page = self._active_page()
        if hasattr(page, "shortcut_new"):
            page.shortcut_new()

    def shortcut_find(self):
        page = self._active_page()
        if hasattr(page, "shortcut_find"):
            page.shortcut_find()

    def shortcut_save(self):
        page = self._active_page()
        if hasattr(page, "shortcut_save"):
            page.shortcut_save()

    def close_drawer(self) -> bool:
        page = self._active_page()
        return page.close_drawer() if hasattr(page, "close_drawer") else True

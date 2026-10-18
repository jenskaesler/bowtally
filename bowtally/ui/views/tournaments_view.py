# -*- coding: utf-8 -*-
"""Tournament list and tournament detail (participants, score entry, results)."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QTabWidget, QVBoxLayout, QWidget

from bowtally.services import tournament_service as ts
from bowtally.ui import button, show_error
from bowtally.ui.components.action_bar import Action
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.status_chip import StatusChip, tournament_chip
from bowtally.ui.components.toast import Toast
from bowtally.ui.dialogs.tournament_wizard import TournamentWizard
from bowtally.ui.views import ListView
from bowtally.ui.views.participants_view import ParticipantsView
from bowtally.ui.views.results_view import ResultsView
from bowtally.ui.views.scoring_view import ScoringView

HEADERS = ["Datum", "Name", "Ort", "Veranstalter", "Status", "Teilnehmer", "Regelwerk"]
STATUS_ACTIONS = {"draft": ("Turnier starten", "Status auf „Aktiv“ setzen"),
                  "active": ("Turnier abschließen",
                             "Status auf „Abgeschlossen“ setzen, danach keine Eingaben mehr")}
TABS = {"participants": 0, "scoring": 1, "results": 2}


class TournamentList(ListView):
    openRequested = Signal(int)
    changed = Signal()

    def __init__(self, parent=None):
        empty = EmptyState("target", "Noch keine Turniere",
                           "Der Assistent führt in fünf Schritten durch die Anlage.",
                           "Neues Turnier")
        super().__init__("Turniere", HEADERS, empty, None, "Name, Ort oder Status …")
        empty.actionTriggered.connect(self.new_item)
        self.header.add(button("Neues Turnier", self.new_item, "primary",
                               "Neues Turnier mit dem Assistenten anlegen (Strg+N)"))
        self.table.activated.connect(self.openRequested.emit)
        self._items = {}

    def refresh(self):
        items = ts.list_tournaments()
        self._items = {t.id: t for t in items}
        self.table.set_rows([[t.date, t.name, t.location, t.organizer,
                              Cell(t.status, chip=tournament_chip(t.status)),
                              len(t.participants),
                              t.scoring_rule.name if t.scoring_rule else None] for t in items],
                            [t.id for t in items])
        active = sum(t.status == "active" for t in items)
        self.header.set_subtitle(f"{len(items)} Turniere | {active} aktiv")
        self.on_selection(self.table.selected_ids())

    def _selected(self):
        return self._items.get(self.table.selected_id())

    def on_selection(self, ids):
        t = self._selected()
        if t is None:
            self.action_bar.set_actions("", [])
            return
        closed = t.status == "closed"
        self.action_bar.set_actions(t.name, [
            Action("Öffnen", lambda: self.openRequested.emit(t.id),
                   tooltip="Teilnehmer, Ergebniseingabe und Auswertung (Enter)"),
            Action("Bearbeiten", self.edit_item, enabled=not closed,
                   tooltip="Abgeschlossene Turniere sind gesperrt" if closed
                   else "Turnierdaten im Assistenten bearbeiten"),
            Action("Löschen", self.delete_item, "danger",
                   tooltip="Turnier mit allen Teilnehmern und Ergebnissen löschen")])

    def context_entries(self, row_id):
        t = self._items.get(row_id)
        if t is None:
            return []
        closed = t.status == "closed"
        return [("Öffnen", lambda: self.openRequested.emit(t.id)),
                ("Bearbeiten", self.edit_item, not closed, "Abgeschlossene Turniere sind gesperrt"),
                None,
                ("Löschen", self.delete_item)]

    def new_item(self):
        wiz = TournamentWizard(parent=self)
        if wiz.exec() and wiz.created_id:
            self.changed.emit()
            self.openRequested.emit(wiz.created_id)

    def edit_item(self):
        t = self._selected()
        if t is not None and t.status != "closed" and \
                TournamentWizard(ts.get_tournament(t.id), self).exec():
            self.refresh()
            self.changed.emit()

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
        self.btn_edit = button("Turnierdaten bearbeiten", self._edit,
                               tooltip="Grunddaten, Regelwerk, Klassen und Parcours ändern")
        self.btn_status = button("", self._advance_status)
        self.header.add(button("Alle Turniere", self.backRequested.emit,
                               tooltip="Zurück zur Turnierliste"),
                        self.btn_edit, self.btn_status)
        self.participants = ParticipantsView()
        self.scoring = ScoringView()
        self.results = ResultsView()
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.participants, "Teilnehmer")
        self.tabs.addTab(self.scoring, "Ergebniseingabe")
        self.tabs.addTab(self.results, "Auswertung")
        self.tabs.currentChanged.connect(lambda _i: self.reload())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.header)
        lay.addWidget(self.tabs, 1)

    def open(self, tournament_id: int, tab: str | None = None) -> bool:
        self.current = ts.get_tournament(tournament_id)
        if self.current is None:
            return False
        if tab in TABS and self.tabs.currentIndex() != TABS[tab]:
            self.tabs.setCurrentIndex(TABS[tab])   # triggers reload
        else:
            self.reload()
        return True

    def reload(self):
        if self.current is None:
            return
        t = self.current = ts.get_tournament(self.current.id)
        self.header.set_title(t.name)
        self.chip.set_tournament_status(t.status)
        self.header.set_subtitle(
            f"{t.date:%d.%m.%Y} · {t.location or 'Ort offen'} · "
            f"{t.scoring_rule.name if t.scoring_rule else '–'} · "
            f"{t.num_targets} Scheiben × {t.shots_per_target} Schuss · "
            f"{len(t.participants)} Teilnehmer")
        action = STATUS_ACTIONS.get(t.status)
        self.btn_status.setVisible(action is not None)
        if action:
            self.btn_status.setText(action[0])
            self.btn_status.setToolTip(action[1])
        closed = t.status == "closed"
        self.btn_edit.setEnabled(not closed)
        self.btn_edit.setToolTip("Abgeschlossene Turniere sind gesperrt" if closed
                                 else "Grunddaten, Regelwerk, Klassen und Parcours ändern")
        self.tabs.currentWidget().set_tournament(t)

    def _edit(self):
        if TournamentWizard(self.current, self).exec():
            self.reload()
            self.changed.emit()

    def _advance_status(self):
        t = self.current
        new = ts.STATUS_NEXT.get(t.status)
        if new == "closed":
            ok = ConfirmDialog.ask(self, "Turnier abschließen?",
                                   "Danach sind keine Eingaben und Änderungen mehr möglich. "
                                   "Die Ergebnisliste bleibt verfügbar.", "Abschließen")
        else:
            ok = ConfirmDialog.ask(self, "Turnier starten?",
                                   "Das Turnier erhält den Status „Aktiv“. Die Ergebnisliste "
                                   "kann ab jetzt erstellt werden.", "Starten",
                                   destructive=False)
        if not ok:
            return
        try:
            ts.set_status(t.id, new)
        except Exception as exc:
            show_error(self, exc)
            return
        Toast.show(self, f"Status: {ts.STATUS_LABELS[new]}", Toast.SUCCESS)
        self.reload()
        self.changed.emit()


class TournamentsView(QWidget):
    changed = Signal()      # tournaments created / deleted / status changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.list = TournamentList()
        self.detail = TournamentDetail()
        self.list.openRequested.connect(self.open_tournament)
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

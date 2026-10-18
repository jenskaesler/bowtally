# -*- coding: utf-8 -*-
"""Tournament list and tournament detail (participants, score entry, results)."""
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QStackedWidget, QTabWidget, QVBoxLayout,
                               QWidget)

from bowtally.services import tournament_service as ts
from bowtally.ui import button, confirm
from bowtally.ui.dialogs.tournament_wizard import TournamentWizard
from bowtally.ui.views import page_title
from bowtally.ui.views.participants_view import ParticipantsView
from bowtally.ui.views.results_view import ResultsView
from bowtally.ui.views.scoring_view import ScoringView
from bowtally.ui.widgets.sortable_table import SortableTable

HEADERS = ["Datum", "Name", "Ort", "Veranstalter", "Status", "Teilnehmer", "Regelwerk"]
STATUS_ACTIONS = {"draft": "Turnier starten", "active": "Turnier abschließen"}


class TournamentsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = None
        self.stack = QStackedWidget()
        self.stack.addWidget(self._list_page())
        self.stack.addWidget(self._detail_page())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.stack)

    # ------------------------------------------------------------ list
    def _list_page(self) -> QWidget:
        w = QWidget()
        self.table = SortableTable(HEADERS)
        self.table.activated.connect(self.open_tournament)
        bar = QHBoxLayout()
        bar.addWidget(button("Neues Turnier ...", self._new, "primary"))
        bar.addWidget(button("Öffnen", lambda: self.open_tournament(self.table.selected_id())))
        bar.addWidget(button("Löschen", self._delete, "danger"))
        bar.addStretch()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(page_title("Turniere"))
        lay.addLayout(bar)
        lay.addWidget(self.table, 1)
        return w

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        if self.stack.currentIndex() == 1 and self.current is not None:
            self._reload()
            return
        items = ts.list_tournaments()
        self.table.set_rows([[t.date, t.name, t.location, t.organizer,
                              ts.STATUS_LABELS[t.status], len(t.participants),
                              t.scoring_rule.name if t.scoring_rule else None] for t in items],
                            [t.id for t in items])

    def _new(self):
        wiz = TournamentWizard(parent=self)
        if wiz.exec() and wiz.created_id:
            self.open_tournament(wiz.created_id)

    def _delete(self):
        tid = self.table.selected_id()
        t = ts.get_tournament(tid) if tid else None
        if t is None:
            return
        text = f"Turnier '{t.name}' mit {len(t.participants)} Teilnehmern löschen?"
        if t.participants:
            text += "\n\nAlle Teilnehmer und Ergebnisse dieses Turniers werden gelöscht!"
        if confirm(self, text):
            ts.delete_tournament(tid)
            self.refresh()

    # ------------------------------------------------------------ detail
    def _detail_page(self) -> QWidget:
        w = QWidget()
        self.title = page_title("")
        self.meta = QLabel()
        self.meta.setProperty("secondary", True)
        self.btn_status = button("", self._advance_status, "primary")
        self.btn_edit = button("Turnierdaten bearbeiten ...", self._edit)
        head = QHBoxLayout()
        head.addWidget(button("< Alle Turniere", self._back))
        head.addStretch()
        head.addWidget(self.btn_edit)
        head.addWidget(self.btn_status)
        self.participants = ParticipantsView()
        self.scoring = ScoringView()
        self.results = ResultsView()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.participants, "Teilnehmer")
        self.tabs.addTab(self.scoring, "Ergebniseingabe")
        self.tabs.addTab(self.results, "Auswertung")
        self.tabs.currentChanged.connect(lambda _i: self._reload())
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(head)
        lay.addWidget(self.title)
        lay.addWidget(self.meta)
        lay.addWidget(self.tabs, 1)
        return w

    def open_tournament(self, tournament_id):
        if tournament_id is None:
            return
        self.current = ts.get_tournament(tournament_id)
        if self.current is None:
            return
        self.stack.setCurrentIndex(1)
        self._reload()

    def _reload(self):
        t = self.current = ts.get_tournament(self.current.id)
        self.title.setText(t.name)
        self.meta.setText(f"{t.date:%d.%m.%Y} · {t.location or '-'} · "
                          f"{t.scoring_rule.name if t.scoring_rule else '-'} · "
                          f"{t.num_targets} Scheiben × {t.shots_per_target} Schuss · "
                          f"Status: {ts.STATUS_LABELS[t.status]}")
        action = STATUS_ACTIONS.get(t.status)
        self.btn_status.setVisible(action is not None)
        self.btn_status.setText(action or "")
        self.btn_edit.setEnabled(t.status != "closed")
        self.tabs.currentWidget().set_tournament(t)

    def _back(self):
        self.stack.setCurrentIndex(0)
        self.current = None
        self.refresh()

    def _edit(self):
        if TournamentWizard(self.current, self).exec():
            self._reload()

    def _advance_status(self):
        t = self.current
        new = ts.STATUS_NEXT.get(t.status)
        if new == "closed" and not confirm(
                self, "Turnier abschließen?\n\nDanach sind keine Eingaben und Änderungen mehr "
                      "möglich.", "Turnier abschließen"):
            return
        if new == "active" and not confirm(self, "Turnier starten (Status 'Aktiv')?"):
            return
        ts.set_status(t.id, new)
        self._reload()

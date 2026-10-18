# -*- coding: utf-8 -*-
"""The active tournament ("tournament context"), shared by sidebar, dashboard and views.

Persisted in app_settings so it survives a restart.
"""
from PySide6.QtCore import QObject, Signal

from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts

SETTING_KEY = "last_active_tournament_id"


class TournamentContext(QObject):
    changed = Signal(object)      # tournament id or None
    dataChanged = Signal()        # phase / participants / fees changed -> refresh displays

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament_id: int | None = None

    def restore(self) -> None:
        value = ss.get(SETTING_KEY, "") or ""
        if value.isdigit() and ts.get_tournament(int(value)) is not None:
            self.tournament_id = int(value)

    def set(self, tournament_id: int | None) -> None:
        if tournament_id is not None and ts.get_tournament(tournament_id) is None:
            tournament_id = None
        self.tournament_id = tournament_id
        ss.set_value(SETTING_KEY, "" if tournament_id is None else str(tournament_id))
        self.changed.emit(tournament_id)

    def tournament(self):
        return ts.get_tournament(self.tournament_id) if self.tournament_id else None

    def notify(self) -> None:
        self.dataChanged.emit()


# one instance per application (created on import, like the theme notifier)
context = TournamentContext()

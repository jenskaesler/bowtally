# -*- coding: utf-8 -*-
import datetime

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _announced_tournament(tmp_path, monkeypatch, use_draw):
    from bowtally import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    from bowtally.database.engine import init_database
    init_database()
    from bowtally.services import master_data_service as md, settings_service as ss
    from bowtally.services import tournament_service as ts
    t = ts.save_tournament({"name": "T", "date": datetime.date.today(), "num_targets": 1,
                            "scoring_rule_id": int(ss.get("default_scoring_rule_id"))},
                           [bc.id for bc in md.list_bow_classes()])
    from bowtally.database.engine import session_scope
    from bowtally.database.models import Tournament
    with session_scope() as session:      # save_tournament does not persist use_draw
        session.get(Tournament, t.id).use_draw = use_draw
    ts.transition_phase(t.id, "announcement", force=True)
    return t


def _visible_tabs(detail):
    from bowtally.ui.views.tournaments_view import TABS
    return {TABS[i] for i in range(detail.tabs.count()) if detail.tabs.isTabVisible(i)}


@pytest.mark.parametrize("use_draw", [False, True])
def test_phase_change_hides_fees_and_loads_new_current_tab(tmp_path, monkeypatch, app, use_draw):
    t = _announced_tournament(tmp_path, monkeypatch, use_draw)
    from bowtally.services import tournament_service as ts
    from bowtally.ui.views.tournaments_view import TournamentDetail
    detail = TournamentDetail()
    detail.open(t.id, "fees")

    loaded = []
    for key, page in detail.pages.items():
        monkeypatch.setattr(page, "set_tournament", lambda _t, key=key: loaded.append(key))
    ts.transition_phase(t.id, "preparation", force=True)
    detail.reload(refresh_tab=False)      # what a context.dataChanged signal triggers
    app.processEvents()

    visible = _visible_tabs(detail)
    assert "fees" not in visible and "course" in visible
    assert ("schedule" in visible) is (not use_draw)
    assert detail.tabs.isTabVisible(detail.tabs.currentIndex())
    assert loaded == [list(detail.pages)[detail.tabs.currentIndex()]]

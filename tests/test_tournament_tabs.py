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
    assert detail.tabs.currentIndex() == 0      # hidden current tab -> first tab, not Qt's pick
    assert loaded == [list(detail.pages)[detail.tabs.currentIndex()]]


def test_phase_change_while_page_hidden_leaves_no_gap_in_tab_bar(tmp_path, monkeypatch, app):
    t = _announced_tournament(tmp_path, monkeypatch, use_draw=False)
    from bowtally.services import tournament_service as ts
    from bowtally.ui import theme
    from bowtally.ui.views.tournaments_view import TournamentDetail
    theme.apply(app)
    detail = TournamentDetail()
    detail.resize(1100, 700)
    detail.show()
    detail.open(t.id)
    app.processEvents()

    detail.hide()                       # user is on another page when the phase changes
    ts.transition_phase(t.id, "preparation", force=True)
    detail.reload()
    detail.show()
    app.processEvents()

    bar = detail.tabs.tabBar()
    rects = [bar.tabRect(i) for i in range(bar.count()) if bar.isTabVisible(i)]
    assert [b.left() - a.right() - 1 for a, b in zip(rects, rects[1:])] == [0] * (len(rects) - 1)


@pytest.mark.parametrize("page_name, expected_loads", [("guide", 0), ("tournaments", 1)])
def test_next_phase_reloads_the_active_tab_at_most_once(tmp_path, monkeypatch, app,
                                                        page_name, expected_loads):
    t = _announced_tournament(tmp_path, monkeypatch, use_draw=False)
    from bowtally.ui.components.confirm_dialog import ConfirmDialog
    from bowtally.ui.context import context
    from bowtally.ui.main_window import MainWindow
    monkeypatch.setattr(ConfirmDialog, "ask", staticmethod(lambda *a, **k: True))
    context.set(t.id)
    win = MainWindow()
    win.show()
    win.select_page(win.tournaments)
    win.select_page(getattr(win, page_name))
    app.processEvents()
    loaded = []
    for page in win.tournaments.detail.pages.values():
        monkeypatch.setattr(page, "set_tournament", lambda _t: loaded.append(1))

    win.next_phase()

    assert len(loaded) == expected_loads
    context.set(None)

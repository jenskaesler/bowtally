# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])


def _gap(view, controls, first_list_widget) -> int:
    from PySide6.QtWidgets import QApplication
    view.resize(1200, 800)
    view.show()
    QApplication.processEvents()
    bottom = max(w.mapTo(view, w.rect().bottomLeft()).y() + 1 for w in controls)
    gap = first_list_widget.mapTo(view, first_list_widget.rect().topLeft()).y() - bottom
    view.hide()
    return gap


def test_control_bar_to_list_gap_is_the_same_in_all_views():
    from bowtally.ui.views import BAR_BOTTOM_MARGIN
    from bowtally.ui.views.checkin_view import CheckinView
    from bowtally.ui.views.participants_view import ParticipantsView
    from bowtally.ui.views.results_view import ResultsView
    from bowtally.ui.views.scoring_view import ScoringView
    expected = 10 + BAR_BOTTOM_MARGIN      # layout spacing + bar margin = 26 px, as under a ListView header
    part, check, score, results = ParticipantsView(), CheckinView(), ScoringView(), ResultsView()
    assert _gap(part, [part.search, part.btn_add, part.group_filter, part.capacity], part.table) == expected
    assert _gap(check, [check.not_found], check.table) == expected
    assert _gap(score, [score.search, score.save_btn, score.group_filter], score.class_tabs) == expected
    assert _gap(results, [results.btn_pdf, results.btn_export], results.tabs) == expected

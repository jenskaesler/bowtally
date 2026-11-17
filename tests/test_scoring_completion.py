# -*- coding: utf-8 -*-
from datetime import date

import pytest

from bowtally.database import engine
from bowtally.services import ValidationError
from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 's.db').as_posix()}")


def _tournament_with_starter(mode: str, num_rounds: int = 1, num_targets: int = 3, shots: int = 1):
    rule = sc.list_rules()[0]
    t = ts.save_tournament({"name": "T", "date": date(2026, 5, 1), "num_targets": num_targets,
                            "shots_per_target": shots, "scoring_rule_id": rule.id,
                            "scoring_mode": mode, "num_rounds": num_rounds},
                           [md.list_bow_classes()[0].id])
    archer = md.save_archer({"first_name": "A", "last_name": "B"})
    ts.add_participants(t.id, [archer.id])
    return t, ts.get_tournament(t.id).participants[0].id


def _incomplete(t):
    return ts.get_completion_progress(t.id).incomplete_ids


def _scoring_warnings(t):
    return [c.message for c in ts.get_phase_conditions(t.id, "scoring")
            if c.severity == "warning" and not c.ok]


def test_total_only_needs_exactly_one_value():
    t, pid = _tournament_with_starter("total_only")
    assert _incomplete(t) == [pid]
    sc.set_score(pid, 0, 1, (250, None), round_number=0)
    assert _incomplete(t) == [] and _scoring_warnings(t) == []
    progress = ts.get_completion_progress(t.id)
    assert (progress.entered, progress.needed) == (1, 1)


def test_per_round_needs_one_value_per_round():
    t, pid = _tournament_with_starter("per_round", num_rounds=2)
    sc.set_score(pid, 0, 1, (100, None), round_number=1)
    assert _incomplete(t) == [pid]
    sc.set_score(pid, 0, 1, (90, None), round_number=2)
    assert _incomplete(t) == [] and _scoring_warnings(t) == []


def test_multi_round_per_target_needs_every_shot_of_every_round():
    t, pid = _tournament_with_starter("per_target", num_rounds=2, num_targets=1, shots=1)
    zone = sc.list_rules()[0].ring_values[0]
    sc.set_score(pid, 1, 1, (zone["points"], zone["zone"]), round_number=1)
    assert _incomplete(t) == [pid]
    sc.set_score(pid, 1, 1, (zone["points"], zone["zone"]), round_number=2)
    assert _incomplete(t) == []


def test_per_target_message_keeps_its_wording():
    t, _ = _tournament_with_starter("per_target")
    assert _scoring_warnings(t) == ["1 Teilnehmer haben unvollständige Scheibenergebnisse"]


def test_negative_total_is_refused_by_the_service():
    _, pid = _tournament_with_starter("total_only")
    with pytest.raises(ValidationError):
        sc.set_score(pid, 0, 1, (-5, None), round_number=0)


@pytest.fixture
def app(monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from bowtally.ui.views import scoring_view

    app = QApplication.instance() or QApplication([])
    app.errors = []     # a real error dialog is modal and would hang the test
    monkeypatch.setattr(scoring_view, "show_error", lambda _parent, exc, *_: app.errors.append(exc))
    return app


def _view_for(t, app):
    from bowtally.ui.views.scoring_view import ScoringView
    view = ScoringView()
    view._mark_saved = lambda: None     # needs the main window's status bar
    view.set_tournament(ts.get_tournament(t.id))
    return view


def test_total_table_accepts_digits_only(app):
    from PySide6.QtGui import QValidator
    t, _ = _tournament_with_starter("total_only")
    table = _view_for(t, app)._simple_table
    editor = table.itemDelegate().createEditor(table, None, table.model().index(0, 4))
    check = lambda text: editor.validator().validate(text, len(text))[0]  # noqa: E731
    assert check("250") == QValidator.State.Acceptable
    for bad in ("12a", "-5", "1,5", "+3"):
        assert check(bad) == QValidator.State.Invalid, bad


def test_total_entry_is_saved_and_incomplete_filter_hides_complete_rows(app):
    t, first = _tournament_with_starter("total_only")
    second = md.save_archer({"first_name": "C", "last_name": "D"})
    ts.add_participants(t.id, [second.id])
    view = _view_for(t, app)
    view._simple_table.item(0, 4).setText("250")
    scores = sc.get_all_scores(t.id)
    assert app.errors == [] and [s.points for s in scores.values()] == [250]
    view.show_incomplete()
    assert [view._simple_table.isRowHidden(r) for r in range(2)] == [True, False]

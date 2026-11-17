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


def _kill_rule():
    """3D rule that counts kills and uses them as tie-break (the built-in IBO rules do not)."""
    return sc.save_rule({"name": "Kill-Regelwerk", "max_shots_per_target": 1,
                         "ring_values": [{"zone": "Kill", "points": 10, "type": "kill"},
                                         {"zone": "Körper", "points": 5},
                                         {"zone": "Miss", "points": 0, "type": "miss"}],
                         "tracked_specials": [{"key": "kill", "label": "Kill", "track": True,
                                               "tiebreak": True}],
                         "rules_json": {"discipline": "3d", "tiebreak": "most_top_scores"}})


def _tournament_with_starter(mode: str, num_rounds: int = 1, num_targets: int = 3, shots: int = 1):
    rule = _kill_rule()
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
    zone = {"zone": "Kill", "points": 10}
    sc.set_score(pid, 1, 1, (zone["points"], zone["zone"]), round_number=1)
    assert _incomplete(t) == [pid]
    sc.set_score(pid, 1, 1, (zone["points"], zone["zone"]), round_number=2)
    assert _incomplete(t) == []


def test_per_target_message_keeps_its_wording():
    t, _ = _tournament_with_starter("per_target")
    assert _scoring_warnings(t) == ["1 Teilnehmer haben unvollständige Zielergebnisse"]


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


def test_total_table_has_a_kill_column_that_needs_points_first(app):
    t, pid = _tournament_with_starter("total_only")
    view = _view_for(t, app)
    table = view._simple_table
    assert table.horizontalHeaderItem(5).text() == "Kill"
    table.item(0, 5).setText("3")                  # no points yet -> refused, nothing stored
    assert len(app.errors) == 1 and sc.get_all_scores(t.id) == {}
    app.errors.clear()
    view = _view_for(t, app)
    view._simple_table.item(0, 4).setText("200")
    view._simple_table.item(0, 5).setText("3")
    assert app.errors == [] and sc.get_all_scores(t.id)[(pid, 0, 0, 1)].specials == {"kill": 3}
    view._simple_table.item(0, 4).setText("")      # clearing the points clears the kills too
    assert sc.get_all_scores(t.id) == {} and view._simple_table.item(0, 5).text() == ""


def test_per_round_table_sums_points_and_kills_over_rounds(app):
    t, pid = _tournament_with_starter("per_round", num_rounds=2)
    view = _view_for(t, app)
    table = view._simple_table
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    assert headers[4:] == ["1. Runde", "1. Runde Kill", "2. Runde", "2. Runde Kill",
                           "Gesamt", "Kill gesamt"]
    for col, value in ((4, "100"), (5, "2"), (6, "90"), (7, "1")):
        table.item(0, col).setText(value)
    assert app.errors == []
    assert (table.item(0, 8).text(), table.item(0, 9).text()) == ("190", "3")


@pytest.mark.parametrize("mode", ["total_only", "per_round"])
def test_results_view_and_pdf_show_the_kill_column(app, tmp_path, monkeypatch, mode):
    from bowtally.reports import result_list
    from bowtally.ui.views.results_view import ResultsView
    t, first = _tournament_with_starter(mode)
    second = md.save_archer({"first_name": "C", "last_name": "D"})
    ts.add_participants(t.id, [second.id])
    for pid, kills in zip((p.id for p in ts.get_tournament(t.id).participants), (3, 5)):
        sc.set_score(pid, 0, 1, (200, None), round_number=0 if mode == "total_only" else 1)
        sc.set_special(pid, 0 if mode == "total_only" else 1, "kill", kills)

    view = ResultsView()
    view.set_tournament(ts.get_tournament(t.id))
    _title, headers, rows = view.sheets[0]
    assert headers[-2:] == ["Kill", "Gesamt"]
    assert [r[-2] for r in rows] == [5, 3]            # more kills first, same points

    tables = []
    original = result_list.Table
    monkeypatch.setattr(result_list, "Table", lambda data, *a, **k: tables.append(data)
                        or original(data, *a, **k))
    result_list.build_result_list(t.id, tmp_path / "r.pdf")
    assert any(data[0][-2:] == ["Kill", "Gesamt"] and data[1][-2] == "5" for data in tables)


def _grouped_tournament(mode):
    rule = _kill_rule()
    t = ts.save_tournament({"name": "G", "date": date(2026, 5, 1), "num_targets": 1,
                            "shots_per_target": 1, "scoring_rule_id": rule.id, "scoring_mode": mode,
                            "start_groups": "A, B"}, [md.list_bow_classes()[0].id])
    ts.add_participants(t.id, [md.save_archer({"first_name": n, "last_name": "Test"}).id
                               for n in ("Anna", "Bernd")])
    return t


@pytest.mark.parametrize("mode", ["total_only", "per_round", "per_target"])
def test_every_scoring_mode_has_search_save_group_and_incomplete_filter(app, mode):
    t = _grouped_tournament(mode)
    view = _view_for(t, app)
    for widget in (view.search, view.save_btn, view.group_filter, view.incomplete_only, view.class_tabs):
        assert widget.isVisibleTo(view), mode
    assert view.group_filter.count() == 3                      # Alle Gruppen, A, B
    table = view._simple_table if mode != "per_target" else view.mid
    hidden = lambda: [table.isRowHidden(r) for r in range(2)]  # noqa: E731
    assert hidden() == [False, False]
    view.group_filter.setCurrentIndex(view.group_filter.findData("B"))
    assert hidden().count(True) == 1
    view.group_filter.setCurrentIndex(0)
    view.search.setText("bernd")
    view.search.searchChanged.emit("bernd")                    # skip the debounce timer
    assert hidden().count(True) == 1
    view.search.clear()
    view.search.searchChanged.emit("")
    assert hidden() == [False, False]


def test_save_button_works_in_the_simple_table(app):
    t, _ = _tournament_with_starter("total_only")
    view = _view_for(t, app)
    view.save()
    assert app.errors == []

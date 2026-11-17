# -*- coding: utf-8 -*-
from datetime import date

import pytest

from bowtally.database import engine
from bowtally.services import ValidationError
from bowtally.services import master_data_service as md
from bowtally.services import ranking_service as rs
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'so.db').as_posix()}")


def _tied_tournament(shoot_off=True, tag=""):
    rule = sc.save_rule({"name": f"Eigenes 3D {tag}", "max_shots_per_target": 1, "tracked_specials": [],
                         "ring_values": [{"zone": "Treffer", "points": 10}, {"zone": "Miss", "points": 0}],
                         "rules_json": {"discipline": "3d", "tiebreak": "total_highest",
                                        "shoot_off": shoot_off}})
    t = ts.save_tournament({"name": "T", "date": date(2026, 5, 1), "num_targets": 1,
                            "shots_per_target": 1, "scoring_rule_id": rule.id,
                            "scoring_mode": "total_only"}, [md.list_bow_classes()[0].id])
    ts.add_participants(t.id, [md.save_archer({"first_name": f"P{i}", "last_name": f"X{tag}"}).id
                               for i in range(2)])
    first, second = sorted(ts.get_tournament(t.id).participants, key=lambda p: p.start_number or 0)
    for p in (first, second):
        sc.set_score(p.id, 0, 1, (200, None), round_number=0)
    return t, first.id, second.id


def _ranks(t):
    rows = next(iter(rs.compute_ranking(t.id).values()))
    return {r.participant_id: r.rank for r in rows}


def test_shoot_off_points_decide_a_tie_and_close_the_hint():
    t, first, second = _tied_tournament()
    assert _ranks(t) == {first: 1, second: 1} and len(rs.podium_ties(t.id)) == 1
    sc.set_shoot_off(first, 3)
    sc.set_shoot_off(second, 5)
    assert _ranks(t) == {second: 1, first: 2}
    assert rs.podium_ties(t.id) == []
    (group,) = rs.podium_ties(t.id, include_resolved=True)     # still listed to correct the values
    assert sorted((r.participant_id, r.shoot_off) for r in group.rows) == [(first, 0), (second, 0)]
    sc.set_shoot_off(first, 5)                                  # sudden death continues: still equal
    assert _ranks(t) == {first: 1, second: 1} and len(rs.podium_ties(t.id)) == 1
    sc.set_shoot_off(first, None)
    sc.set_shoot_off(second, None)
    assert _ranks(t) == {first: 1, second: 1}


def test_shoot_off_is_validated_and_locked_with_the_results():
    t, first, _ = _tied_tournament()
    with pytest.raises(ValidationError):
        sc.set_shoot_off(first, -1)
    ts.mark_results_generated(t.id)
    with pytest.raises(ValidationError):
        sc.set_shoot_off(first, 4)


def test_participant_table_has_the_shoot_off_column():
    from sqlalchemy import inspect
    from bowtally.database.engine import session_scope
    with session_scope() as s:
        columns = {c["name"] for c in inspect(s.get_bind()).get_columns("tournament_participants")}
    assert "shoot_off_points" in columns


@pytest.fixture
def app(monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_dialog_saves_the_shoot_off_points(app):
    from bowtally.ui.dialogs.shoot_off_dialog import ShootOffDialog
    t, first, second = _tied_tournament()
    dialog = ShootOffDialog(t.id)
    assert set(dialog.spins) == {first, second}
    dialog.spins[first].setValue(2)
    dialog.spins[second].setValue(4)
    assert dialog.save()
    assert _ranks(t) == {second: 1, first: 2}
    dialog = ShootOffDialog(t.id)                               # resolved ties stay editable
    assert (dialog.spins[first].value(), dialog.spins[second].value()) == (2, 4)
    dialog.spins[second].setValue(dialog.spins[second].minimum())     # "–" = no shoot-off value
    dialog.spins[first].setValue(dialog.spins[first].minimum())
    assert dialog.save() and _ranks(t) == {first: 1, second: 1}


def test_results_view_offers_the_button_only_for_rules_with_a_shoot_off(app):
    from bowtally.ui.views.results_view import ResultsView
    for shoot_off in (True, False):
        t, *_ = _tied_tournament(shoot_off, tag=str(shoot_off))
        view = ResultsView()
        view.set_tournament(ts.get_tournament(t.id))
        assert view.btn_shoot_off.isVisibleTo(view) is shoot_off


def _tables_of_the_pdf(t, tmp_path, monkeypatch):
    from bowtally.reports import result_list
    tables, original = [], result_list.Table
    monkeypatch.setattr(result_list, "Table", lambda data, *a, **k: tables.append(data)
                        or original(data, *a, **k))
    result_list.build_result_list(t.id, tmp_path / "r.pdf")
    return [data for data in tables if data and data[0] and data[0][0] == "Rang"]


def test_shoot_off_column_appears_in_view_exports_and_pdf_once_values_exist(app, tmp_path, monkeypatch):
    from bowtally.ui.dialogs.export_helper import tournament_sheets
    from bowtally.ui.views.results_view import ResultsView
    t, first, second = _tied_tournament()

    def view_headers():
        view = ResultsView()
        view.set_tournament(ts.get_tournament(t.id))
        return view.sheets[0][1], view.sheets[0][2]

    assert "Stechen" not in view_headers()[0]
    assert all("Stechen" not in tbl[0] for tbl in _tables_of_the_pdf(t, tmp_path, monkeypatch))
    sc.set_shoot_off(first, 0)                 # a real 0 is shown, not mistaken for "no value"
    sc.set_shoot_off(second, 4)
    headers, rows = view_headers()
    assert headers[-2:] == ["Stechen", "Gesamt"] and [r[-2] for r in rows] == [4, 0]
    sheet = {name: (h, r) for name, h, r in tournament_sheets(t.id)}["Rangliste"]
    assert sheet[0][-2:] == ["Stechen", "Gesamt"] and [r[-2] for r in sheet[1]] == [4, 0]
    tables = _tables_of_the_pdf(t, tmp_path, monkeypatch)
    assert tables and all(tbl[0][-2:] == ["Stechen", "Gesamt"] for tbl in tables)
    assert [row[-2] for row in tables[0][1:]] == ["4", "0"]

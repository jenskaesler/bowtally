# -*- coding: utf-8 -*-
from datetime import date

import pytest

pytest.importorskip("PySide6")

from bowtally.database import engine
from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts
from bowtally.ui.dialogs.export_helper import tournament_sheets


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'e.db').as_posix()}")


def _tournament(mode, num_rounds=1, targets=2):
    rule = sc.save_rule({"name": f"Kill {mode}", "max_shots_per_target": 1,
                         "ring_values": [{"zone": "Kill", "points": 10, "type": "kill"},
                                         {"zone": "Miss", "points": 0, "type": "miss"}],
                         "tracked_specials": [{"key": "kill", "label": "Kill", "track": True,
                                               "tiebreak": True}],
                         "rules_json": {"discipline": "3d", "tiebreak": "most_top_scores"}})
    t = ts.save_tournament({"name": "T", "date": date(2026, 5, 1), "num_targets": targets,
                            "shots_per_target": 1, "scoring_rule_id": rule.id,
                            "scoring_mode": mode, "num_rounds": num_rounds},
                           [md.list_bow_classes()[0].id])
    ts.add_participants(t.id, [md.save_archer({"first_name": "A", "last_name": "B"}).id])
    return t, ts.get_tournament(t.id).participants[0].id


def _sheets(t):
    return {name: (headers, rows) for name, headers, rows in tournament_sheets(t.id)}


def test_total_only_export_has_the_total_and_kills():
    t, pid = _tournament("total_only")
    sc.set_score(pid, 0, 1, (240, None), round_number=0)
    sc.set_special(pid, 0, "kill", 7)
    headers, rows = _sheets(t)["Ergebnisse"]
    assert headers == ["Nr.", "Name", "Gesamt", "Kill"] and rows[0][2:] == [240, 7]
    headers, rows = _sheets(t)["Rangliste"]
    assert headers[-2:] == ["Kill", "Gesamt"] and rows[0][-2:] == [7, 240]


def test_per_round_export_lists_every_round_with_its_kills():
    t, pid = _tournament("per_round", num_rounds=2)
    for rnd, (points, kills) in enumerate([(100, 2), (90, 1)], start=1):
        sc.set_score(pid, 0, 1, (points, None), round_number=rnd)
        sc.set_special(pid, rnd, "kill", kills)
    headers, rows = _sheets(t)["Ergebnisse"]
    assert headers[2:] == ["1. Runde", "1. Runde Kill", "2. Runde", "2. Runde Kill"]
    assert rows[0][2:] == [100, 2, 90, 1]


def test_per_target_export_lists_every_round():
    t, pid = _tournament("per_target", num_rounds=2)
    for rnd in (1, 2):
        sc.set_score(pid, 1, 1, (10, "Kill"), round_number=rnd)
    headers, rows = _sheets(t)["Ergebnisse"]
    assert headers[2:] == ["R1 1", "R1 2", "R2 1", "R2 2"]
    assert rows[0][2:] == [10, None, 10, None]


def test_pdf_table_per_target_lists_targets_kills_and_total(tmp_path, monkeypatch):
    from bowtally.reports import result_list
    t, pid = _tournament("per_target", targets=2)
    sc.set_score(pid, 1, 1, (10, "Kill"))
    sc.set_score(pid, 2, 1, (0, "Miss"))
    tables, original = [], result_list.Table
    monkeypatch.setattr(result_list, "Table", lambda data, *a, **k: tables.append(data)
                        or original(data, *a, **k))
    result_list.build_result_list(t.id, tmp_path / "r.pdf")
    (table,) = [d for d in tables if d and d[0] and d[0][0] == "Rang"]
    assert table[0] == ["Rang", "St.-Nr.", "Name", "Verein", "1", "2", "Kill", "Gesamt"]
    assert table[1][4:] == ["10", "0", "1", 10]

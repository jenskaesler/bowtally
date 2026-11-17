# -*- coding: utf-8 -*-
from datetime import date

import pytest

from bowtally.database import engine
from bowtally.services import ValidationError
from bowtally.services import master_data_service as md
from bowtally.services import ranking_service as rs
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts
from bowtally.services.ranking_service import RankRow, rank_rows


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'k.db').as_posix()}")


def _tournament(mode: str, num_rounds: int = 1, people: int = 2):
    rule = next(r for r in sc.list_rules() if r.name == "3D Hunter (IBO)")   # kill = tie-break
    t = ts.save_tournament({"name": "T", "date": date(2026, 5, 1), "num_targets": 1,
                            "shots_per_target": 1, "scoring_rule_id": rule.id,
                            "scoring_mode": mode, "num_rounds": num_rounds},
                           [md.list_bow_classes()[0].id])
    ts.add_participants(t.id, [md.save_archer({"first_name": f"P{i}", "last_name": "X"}).id
                               for i in range(people)])
    return t, [p.id for p in sorted(ts.get_tournament(t.id).participants,
                                    key=lambda p: p.start_number or 0)]


def _ranks(t):
    rows = next(iter(rs.compute_ranking(t.id).values()))
    return {r.participant_id: r.rank for r in rows}


def test_kills_need_points_first_and_survive_a_points_update():
    t, (a, _) = _tournament("total_only")
    with pytest.raises(ValidationError):
        sc.set_special(a, 0, "kill", 3)
    sc.set_score(a, 0, 1, (200, None), round_number=0)
    sc.set_special(a, 0, "kill", 3)
    sc.set_score(a, 0, 1, (210, None), round_number=0)
    row = sc.get_all_scores(t.id)[(a, 0, 0, 1)]
    assert (row.points, row.specials) == (210, {"kill": 3})
    sc.set_special(a, 0, "kill", None)
    assert sc.get_all_scores(t.id)[(a, 0, 0, 1)].specials == {}


def test_total_only_equal_points_more_kills_wins_and_full_tie_shares_first_place():
    t, (a, b) = _tournament("total_only")
    for pid, kills in ((a, 3), (b, 5)):
        sc.set_score(pid, 0, 1, (200, None), round_number=0)
        sc.set_special(pid, 0, "kill", kills)
    assert _ranks(t) == {b: 1, a: 2}
    sc.set_special(a, 0, "kill", 5)
    assert _ranks(t) == {a: 1, b: 1}


def test_per_round_adds_kills_of_all_rounds():
    t, (a, b) = _tournament("per_round", num_rounds=2)
    for pid, kills in ((a, (2, 2)), (b, (1, 2))):
        for rnd, k in enumerate(kills, start=1):
            sc.set_score(pid, 0, 1, (100, None), round_number=rnd)
            sc.set_special(pid, rnd, "kill", k)
    assert _ranks(t) == {a: 1, b: 2}


def test_kills_decide_before_the_number_of_top_hits():
    def row(pid, shots, kills):
        return RankRow(pid, pid, f"A{pid}", "", 1, "RH", [], shot_points=shots, total=sum(shots),
                       specials={"kill": kills})
    more_top_hits, more_kills = row(1, [20, 0, 10], 1), row(2, [10, 10, 10], 4)
    ranked = rank_rows([more_top_hits, more_kills], "most_top_scores", [20, 10, 0], ["kill"])
    assert [r.participant_id for r in ranked] == [2, 1]

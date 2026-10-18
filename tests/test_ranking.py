# -*- coding: utf-8 -*-
import pytest

from bowtally.services import ValidationError
from bowtally.services.ranking_service import RankRow, rank_rows
from bowtally.services.scoring_service import parse_entry

IBO = [{"zone": "Vital innen", "points": 20}, {"zone": "Vital außen", "points": 10},
       {"zone": "Körper", "points": 5}, {"zone": "Miss", "points": 0}]


def _row(pid, shots):
    return RankRow(pid, pid, f"A{pid}", "", 1, "RH", [], shots, sum(shots))


def test_most_top_scores_breaks_tie():
    a = _row(1, [20, 0, 10])   # 30, one 20
    b = _row(2, [10, 10, 10])  # 30, no 20
    c = _row(3, [20, 20, 0])   # 40
    ranked = rank_rows([a, b, c], "most_top_scores", [20, 10, 5, 0])
    assert [(r.participant_id, r.rank) for r in ranked] == [(3, 1), (1, 2), (2, 3)]


def test_total_highest_shares_rank():
    a, b, c = _row(1, [20, 0, 10]), _row(2, [10, 10, 10]), _row(3, [5])
    ranked = rank_rows([a, b, c], "total_highest", [20, 10, 5, 0])
    assert [r.rank for r in ranked] == [1, 1, 3]


def test_parse_entry():
    assert parse_entry("", IBO) is None
    assert parse_entry("20", IBO) == (20, "Vital innen")
    assert parse_entry("körper", IBO) == (5, "Körper")
    assert parse_entry("Vital außen (10)", IBO) == (10, "Vital außen")
    with pytest.raises(ValidationError):
        parse_entry("7", IBO)
    with pytest.raises(ValidationError):
        parse_entry("Kopf", IBO)

# -*- coding: utf-8 -*-
"""Ranking computation with configurable tie-break."""
from dataclasses import dataclass, field

from bowtally.services import settings_service
from bowtally.services.scoring_service import get_all_scores, get_scores
from bowtally.services.tournament_service import get_tournament

TIEBREAK_MOST_TOP = "most_top_scores"
TIEBREAK_TOTAL = "total_highest"


@dataclass
class RankRow:
    participant_id: int
    start_number: int | None
    name: str
    club: str
    bow_class_id: int | None
    bow_class: str
    target_totals: list[int | None]   # None = nothing entered for this target (per_target)
    round_totals: list[int | None] = field(default_factory=list)  # per_round mode
    shot_points: list[int] = field(default_factory=list)
    total: int = 0
    rank: int = 0


def tiebreak_key(row: RankRow, mode: str, point_levels: list[int]) -> tuple:
    """Higher key = better. most_top_scores compares hit counts from the top zone down."""
    if mode == TIEBREAK_MOST_TOP:
        return (row.total,) + tuple(row.shot_points.count(v) for v in point_levels)
    return (row.total,)


def rank_rows(rows: list[RankRow], mode: str, point_levels: list[int]) -> list[RankRow]:
    """Sort descending and assign competition ranks (1, 1, 3). Mutates and returns rows."""
    point_levels = sorted({p for p in point_levels if p > 0}, reverse=True)
    rows.sort(key=lambda r: (tiebreak_key(r, mode, point_levels),
                             -(r.start_number or 0)), reverse=True)
    prev = None
    for i, r in enumerate(rows, start=1):
        key = tiebreak_key(r, mode, point_levels)
        r.rank = prev[1] if prev and prev[0] == key else i
        prev = (key, r.rank)
    return rows


OVERALL = "all"


def compute_ranking(tournament_id: int, mode: str | None = None,
                    overall: bool = False) -> dict[int | str | None, list]:
    """Returns {bow_class_id: [RankRow, ...]} ranked within each class, ordered by class.

    overall=True ranks everybody together: {OVERALL: [RankRow, ...]}.
    Handles per_target (single/multi-round), per_round and total_only scoring modes.
    """
    t = get_tournament(tournament_id)
    mode = mode or settings_service.get(settings_service.KEY_RESULT_TIEBREAK_MODE,
                                        TIEBREAK_MOST_TOP)
    scoring_mode = getattr(t, "scoring_mode", "per_target") or "per_target"
    num_rounds = getattr(t, "num_rounds", 1) or 1
    levels = [z["points"] for z in (t.scoring_rule.ring_values if t.scoring_rule else [])]

    by_class: dict[int | None, list[RankRow]] = {bc.id: [] for bc in t.bow_classes}

    if scoring_mode == "total_only":
        scores = get_all_scores(tournament_id)
        for p in t.participants:
            sc = scores.get((p.id, 0, 0, 1))
            total = sc.points if sc else 0
            row = RankRow(participant_id=p.id, start_number=p.start_number,
                          name=f"{p.archer.last_name}, {p.archer.first_name}",
                          club=p.archer.club or "", bow_class_id=p.bow_class_id,
                          bow_class=p.bow_class.name if p.bow_class else "-",
                          target_totals=[], total=total)
            by_class.setdefault(OVERALL if overall else p.bow_class_id, []).append(row)

    elif scoring_mode == "per_round":
        scores = get_all_scores(tournament_id)
        round_numbers = list(range(1, num_rounds + 1))
        for p in t.participants:
            rtotals = []
            grand = 0
            for rn in round_numbers:
                sc = scores.get((p.id, rn, 0, 1))
                pts = sc.points if sc else None
                rtotals.append(pts)
                grand += pts or 0
            row = RankRow(participant_id=p.id, start_number=p.start_number,
                          name=f"{p.archer.last_name}, {p.archer.first_name}",
                          club=p.archer.club or "", bow_class_id=p.bow_class_id,
                          bow_class=p.bow_class.name if p.bow_class else "-",
                          target_totals=[], round_totals=rtotals, total=grand)
            by_class.setdefault(OVERALL if overall else p.bow_class_id, []).append(row)

    else:  # per_target (single or multi-round)
        all_scores = get_all_scores(tournament_id)
        for p in t.participants:
            totals, shots = [], []
            for rn in range(1, num_rounds + 1):
                for target in range(1, t.num_targets + 1):
                    pts = [all_scores[(p.id, rn, target, s)].points
                           for s in range(1, t.shots_per_target + 1)
                           if (p.id, rn, target, s) in all_scores]
                    shots += pts
                    totals.append(sum(pts) if pts else None)
            row = RankRow(participant_id=p.id, start_number=p.start_number,
                          name=f"{p.archer.last_name}, {p.archer.first_name}",
                          club=p.archer.club or "", bow_class_id=p.bow_class_id,
                          bow_class=p.bow_class.name if p.bow_class else "-",
                          target_totals=totals, shot_points=shots, total=sum(shots))
            by_class.setdefault(OVERALL if overall else p.bow_class_id, []).append(row)

    if overall:
        return {OVERALL: rank_rows(by_class.get(OVERALL, []), mode, levels)}
    return {cid: rank_rows(rows, mode, levels) for cid, rows in by_class.items()}

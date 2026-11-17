# -*- coding: utf-8 -*-
"""Ranking computation with configurable tie-break."""
from dataclasses import dataclass, field

from bowtally.services import settings_service
from bowtally.services.scoring_service import active_specials, get_all_scores, get_scores
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
    specials: dict = field(default_factory=dict)  # {zone_type_key: count}
    shoot_off: int = 0                            # shoot-off result, decides remaining ties only
    shoot_off_entered: int | None = None          # the entered value (None = no shoot-off), for display


def tiebreak_key(row: RankRow, mode: str, point_levels: list[int],
                 tiebreak_specials: list[str] = (), top_hits_first: bool = False) -> tuple:
    """Higher key = better: total, then the rule's tie-break specials (e.g. kills) and - for
    most_top_scores - hit counts from the top zone down (before the specials if top_hits_first)."""
    specials = tuple(row.specials.get(k, 0) for k in tiebreak_specials)
    top_hits = tuple(row.shot_points.count(v) for v in point_levels) \
        if mode == TIEBREAK_MOST_TOP else ()
    order = top_hits + specials if top_hits_first else specials + top_hits
    return (row.total,) + order + (row.shoot_off,)


def rank_rows(rows: list[RankRow], mode: str, point_levels: list[int],
              tiebreak_specials: list[str] = (), top_hits_first: bool = False) -> list[RankRow]:
    """Sort descending and assign competition ranks (1, 1, 3). Mutates and returns rows."""
    point_levels = sorted({p for p in point_levels if p > 0}, reverse=True)
    rows.sort(key=lambda r: (tiebreak_key(r, mode, point_levels, tiebreak_specials, top_hits_first),
                             -(r.start_number or 0)), reverse=True)
    prev = None
    for i, r in enumerate(rows, start=1):
        key = tiebreak_key(r, mode, point_levels, tiebreak_specials, top_hits_first)
        r.rank = prev[1] if prev and prev[0] == key else i
        prev = (key, r.rank)
    return rows


OVERALL = "all"


def compute_ranking(tournament_id: int, mode: str | None = None, overall: bool = False,
                    use_shoot_off: bool = True) -> dict[int | str | None, list]:
    """Returns {bow_class_id: [RankRow, ...]} ranked within each class, ordered by class.

    overall=True ranks everybody together: {OVERALL: [RankRow, ...]}.
    Handles per_target (single/multi-round), per_round and total_only scoring modes.
    """
    t = get_tournament(tournament_id)
    rule_mode = (t.scoring_rule.rules_json or {}).get("tiebreak") if t.scoring_rule else None
    mode = mode or rule_mode or TIEBREAK_MOST_TOP
    top_first = bool((t.scoring_rule.rules_json or {}).get("top_hits_first")) if t.scoring_rule else False
    scoring_mode = getattr(t, "scoring_mode", "per_target") or "per_target"
    num_rounds = getattr(t, "num_rounds", 1) or 1
    levels = [z["points"] for z in (t.scoring_rule.ring_values if t.scoring_rule else [])]
    _tracked = active_specials(t.scoring_rule)
    tiebreak_specials = [sp["key"] for sp in _tracked if sp.get("tiebreak")]

    by_class: dict[int | None, list[RankRow]] = {bc.id: [] for bc in t.bow_classes}
    shoot_off = lambda p: (p.shoot_off_points or 0) if use_shoot_off else 0  # noqa: E731

    if scoring_mode == "total_only":
        scores = get_all_scores(tournament_id)
        for p in t.participants:
            sc = scores.get((p.id, 0, 0, 1))
            total = sc.points if sc else 0
            row = RankRow(participant_id=p.id, start_number=p.start_number,
                          name=f"{p.archer.last_name}, {p.archer.first_name}",
                          club=p.archer.club or "", bow_class_id=p.bow_class_id,
                          bow_class=p.bow_class.name if p.bow_class else "-",
                          target_totals=[], total=total,
                          specials=dict(sc.specials or {}) if sc else {}, shoot_off=shoot_off(p),
                          shoot_off_entered=p.shoot_off_points)
            by_class.setdefault(OVERALL if overall else p.bow_class_id, []).append(row)

    elif scoring_mode == "per_round":
        scores = get_all_scores(tournament_id)
        round_numbers = list(range(1, num_rounds + 1))
        for p in t.participants:
            rtotals = []
            grand = 0
            spec_total: dict[str, int] = {}
            for rn in round_numbers:
                sc = scores.get((p.id, rn, 0, 1))
                pts = sc.points if sc else None
                rtotals.append(pts)
                grand += pts or 0
                for k, v in (sc.specials or {}).items() if sc else ():
                    spec_total[k] = spec_total.get(k, 0) + v
            row = RankRow(participant_id=p.id, start_number=p.start_number,
                          name=f"{p.archer.last_name}, {p.archer.first_name}",
                          club=p.archer.club or "", bow_class_id=p.bow_class_id,
                          bow_class=p.bow_class.name if p.bow_class else "-",
                          target_totals=[], round_totals=rtotals, total=grand,
                          specials=spec_total, shoot_off=shoot_off(p),
                          shoot_off_entered=p.shoot_off_points)
            by_class.setdefault(OVERALL if overall else p.bow_class_id, []).append(row)

    else:  # per_target (single or multi-round)
        all_scores = get_all_scores(tournament_id)
        for p in t.participants:
            totals, shots = [], []
            spec_total: dict[str, int] = {}
            for rn in range(1, num_rounds + 1):
                for target in range(1, t.num_targets + 1):
                    pts = [all_scores[(p.id, rn, target, s)].points
                           for s in range(1, t.shots_per_target + 1)
                           if (p.id, rn, target, s) in all_scores]
                    shots += pts
                    totals.append(sum(pts) if pts else None)
                    for s in range(1, t.shots_per_target + 1):
                        sc_obj = all_scores.get((p.id, rn, target, s))
                        if sc_obj and sc_obj.specials:
                            for k, v in sc_obj.specials.items():
                                spec_total[k] = spec_total.get(k, 0) + v
            row = RankRow(participant_id=p.id, start_number=p.start_number,
                          name=f"{p.archer.last_name}, {p.archer.first_name}",
                          club=p.archer.club or "", bow_class_id=p.bow_class_id,
                          bow_class=p.bow_class.name if p.bow_class else "-",
                          target_totals=totals, shot_points=shots, total=sum(shots),
                          specials=spec_total, shoot_off=shoot_off(p),
                          shoot_off_entered=p.shoot_off_points)
            by_class.setdefault(OVERALL if overall else p.bow_class_id, []).append(row)

    if overall:
        return {OVERALL: rank_rows(by_class.get(OVERALL, []), mode, levels, tiebreak_specials,
                                   top_first)}
    return {cid: rank_rows(rows, mode, levels, tiebreak_specials, top_first)
            for cid, rows in by_class.items()}


def has_shoot_off_values(ranking: dict) -> bool:
    """True if any participant has a shoot-off result (then lists get a 'Stechen' column)."""
    return any(r.shoot_off_entered is not None for rows in ranking.values() for r in rows)


PODIUM_PLACES = 3


@dataclass
class TieGroup:
    class_id: int | None
    class_name: str
    rank: int
    rows: list[RankRow]

    @property
    def names(self) -> list[str]:
        return [r.name for r in self.rows]


def podium_ties(tournament_id: int, include_resolved: bool = False) -> list[TieGroup]:
    """Ties on places 1-3 if the rule demands a shoot-off. By default only the still open ones;
    include_resolved also lists ties already decided by shoot-off points (to correct them)."""
    t = get_tournament(tournament_id)
    if not t.scoring_rule or not (t.scoring_rule.rules_json or {}).get("shoot_off"):
        return []
    class_names = {bc.id: bc.name for bc in t.bow_classes}
    groups = []
    for cid, rows in compute_ranking(tournament_id, use_shoot_off=not include_resolved).items():
        for rank in sorted({r.rank for r in rows if r.rank <= PODIUM_PLACES and r.total > 0}):
            tied = [r for r in rows if r.rank == rank]
            if len(tied) > 1:
                groups.append(TieGroup(cid, class_names.get(cid, "Ohne Klasse"), rank, tied))
    return groups


def describe_ties(groups: list[TieGroup]) -> str:
    """'Stechen laut Regelwerk: Recurve Platz 1 (A, B); ...' (empty without ties)."""
    if not groups:
        return ""
    return "Stechen laut Regelwerk: " + "; ".join(
        f"{g.class_name} Platz {g.rank} ({', '.join(g.names)})" for g in groups)

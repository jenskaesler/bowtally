# -*- coding: utf-8 -*-
"""Scoring rules CRUD and score entry."""
from sqlalchemy import func, select

from bowtally.database.engine import session_scope
from bowtally.database.models import Score, ScoringRule, Tournament, TournamentParticipant
from bowtally.services import ValidationError

RULE_FIELDS = ["name", "description", "ring_values", "max_shots_per_target",
               "allow_retry_shot", "rules_json", "tracked_specials"]


# ---------------------------------------------------------------- rules

def list_rules() -> list[ScoringRule]:
    with session_scope() as s:
        return list(s.scalars(select(ScoringRule).order_by(ScoringRule.is_builtin.desc(),
                                                           ScoringRule.name)))


def get_rule(rule_id: int) -> ScoringRule | None:
    with session_scope() as s:
        return s.get(ScoringRule, rule_id)


def _validate_rule(data: dict) -> dict:
    data = {k: v for k, v in data.items() if k in RULE_FIELDS}
    data["name"] = (data.get("name") or "").strip()
    if not data["name"]:
        raise ValidationError("Name ist ein Pflichtfeld.")
    zones = data.get("ring_values") or []
    if not zones:
        raise ValidationError("Mindestens eine Zone ist erforderlich.")
    seen = set()
    for z in zones:
        name = (z.get("zone") or "").strip()
        if not name:
            raise ValidationError("Jede Zone braucht einen Namen.")
        if name in seen:
            raise ValidationError(f"Zone '{name}' ist doppelt vorhanden.")
        if not isinstance(z.get("points"), int) or z["points"] < 0:
            raise ValidationError(f"Ungültiger Punktwert für Zone '{name}'.")
        seen.add(name)
    data["ring_values"] = [{"zone": z["zone"].strip(), "points": z["points"],
                            **({} if not z.get("type")
                               else {"type": z["type"].strip()})}
                           for z in zones]
    # auto-derive tracked_specials from zone types if not provided
    if not data.get("tracked_specials"):
        _tb = {"kill", "x", "12"}
        seen: dict[str, str] = {}
        for z in data["ring_values"]:
            zt = (z.get("type") or "").strip()
            if zt and zt not in seen:
                seen[zt] = z["zone"]
        data["tracked_specials"] = [{"key": k, "label": lbl, "track": True,
                                     "tiebreak": k in _tb}
                                    for k, lbl in seen.items()]
    if int(data.get("max_shots_per_target") or 1) < 1:
        raise ValidationError("Mindestens ein Schuss je Scheibe.")
    return data


def save_rule(data: dict, rule_id: int | None = None) -> ScoringRule:
    data = _validate_rule(data)
    with session_scope() as s:
        dup = s.scalar(select(ScoringRule).where(ScoringRule.name == data["name"]))
        if dup is not None and dup.id != rule_id:
            raise ValidationError(f"Ein Regelwerk namens '{data['name']}' existiert bereits.")
        if rule_id is None:
            rule = ScoringRule(is_builtin=False, **data)
            s.add(rule)
        else:
            rule = s.get(ScoringRule, rule_id)
            if rule is None:
                raise ValidationError("Regelwerk nicht gefunden.")
            if rule.is_builtin:
                raise ValidationError("Standard-Regelwerke sind schreibgeschützt. "
                                      "Bitte kopieren.")
            for k, v in data.items():
                setattr(rule, k, v)
        s.flush()
        return rule


def clone_rule(rule_id: int) -> ScoringRule:
    with session_scope() as s:
        src = s.get(ScoringRule, rule_id)
        names = set(s.scalars(select(ScoringRule.name)))
    name = f"{src.name} (Kopie)"
    i = 2
    while name in names:
        name = f"{src.name} (Kopie {i})"
        i += 1
    return save_rule({"name": name, "description": src.description,
                      "ring_values": [dict(z) for z in src.ring_values],
                      "max_shots_per_target": src.max_shots_per_target,
                      "allow_retry_shot": src.allow_retry_shot,
                      "rules_json": dict(src.rules_json or {})})


def import_rules(records: list[dict], strategy: str) -> dict:
    """strategy: 'skip' | 'update' | 'new'. Returns counters."""
    import json as _json
    result = {"created": 0, "updated": 0, "skipped": 0}
    with session_scope() as s:
        for rec in records:
            rec = dict(rec)
            for key in ("ring_values", "rules_json"):
                v = rec.get(key)
                if isinstance(v, str) and v.strip():
                    try:
                        rec[key] = _json.loads(v)
                    except Exception:
                        rec[key] = None
            name = (rec.get("name") or "").strip()
            if not name or not rec.get("ring_values"):
                continue
            existing = None if strategy == "new" else s.scalars(
                select(ScoringRule).where(ScoringRule.name == name,
                                          ScoringRule.is_builtin.is_(False))).first()
            try:
                data = _validate_rule(rec)
            except ValidationError:
                continue
            if existing is None:
                s.add(ScoringRule(is_builtin=False, **data))
                result["created"] += 1
            elif strategy == "update":
                for k, v in data.items():
                    setattr(existing, k, v)
                result["updated"] += 1
            else:
                result["skipped"] += 1
    return result


def delete_rule(rule_id: int) -> None:
    with session_scope() as s:
        rule = s.get(ScoringRule, rule_id)
        if rule is None:
            return
        if rule.is_builtin:
            raise ValidationError("Standard-Regelwerke können nicht gelöscht werden.")
        if s.scalar(select(func.count(Tournament.id))
                    .where(Tournament.scoring_rule_id == rule_id)):
            raise ValidationError("Das Regelwerk wird von einem Turnier verwendet.")
        s.delete(rule)


# ---------------------------------------------------------------- score entry

def parse_entry(text: str, ring_values: list[dict]) -> tuple[int, str | None] | None:
    """Parse a cell entry: zone name, 'Zone (20)' combo text or plain number.

    Returns (points, zone) or None for an empty entry. Raises ValidationError.
    """
    text = (text or "").strip()
    if not text:
        return None
    by_zone = {z["zone"].lower(): z for z in ring_values}
    label = text.rsplit(" (", 1)[0].lower() if text.endswith(")") else text.lower()
    if label in by_zone:
        z = by_zone[label]
        return z["points"], z["zone"]
    try:
        points = int(text)
    except ValueError:
        raise ValidationError(f"'{text}' ist weder Zahl noch Zone des Regelwerks.") from None
    allowed = sorted({z["points"] for z in ring_values})
    if points not in allowed:
        raise ValidationError(f"{points} Punkte sind im Regelwerk nicht vorgesehen "
                              f"(erlaubt: {', '.join(map(str, allowed))}).")
    zones = [z["zone"] for z in ring_values if z["points"] == points]
    return points, zones[0] if len(zones) == 1 else None


def get_scores(tournament_id: int, round_number: int = 1) -> dict[tuple[int, int, int], Score]:
    """(participant_id, target, shot) -> Score for the given round."""
    with session_scope() as s:
        q = (select(Score).join(TournamentParticipant)
             .where(TournamentParticipant.tournament_id == tournament_id,
                    Score.round_number == round_number))
        return {(sc.participant_id, sc.target_number, sc.shot_number): sc for sc in s.scalars(q)}


def get_all_scores(tournament_id: int) -> dict[tuple[int, int, int, int], Score]:
    """(participant_id, round_number, target, shot) -> Score for all rounds."""
    with session_scope() as s:
        q = (select(Score).join(TournamentParticipant)
             .where(TournamentParticipant.tournament_id == tournament_id))
        return {(sc.participant_id, sc.round_number, sc.target_number, sc.shot_number): sc
                for sc in s.scalars(q)}


def recent_scores(limit: int = 12) -> list[dict]:
    """Most recently entered / changed scores across all tournaments (dashboard)."""
    from sqlalchemy.orm import selectinload
    from bowtally.database.models import Archer
    with session_scope() as s:
        q = (select(Score).options(selectinload(Score.participant)
                                   .selectinload(TournamentParticipant.archer),
                                   selectinload(Score.participant)
                                   .selectinload(TournamentParticipant.tournament))
             .order_by(Score.entered_at.desc(), Score.id.desc()).limit(limit))
        out = []
        for sc in s.scalars(q):
            p = sc.participant
            a: Archer = p.archer
            out.append({"entered_at": sc.entered_at, "tournament_id": p.tournament_id,
                        "tournament": p.tournament.name, "archer": f"{a.first_name} {a.last_name}",
                        "target": sc.target_number, "shot": sc.shot_number,
                        "points": sc.points, "zone": sc.zone_hit})
        return out


def set_score(participant_id: int, target: int, shot: int,
              entry: tuple[int, str | None] | None,
              round_number: int = 1) -> None:
    """Upsert or (entry=None) delete one score."""
    with session_scope() as s:
        part = s.get(TournamentParticipant, participant_id)
        if part is None:
            raise ValidationError("Teilnehmer nicht gefunden.")
        t = part.tournament
        if t.status == "closed" or t.results_generated_at is not None:
            raise ValidationError("Die Auswertung ist geschlossen, Eingaben sind gesperrt.")
        # target=0 is the per_round/total_only convention; skip range check for it
        if target != 0 and (not 1 <= target <= t.num_targets or
                            not 1 <= shot <= t.shots_per_target):
            raise ValidationError("Scheibe oder Schuss außerhalb des Turnierbereichs.")
        sc = s.scalar(select(Score).where(Score.participant_id == participant_id,
                                          Score.round_number == round_number,
                                          Score.target_number == target,
                                          Score.shot_number == shot))
        if entry is None:
            if sc is not None:
                s.delete(sc)
            return
        points, zone = entry
        if sc is None:
            sc = Score(participant_id=participant_id, round_number=round_number,
                       target_number=target, shot_number=shot)
            s.add(sc)
        sc.points = points
        sc.zone_hit = zone
        rule = s.get(ScoringRule, t.scoring_rule_id) if t.scoring_rule_id else None
        sc.specials = {}
        if rule and zone and rule.tracked_specials:
            zone_map = {z["zone"]: (z.get("type") or "") for z in rule.ring_values}
            zt = zone_map.get(zone, "")
            if zt and any(sp["key"] == zt and sp.get("track") for sp in rule.tracked_specials):
                sc.specials = {zt: 1}

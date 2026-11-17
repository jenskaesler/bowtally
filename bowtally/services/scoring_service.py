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


COUNTER_KEYS = ("kill", "x")        # counters a rule can switch on; entered by hand in per_round / total_only


def derive_tracked_specials(ring_values: list[dict]) -> list[dict]:
    """One counter per zone type used in the rule (labelled with its first zone)."""
    first_zone: dict[str, str] = {}
    for z in ring_values:
        zone_type = (z.get("type") or "").strip()
        if zone_type and zone_type not in first_zone:
            first_zone[zone_type] = z["zone"]
    return [{"key": k, "label": lbl, "track": True, "tiebreak": k in {"kill", "x", "12"}}
            for k, lbl in first_zone.items()]


DISCIPLINES = (("3d", "3D-Parcours"), ("target", "Scheibe"))
COUNTER_DISCIPLINE = {"kill": "3d", "x": "target"}      # Kill only counts in 3D, X only on targets


def rule_discipline(rule) -> str:
    """'3d' or 'target': stored in the rule, else guessed from its name."""
    stored = (rule.rules_json or {}).get("discipline")
    return stored or ("3d" if "3d" in rule.name.lower() else "target")


def active_specials(rule) -> list[dict]:
    """The rule's tracked specials that apply to its discipline (no Kill on targets, no X in 3D)."""
    if not rule:
        return []
    discipline = rule_discipline(rule)
    return [sp for sp in (rule.tracked_specials or [])
            if COUNTER_DISCIPLINE.get(sp.get("key"), discipline) == discipline]


def counter_specials(rule) -> list[dict]:
    """The rule's active Kill / X counters, Kill first."""
    specials = active_specials(rule)
    return [sp for key in COUNTER_KEYS for sp in specials if sp.get("key") == key and sp.get("track")]


ZONE_TYPES = [("", "(kein)"), ("kill", "Kill"), ("x", "X-Ring"), ("12", "12-Ring"),
              ("body", "Body/Vital"), ("hit", "Treffer"), ("miss", "Miss")]
_COUNTER_LABEL = {"kill": "Kill", "x": "X"}


def rule_options_to_data(discipline: str, flags: dict, ring_values: list[dict],
                         previous_specials: list[dict] | None = None,
                         previous_rules_json: dict | None = None) -> dict:
    """tracked_specials + rules_json from the switches (count_/tie_ for kill and x, top_hits).

    Kill is only possible in 3D, X only on targets. Specials other than Kill / X are kept.
    """
    previous = previous_specials if previous_specials is not None \
        else derive_tracked_specials(ring_values)
    labels = {sp["key"]: sp["label"] for sp in previous}
    counters = [{"key": k, "label": labels.get(k) or _COUNTER_LABEL[k], "track": True,
                 "tiebreak": bool(flags.get(f"tie_{k}"))}
                for k in COUNTER_KEYS if flags.get(f"count_{k}") and COUNTER_DISCIPLINE[k] == discipline]
    return {"tracked_specials": counters + [sp for sp in previous if sp["key"] not in COUNTER_KEYS],
            "rules_json": {**(previous_rules_json or {}), "discipline": discipline,
                           "tiebreak": "most_top_scores" if flags.get("top_hits") else "total_highest",
                           "top_hits_first": bool(flags.get("top_hits") and flags.get("top_first")),
                           "shoot_off": bool(flags.get("shoot_off"))}}


def format_zones(zones: list[dict]) -> str:
    """'Kill-Zone = 11 [Kill]; Körper = 8; Miss = 0 [Miss]'"""
    labels = dict(ZONE_TYPES)
    return "; ".join(f"{z['zone']} = {z['points']}"
                     + (f" [{labels.get(z['type'], z['type'])}]" if z.get("type") else "")
                     for z in zones)


def parse_zones(text: str) -> list[dict]:
    """Inverse of format_zones; the type may be given by key or label."""
    types = {name.lower(): key for key, label in ZONE_TYPES if key for name in (key, label)}
    zones = []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        zone_type = ""
        if part.endswith("]") and "[" in part:
            part, _, label = part[:-1].rpartition("[")
            zone_type = types.get(label.strip().lower())
            if zone_type is None:
                raise ValidationError(f"Unbekannter Zonentyp '{label.strip()}'.")
        name, sep, points = part.rpartition("=")
        if not sep or not name.strip():
            raise ValidationError(f"Zone '{part.strip()}' braucht die Form 'Name = Punkte'.")
        try:
            zone = {"zone": name.strip(), "points": int(points.strip())}
        except ValueError:
            raise ValidationError(f"Ungültiger Punktwert in '{part.strip()}'.") from None
        zones.append({**zone, **({"type": zone_type} if zone_type else {})})
    return zones


RULE_EXPORT_HEADERS = ["Bezeichnung", "Beschreibung", "Disziplin", "Schüsse je Ziel", "Nachschuss",
                       "Zonen", "Kills zählen", "Bei Gleichstand zählen Kills", "X-Treffer zählen",
                       "Bei Gleichstand zählen X-Treffer", "Treffer in der höchsten Wertung",
                       "Treffer in der höchsten Wertung zuerst", "Stechen erforderlich"]


def rule_export_row(rule) -> list:
    counters = {sp["key"]: sp for sp in counter_specials(rule)}
    yes_no = lambda value: "Ja" if value else "Nein"  # noqa: E731
    top_hits = (rule.rules_json or {}).get("tiebreak", "most_top_scores") == "most_top_scores"
    return [rule.name, rule.description or "", dict(DISCIPLINES)[rule_discipline(rule)],
            rule.max_shots_per_target, yes_no(rule.allow_retry_shot), format_zones(rule.ring_values),
            yes_no("kill" in counters), yes_no(counters.get("kill", {}).get("tiebreak")),
            yes_no("x" in counters), yes_no(counters.get("x", {}).get("tiebreak")), yes_no(top_hits),
            yes_no((rule.rules_json or {}).get("top_hits_first")),
            yes_no((rule.rules_json or {}).get("shoot_off"))]


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
    if data.get("tracked_specials") is None:    # [] means: nothing is counted
        data["tracked_specials"] = derive_tracked_specials(data["ring_values"])
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


def _parse_discipline(text, name: str) -> str:
    text = (text or "").strip().lower()
    if text:
        return "3d" if "3d" in text else "target"
    return "3d" if "3d" in name.lower() else "target"


def _rule_data_from_record(rec: dict) -> dict | None:
    """Readable import row -> data for _validate_rule (None = row is unusable)."""
    import json as _json
    name = (rec.get("name") or "").strip()
    zones = rec.get("ring_values")
    try:
        if isinstance(zones, str):      # readable text; JSON from older exports still works
            zones = _json.loads(zones) if zones.strip().startswith("[") else parse_zones(zones)
    except (ValueError, ValidationError):
        return None
    if not name or not zones:
        return None
    discipline = _parse_discipline(rec.get("discipline"), name)
    flags = {k: bool(rec.get(k)) for k in ("count_kill", "tie_kill", "count_x", "tie_x",
                                            "top_first", "shoot_off")}
    flags["top_hits"] = rec.get("top_hits") is not False        # empty cell = default (on)
    return {"name": name, "description": rec.get("description"), "ring_values": zones,
            "max_shots_per_target": rec.get("max_shots_per_target") or 1,
            "allow_retry_shot": bool(rec.get("allow_retry_shot")),
            **rule_options_to_data(discipline, flags, zones)}


def import_rules(records: list[dict], strategy: str) -> dict:
    """strategy: 'skip' | 'update' | 'new'. Returns counters."""
    result = {"created": 0, "updated": 0, "skipped": 0}
    with session_scope() as s:
        for rec in records:
            raw = _rule_data_from_record(dict(rec))
            if raw is None:
                continue
            existing = None if strategy == "new" else s.scalars(
                select(ScoringRule).where(ScoringRule.name == raw["name"],
                                          ScoringRule.is_builtin.is_(False))).first()
            try:
                data = _validate_rule(raw)
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


def _open_participant(s, participant_id: int) -> TournamentParticipant:
    part = s.get(TournamentParticipant, participant_id)
    if part is None:
        raise ValidationError("Teilnehmer nicht gefunden.")
    t = part.tournament
    if t.status == "closed" or t.results_generated_at is not None:
        raise ValidationError("Die Auswertung ist geschlossen, Eingaben sind gesperrt.")
    return part


def set_special(participant_id: int, round_number: int, key: str, count: int | None) -> None:
    """Kill-style counter of a per_round / total_only result (round 0 = total_only).

    It lives on the points row, so the points must be entered first. None or 0 removes it.
    """
    if count is not None and count < 0:
        raise ValidationError("Negative Anzahlen sind nicht erlaubt.")
    with session_scope() as s:
        _open_participant(s, participant_id)
        sc = s.scalar(select(Score).where(Score.participant_id == participant_id,
                                          Score.round_number == round_number,
                                          Score.target_number == 0, Score.shot_number == 1))
        if sc is None:
            if count:
                raise ValidationError("Bitte zuerst die Punkte eintragen.")
            return
        specials = {k: v for k, v in (sc.specials or {}).items() if k != key}
        if count:
            specials[key] = count
        sc.specials = specials


def set_score(participant_id: int, target: int, shot: int,
              entry: tuple[int, str | None] | None,
              round_number: int = 1) -> None:
    """Upsert or (entry=None) delete one score."""
    with session_scope() as s:
        t = _open_participant(s, participant_id).tournament
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
        if points < 0:
            raise ValidationError("Negative Punktzahlen sind nicht erlaubt.")
        if sc is None:
            sc = Score(participant_id=participant_id, round_number=round_number,
                       target_number=target, shot_number=shot)
            s.add(sc)
        sc.points = points
        sc.zone_hit = zone
        if target == 0:
            return      # per_round / total_only rows keep their kill counters
        rule = s.get(ScoringRule, t.scoring_rule_id) if t.scoring_rule_id else None
        sc.specials = {}
        if rule and zone and rule.tracked_specials:
            zone_map = {z["zone"]: (z.get("type") or "") for z in rule.ring_values}
            zt = zone_map.get(zone, "")
            if zt and any(sp["key"] == zt and sp.get("track") for sp in active_specials(rule)):
                sc.specials = {zt: 1}

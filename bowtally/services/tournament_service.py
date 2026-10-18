# -*- coding: utf-8 -*-
"""Tournaments, status workflow and participants."""
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bowtally.database.engine import session_scope
from bowtally.database.models import (Archer, BowClass, Score, ScoringRule, Tournament,
                                      TournamentParticipant)
from bowtally.services import ValidationError
from bowtally.services.master_data_service import _bow_class_lookup, _clean_archer, find_archer

STATUS_LABELS = {"draft": "Entwurf", "active": "Aktiv", "closed": "Abgeschlossen"}
STATUS_NEXT = {"draft": "active", "active": "closed"}
TOURNAMENT_FIELDS = ["name", "date", "location", "organizer", "num_targets",
                     "shots_per_target", "scoring_rule_id", "start_groups", "description",
                     "notes"]
PARTICIPANT_FIELDS = ["bow_class_id", "start_number", "start_group", "start_time"]


def _full_load():
    return (selectinload(Tournament.scoring_rule), selectinload(Tournament.bow_classes),
            selectinload(Tournament.participants).selectinload(TournamentParticipant.archer),
            selectinload(Tournament.participants).selectinload(TournamentParticipant.bow_class))


def split_groups(text: str | None) -> list[str]:
    return [g.strip() for g in (text or "").split(",") if g.strip()]


# ---------------------------------------------------------------- tournaments

def list_tournaments(status: str | None = None) -> list[Tournament]:
    with session_scope() as s:
        q = select(Tournament).options(*_full_load())
        if status:
            q = q.where(Tournament.status == status)
        return list(s.scalars(q.order_by(Tournament.date.desc(), Tournament.id.desc())))


def get_tournament(tournament_id: int) -> Tournament | None:
    with session_scope() as s:
        return s.scalar(select(Tournament).options(*_full_load())
                        .where(Tournament.id == tournament_id))


def last_tournament() -> Tournament | None:
    items = list_tournaments()
    return items[0] if items else None


def save_tournament(data: dict, bow_class_ids: list[int],
                    tournament_id: int | None = None) -> Tournament:
    data = {k: v for k, v in data.items() if k in TOURNAMENT_FIELDS}
    if not (data.get("name") or "").strip():
        raise ValidationError("Turniername ist ein Pflichtfeld.")
    if not data.get("date"):
        raise ValidationError("Datum ist ein Pflichtfeld.")
    if int(data.get("num_targets") or 0) < 1:
        raise ValidationError("Mindestens eine Scheibe ist erforderlich.")
    if not data.get("scoring_rule_id"):
        raise ValidationError("Bitte ein Regelwerk auswählen.")
    if not bow_class_ids:
        raise ValidationError("Bitte mindestens eine Bogenklasse auswählen.")
    with session_scope() as s:
        rule = s.get(ScoringRule, data["scoring_rule_id"])
        if int(data.get("shots_per_target") or 1) > rule.max_shots_per_target:
            raise ValidationError(f"Das Regelwerk '{rule.name}' erlaubt höchstens "
                                  f"{rule.max_shots_per_target} Schuss je Scheibe.")
        if tournament_id is None:
            t = Tournament(status="draft", **data)
            s.add(t)
        else:
            t = s.get(Tournament, tournament_id)
            if t is None:
                raise ValidationError("Turnier nicht gefunden.")
            if t.status == "closed":
                raise ValidationError("Abgeschlossene Turniere können nicht geändert werden.")
            for k, v in data.items():
                setattr(t, k, v)
        t.bow_classes = list(s.scalars(select(BowClass).where(BowClass.id.in_(bow_class_ids))))
        s.flush()
        tid = t.id
    return get_tournament(tid)


def delete_tournament(tournament_id: int) -> None:
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        if t is not None:
            s.delete(t)


def set_status(tournament_id: int, new_status: str) -> None:
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        if STATUS_NEXT.get(t.status) != new_status:
            raise ValidationError(f"Statuswechsel von '{STATUS_LABELS[t.status]}' nach "
                                  f"'{STATUS_LABELS.get(new_status, new_status)}' nicht erlaubt.")
        t.status = new_status


# ---------------------------------------------------------------- participants

def _check_editable(t: Tournament) -> None:
    if t.status == "closed":
        raise ValidationError("Das Turnier ist abgeschlossen.")


def _pick_class(t: Tournament, archer: Archer, wanted: int | None) -> int | None:
    ids = [bc.id for bc in t.bow_classes]
    for cid in (wanted, archer.default_bow_class_id):
        if cid in ids:
            return cid
    return ids[0] if ids else None


def _add(s, t: Tournament, archer: Archer, bow_class_id: int | None = None,
         start_number: int | None = None, start_group: str | None = None) -> bool:
    if any(p.archer_id == archer.id for p in t.participants):
        return False
    groups = split_groups(t.start_groups)
    next_no = max((p.start_number or 0 for p in t.participants), default=0) + 1
    if start_group is None and groups:
        start_group = groups[len(t.participants) % len(groups)]
    t.participants.append(TournamentParticipant(
        archer=archer, bow_class_id=_pick_class(t, archer, bow_class_id),
        start_number=start_number or next_no, start_group=start_group))
    return True


def add_participants(tournament_id: int, archer_ids: list[int]) -> int:
    """Add archers from master data. Returns number added (already present are skipped)."""
    added = 0
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        for aid in archer_ids:
            added += _add(s, t, s.get(Archer, aid))
    return added


def update_participant(participant_id: int, data: dict) -> None:
    data = {k: v for k, v in data.items() if k in PARTICIPANT_FIELDS}
    with session_scope() as s:
        p = s.get(TournamentParticipant, participant_id)
        _check_editable(p.tournament)
        no = data.get("start_number")
        if no and s.scalar(select(func.count(TournamentParticipant.id)).where(
                TournamentParticipant.tournament_id == p.tournament_id,
                TournamentParticipant.start_number == no,
                TournamentParticipant.id != participant_id)):
            raise ValidationError(f"Startnummer {no} ist bereits vergeben.")
        for k, v in data.items():
            setattr(p, k, v or None)


def remove_participant(participant_id: int) -> None:
    with session_scope() as s:
        p = s.get(TournamentParticipant, participant_id)
        if p is not None:
            _check_editable(p.tournament)
            s.delete(p)


def participant_has_scores(participant_id: int) -> bool:
    with session_scope() as s:
        return bool(s.scalar(select(func.count(Score.id))
                             .where(Score.participant_id == participant_id)))


def assign_start_numbers(tournament_id: int) -> None:
    """Renumber 1..n ordered by bow class and name; distribute start groups round robin."""
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        parts = sorted(t.participants, key=lambda p: (
            p.bow_class.sort_order if p.bow_class else 9999,
            p.archer.last_name.lower(), p.archer.first_name.lower()))
        groups = split_groups(t.start_groups)
        for i, p in enumerate(parts):
            p.start_number = None
        s.flush()
        for i, p in enumerate(parts):
            p.start_number = i + 1
            if groups:
                p.start_group = groups[i % len(groups)]


def import_participants(tournament_id: int, records: list[dict], strategy: str) -> dict:
    """Records hold archer fields plus bow_class, start_number, start_group.

    strategy applies to the archer master data: 'skip' | 'update' | 'new'.
    """
    result = {"created": 0, "updated": 0, "skipped": 0, "added": 0}
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        classes = _bow_class_lookup(s)
        for rec in records:
            rec = dict(rec)
            bc_name = rec.pop("bow_class", None)
            start_number = rec.pop("start_number", None)
            start_group = rec.pop("start_group", None) or None
            rec = _clean_archer(rec)
            archer = None if strategy == "new" else find_archer(
                s, rec.get("member_number"), rec["first_name"], rec["last_name"],
                rec.get("birth_date"))
            if archer is None:
                archer = Archer(**rec)
                s.add(archer)
                s.flush()
                result["created"] += 1
            elif strategy == "update":
                for k, v in rec.items():
                    if v is not None:
                        setattr(archer, k, v)
                result["updated"] += 1
            else:
                result["skipped"] += 1
            cid = classes.get(str(bc_name).strip().lower()) if bc_name else None
            result["added"] += _add(s, t, archer, cid, start_number, start_group)
    return result

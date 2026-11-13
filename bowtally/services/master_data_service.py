# -*- coding: utf-8 -*-
"""CRUD for archers and bow classes."""
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from bowtally.database.engine import session_scope
from bowtally.database.models import (Archer, BowClass, TournamentParticipant,
                                      tournament_bow_classes)
from bowtally.services import ValidationError

ARCHER_FIELDS = ["first_name", "last_name", "birth_date", "club", "member_number", "email",
                 "phone", "default_bow_class_id", "notes", "active", "notify_new_tournament"]
BOW_CLASS_FIELDS = ["name", "abbreviation", "age_group", "description"]


# ---------------------------------------------------------------- archers

def list_archers(search: str = "", include_inactive: bool = False) -> list[Archer]:
    with session_scope() as s:
        q = select(Archer).options(selectinload(Archer.default_bow_class))
        if not include_inactive:
            q = q.where(Archer.active.is_(True))
        if search:
            like = f"%{search}%"
            q = q.where(or_(Archer.first_name.ilike(like), Archer.last_name.ilike(like),
                            Archer.club.ilike(like), Archer.member_number.ilike(like)))
        return list(s.scalars(q.order_by(Archer.last_name, Archer.first_name)))


def count_active_archers() -> int:
    with session_scope() as s:
        return s.scalar(select(func.count(Archer.id)).where(Archer.active.is_(True)))


def get_archer(archer_id: int) -> Archer | None:
    with session_scope() as s:
        return s.get(Archer, archer_id)


def _clean_archer(data: dict) -> dict:
    data = {k: v for k, v in data.items() if k in ARCHER_FIELDS}
    for k in ("first_name", "last_name"):
        if k in data:
            data[k] = (data[k] or "").strip()
            if not data[k]:
                raise ValidationError("Vor- und Nachname sind Pflichtfelder.")
    for k, v in list(data.items()):
        if isinstance(v, str) and k not in ("first_name", "last_name"):
            data[k] = v.strip() or None
    bd = data.get("birth_date")
    if bd is not None and not isinstance(bd, date):
        raise ValidationError(f"Ungültiges Geburtsdatum: {bd}")
    return data


def save_archer(data: dict, archer_id: int | None = None) -> Archer:
    data = _clean_archer(data)
    with session_scope() as s:
        if archer_id is None:
            for k in ("first_name", "last_name"):
                if not data.get(k):
                    raise ValidationError("Vor- und Nachname sind Pflichtfelder.")
            archer = Archer(**data)
            s.add(archer)
        else:
            archer = s.get(Archer, archer_id)
            if archer is None:
                raise ValidationError("Schütze nicht gefunden.")
            for k, v in data.items():
                setattr(archer, k, v)
        s.flush()
        return archer


def set_archer_active(archer_id: int, active: bool) -> None:
    """Soft delete / reactivate. Archers are never physically deleted."""
    with session_scope() as s:
        archer = s.get(Archer, archer_id)
        if archer is not None:
            archer.active = active


def delete_archer(archer_id: int) -> None:
    """Physical delete, only for archers without tournament data (else: deactivate)."""
    with session_scope() as s:
        archer = s.get(Archer, archer_id)
        if archer is None:
            return
        if s.scalar(select(func.count(TournamentParticipant.id))
                    .where(TournamentParticipant.archer_id == archer_id)):
            raise ValidationError(f"{archer.first_name} {archer.last_name} hat Turnierdaten und "
                                  "kann nicht gelöscht werden. Stattdessen deaktivieren.")
        s.delete(archer)


def archer_has_tournaments(archer_id: int) -> bool:
    with session_scope() as s:
        return bool(s.scalar(select(func.count(TournamentParticipant.id))
                             .where(TournamentParticipant.archer_id == archer_id)))


def get_archer_history(archer_id: int) -> list[dict]:
    """Return tournament participation rows for an archer, ordered newest first."""
    from bowtally.database.models import Tournament
    from sqlalchemy.orm import joinedload
    from bowtally.services import ranking_service
    with session_scope() as s:
        rows = list(s.scalars(
            select(TournamentParticipant)
            .options(joinedload(TournamentParticipant.tournament),
                     joinedload(TournamentParticipant.bow_class))
            .where(TournamentParticipant.archer_id == archer_id)
            .join(TournamentParticipant.tournament)
            .order_by(Tournament.date.desc())
        ))
        ranking_cache: dict[int, dict] = {}
        result = []
        for r in rows:
            tid = r.tournament_id
            if tid not in ranking_cache:
                try:
                    ranking_cache[tid] = {
                        rr.participant_id: rr
                        for class_rows in ranking_service.compute_ranking(tid).values()
                        for rr in class_rows
                    }
                except Exception:
                    ranking_cache[tid] = {}
            rr = ranking_cache[tid].get(r.id)
            result.append({"tournament_id": tid,
                           "name": r.tournament.name,
                           "date": r.tournament.date,
                           "bow_class": r.bow_class.name if r.bow_class else "–",
                           "registration_status": r.registration_status,
                           "payment_status": r.payment_status,
                           "participant_id": r.id,
                           "rank": rr.rank if rr else None,
                           "total": rr.total if rr else None})
        return result


def get_notifiable_archers() -> list[Archer]:
    """Archers with notify_new_tournament=True and a valid e-mail address."""
    with session_scope() as s:
        rows = list(s.scalars(
            select(Archer).where(Archer.active.is_(True),
                                 Archer.notify_new_tournament.is_(True),
                                 Archer.email.isnot(None),
                                 Archer.email != "")
            .order_by(Archer.last_name, Archer.first_name)
        ))
        return rows


def find_archer(s, member_number: str | None, first_name: str, last_name: str,
                birth_date: date | None = None) -> Archer | None:
    """Duplicate lookup: member number wins, else name (+ birth date when given)."""
    if member_number:
        hit = s.scalar(select(Archer).where(Archer.member_number == member_number))
        if hit is not None:
            return hit
    q = select(Archer).where(func.lower(Archer.first_name) == first_name.lower(),
                             func.lower(Archer.last_name) == last_name.lower())
    if birth_date:
        q = q.where(or_(Archer.birth_date == birth_date, Archer.birth_date.is_(None)))
    return s.scalars(q).first()


def import_archers(records: list[dict], strategy: str) -> dict:
    """strategy: 'skip' | 'update' | 'new'. Returns counters."""
    result = {"created": 0, "updated": 0, "skipped": 0}
    with session_scope() as s:
        classes = _bow_class_lookup(s)
        for rec in records:
            rec = dict(rec)
            bc = rec.pop("default_bow_class", None)
            if bc:
                rec["default_bow_class_id"] = classes.get(str(bc).strip().lower())
            rec = _clean_archer(rec)
            existing = None if strategy == "new" else find_archer(
                s, rec.get("member_number"), rec["first_name"], rec["last_name"],
                rec.get("birth_date"))
            if existing is None:
                s.add(Archer(**rec))
                result["created"] += 1
            elif strategy == "update":
                for k, v in rec.items():
                    if v is not None:
                        setattr(existing, k, v)
                result["updated"] += 1
            else:
                result["skipped"] += 1
    return result


# ---------------------------------------------------------------- bow classes

def _bow_class_lookup(s) -> dict[str, int]:
    """name / abbreviation (lowercase) -> id"""
    out = {}
    for bc in s.scalars(select(BowClass)):
        out[bc.name.lower()] = bc.id
        if bc.abbreviation:
            out[bc.abbreviation.lower()] = bc.id
    return out


def list_bow_classes() -> list[BowClass]:
    with session_scope() as s:
        return list(s.scalars(select(BowClass).order_by(BowClass.sort_order, BowClass.id)))


def save_bow_class(data: dict, class_id: int | None = None) -> BowClass:
    data = {k: (v.strip() if isinstance(v, str) else v) or None
            for k, v in data.items() if k in BOW_CLASS_FIELDS}
    if not data.get("name"):
        raise ValidationError("Name ist ein Pflichtfeld.")
    with session_scope() as s:
        if class_id is None:
            max_order = s.scalar(select(func.max(BowClass.sort_order))) or 0
            bc = BowClass(sort_order=max_order + 1, is_builtin=False, **data)
            s.add(bc)
        else:
            bc = s.get(BowClass, class_id)
            if bc is None:
                raise ValidationError("Bogenklasse nicht gefunden.")
            if bc.is_builtin:
                raise ValidationError("Standard-Bogenklassen sind schreibgeschützt. "
                                      "Bitte kopieren.")
            for k, v in data.items():
                setattr(bc, k, v)
        s.flush()
        return bc


def clone_bow_class(class_id: int) -> BowClass:
    with session_scope() as s:
        src = s.get(BowClass, class_id)
        names = set(s.scalars(select(BowClass.name)))
    name = f"{src.name} (Kopie)"
    i = 2
    while name in names:
        name = f"{src.name} (Kopie {i})"
        i += 1
    return save_bow_class({"name": name, "abbreviation": src.abbreviation,
                           "age_group": src.age_group, "description": src.description})


def import_bow_classes(records: list[dict], strategy: str) -> dict:
    """strategy: 'skip' | 'update' | 'new'. Returns counters."""
    result = {"created": 0, "updated": 0, "skipped": 0}
    with session_scope() as s:
        for rec in records:
            name = (rec.get("name") or "").strip()
            if not name:
                continue
            existing = None if strategy == "new" else s.scalars(
                select(BowClass).where(func.lower(BowClass.name) == name.lower(),
                                       BowClass.is_builtin.is_(False))).first()
            if existing is None:
                max_order = s.scalar(select(func.max(BowClass.sort_order))) or 0
                s.add(BowClass(sort_order=max_order + 1, is_builtin=False,
                               **{k: (v.strip() if isinstance(v, str) else v) or None
                                  for k, v in rec.items() if k in BOW_CLASS_FIELDS}))
                result["created"] += 1
            elif strategy == "update":
                for k, v in rec.items():
                    if k in BOW_CLASS_FIELDS and v is not None:
                        setattr(existing, k, (v.strip() if isinstance(v, str) else v) or None)
                result["updated"] += 1
            else:
                result["skipped"] += 1
    return result


def delete_bow_class(class_id: int) -> None:
    with session_scope() as s:
        bc = s.get(BowClass, class_id)
        if bc is None:
            return
        if bc.is_builtin:
            raise ValidationError("Standard-Bogenklassen können nicht gelöscht werden.")
        in_use = (s.scalar(select(func.count()).select_from(TournamentParticipant)
                           .where(TournamentParticipant.bow_class_id == class_id))
                  or s.scalar(select(func.count()).select_from(tournament_bow_classes)
                              .where(tournament_bow_classes.c.bow_class_id == class_id))
                  or s.scalar(select(func.count(Archer.id))
                              .where(Archer.default_bow_class_id == class_id)))
        if in_use:
            raise ValidationError("Die Bogenklasse wird noch verwendet und kann nicht "
                                  "gelöscht werden.")
        s.delete(bc)


def reorder_bow_classes(ordered_ids: list[int]) -> None:
    with session_scope() as s:
        for pos, cid in enumerate(ordered_ids, start=1):
            bc = s.get(BowClass, cid)
            if bc is not None:
                bc.sort_order = pos

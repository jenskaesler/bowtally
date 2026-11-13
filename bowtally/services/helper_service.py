# -*- coding: utf-8 -*-
"""Helper management: global master data and per-tournament assignments."""
from sqlalchemy import select

from bowtally.database.engine import session_scope
from bowtally.database.models import Helper, TournamentHelper
from bowtally.services import ValidationError


def _load(th: TournamentHelper) -> TournamentHelper:
    """Pre-load helper relationship so the object is usable after session close."""
    _ = th.helper.first_name
    return th


def list_helpers(include_inactive: bool = False) -> list[Helper]:
    with session_scope() as s:
        q = select(Helper).order_by(Helper.last_name, Helper.first_name)
        if not include_inactive:
            q = q.where(Helper.active == True)  # noqa: E712
        return s.scalars(q).all()


def set_active(helper_id: int, active: bool) -> None:
    with session_scope() as s:
        s.get(Helper, helper_id).active = active


def list_tournament_helpers(tournament_id: int) -> list[TournamentHelper]:
    with session_scope() as s:
        rows = s.scalars(
            select(TournamentHelper)
            .where(TournamentHelper.tournament_id == tournament_id)
            .order_by(TournamentHelper.id)
        ).all()
        for r in rows:
            _load(r)
        return rows


def get_tournament_helper(assignment_id: int) -> TournamentHelper:
    with session_scope() as s:
        return _load(s.get(TournamentHelper, assignment_id))


def _validate(data: dict) -> None:
    if not (data.get("first_name") or "").strip():
        raise ValidationError("Vorname ist ein Pflichtfeld")
    if not (data.get("last_name") or "").strip():
        raise ValidationError("Nachname ist ein Pflichtfeld")


def create_and_assign(tournament_id: int, data: dict) -> TournamentHelper:
    _validate(data)
    with session_scope() as s:
        h = Helper()
        for k in ("first_name", "last_name", "phone", "email", "notes"):
            setattr(h, k, (data.get(k) or "").strip() or None)
        s.add(h)
        s.flush()
        th = TournamentHelper(
            tournament_id=tournament_id, helper_id=h.id,
            task=(data.get("task") or "").strip() or None,
            time_from=(data.get("time_from") or "").strip() or None,
            time_to=(data.get("time_to") or "").strip() or None,
            confirmed=bool(data.get("confirmed")),
        )
        s.add(th)
        s.flush()
        th.helper = h
        return th


def assign_existing(tournament_id: int, helper_id: int) -> TournamentHelper:
    with session_scope() as s:
        th = TournamentHelper(tournament_id=tournament_id, helper_id=helper_id)
        s.add(th)
        s.flush()
        return _load(th)


def update_assignment(assignment_id: int, data: dict) -> TournamentHelper:
    _validate(data)
    with session_scope() as s:
        th = s.get(TournamentHelper, assignment_id)
        h = th.helper
        for k in ("first_name", "last_name", "phone", "email", "notes"):
            setattr(h, k, (data.get(k) or "").strip() or None)
        th.task = (data.get("task") or "").strip() or None
        th.time_from = (data.get("time_from") or "").strip() or None
        th.time_to = (data.get("time_to") or "").strip() or None
        th.confirmed = bool(data.get("confirmed"))
        s.flush()
        return _load(th)


def remove_assignment(assignment_id: int) -> None:
    with session_scope() as s:
        th = s.get(TournamentHelper, assignment_id)
        s.delete(th)


def set_confirmed(assignment_id: int, confirmed: bool) -> None:
    with session_scope() as s:
        s.get(TournamentHelper, assignment_id).confirmed = confirmed


def get_helper(helper_id: int) -> Helper:
    with session_scope() as s:
        h = s.get(Helper, helper_id)
        _ = h.first_name
        return h


def create_helper(data: dict) -> Helper:
    _validate(data)
    with session_scope() as s:
        h = Helper()
        for k in ("first_name", "last_name", "phone", "email", "notes"):
            setattr(h, k, (data.get(k) or "").strip() or None)
        if "active" in data:
            h.active = bool(data["active"])
        s.add(h)
        s.flush()
        _ = h.first_name
        return h


def update_helper(helper_id: int, data: dict) -> Helper:
    _validate(data)
    with session_scope() as s:
        h = s.get(Helper, helper_id)
        for k in ("first_name", "last_name", "phone", "email", "notes"):
            setattr(h, k, (data.get(k) or "").strip() or None)
        if "active" in data:
            h.active = bool(data["active"])
        s.flush()
        _ = h.first_name
        return h


def helper_has_assignments(helper_id: int) -> bool:
    with session_scope() as s:
        return bool(s.scalars(
            select(TournamentHelper.id).where(TournamentHelper.helper_id == helper_id)
        ).first())


def delete_helper(helper_id: int) -> None:
    with session_scope() as s:
        s.delete(s.get(Helper, helper_id))


def get_helper_history(helper_id: int) -> list[dict]:
    from bowtally.database.models import Tournament
    with session_scope() as s:
        rows = s.execute(
            select(
                Tournament.name, Tournament.date,
                TournamentHelper.task, TournamentHelper.time_from,
                TournamentHelper.time_to, TournamentHelper.confirmed,
            )
            .join(Tournament, TournamentHelper.tournament_id == Tournament.id)
            .where(TournamentHelper.helper_id == helper_id)
            .order_by(Tournament.date.desc())
        ).all()
        return [
            {"name": r.name, "date": r.date, "task": r.task,
             "time_from": r.time_from, "time_to": r.time_to, "confirmed": r.confirmed}
            for r in rows
        ]


def import_helpers(records: list[dict], strategy: str) -> dict:
    created = updated = skipped = 0
    with session_scope() as s:
        for r in records:
            first = (r.get("first_name") or "").strip()
            last = (r.get("last_name") or "").strip()
            existing = s.scalars(
                select(Helper).where(Helper.first_name == first, Helper.last_name == last)
            ).first()
            if existing:
                if strategy == "skip":
                    skipped += 1
                    continue
                for k in ("phone", "email", "notes"):
                    setattr(existing, k, (r.get(k) or "").strip() or None)
                updated += 1
            else:
                h = Helper(first_name=first, last_name=last, active=True)
                for k in ("phone", "email", "notes"):
                    setattr(h, k, (r.get(k) or "").strip() or None)
                s.add(h)
                created += 1
    return {"created": created, "updated": updated, "skipped": skipped}

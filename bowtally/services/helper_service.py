# -*- coding: utf-8 -*-
"""Tournament helpers: assignments of club members or manually entered persons."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bowtally.database.engine import session_scope
from bowtally.database.models import Member, TournamentHelper
from bowtally.services import ValidationError

_OWN_FIELDS = ("first_name", "last_name", "phone", "email")


def _clean(value) -> str | None:
    return (value or "").strip() or None


def _assignment_fields(th: TournamentHelper, data: dict) -> None:
    th.task = _clean(data.get("task"))
    th.time_from = _clean(data.get("time_from"))
    th.time_to = _clean(data.get("time_to"))
    th.confirmed = bool(data.get("confirmed"))


def display_contact(th: TournamentHelper) -> tuple[str, str, str]:
    """(name 'Nachname, Vorname', phone, email) from the linked member or the own fields."""
    src = th.member or th
    name = f"{src.last_name or ''}, {src.first_name or ''}".strip(", ")
    return name, src.phone or "", src.email or ""


def list_tournament_helpers(tournament_id: int) -> list[TournamentHelper]:
    with session_scope() as s:
        return s.scalars(
            select(TournamentHelper)
            .options(selectinload(TournamentHelper.member))
            .where(TournamentHelper.tournament_id == tournament_id)
            .order_by(TournamentHelper.id)
        ).all()


def get_tournament_helper(assignment_id: int) -> TournamentHelper:
    with session_scope() as s:
        th = s.get(TournamentHelper, assignment_id)
        _ = th.member
        return th


def list_assignable_members(tournament_id: int) -> list[Member]:
    """Active tournament-helper members not yet assigned to this tournament."""
    assigned = select(TournamentHelper.member_id).where(
        TournamentHelper.tournament_id == tournament_id, TournamentHelper.member_id.is_not(None))
    with session_scope() as s:
        return s.scalars(
            select(Member)
            .where(Member.active == True, Member.is_tournament_helper == True,  # noqa: E712
                   Member.id.not_in(assigned))
            .order_by(Member.last_name, Member.first_name)
        ).all()


def create_manual(tournament_id: int, data: dict) -> TournamentHelper:
    """Helper for this tournament only: no member link, no master record, no history."""
    _validate_name(data)
    with session_scope() as s:
        th = TournamentHelper(tournament_id=tournament_id,
                              **{k: _clean(data.get(k)) for k in _OWN_FIELDS})
        _assignment_fields(th, data)
        s.add(th)
        s.flush()
        _ = th.member  # load while the session is open
        return th


def assign_member(tournament_id: int, member_id: int) -> TournamentHelper:
    with session_scope() as s:
        member = s.get(Member, member_id)
        if member is None or not (member.active and member.is_tournament_helper):
            raise ValidationError("Nur aktive Mitglieder, die als Turnierhelfer markiert sind, "
                                  "können zugewiesen werden")
        if s.scalars(select(TournamentHelper.id).where(
                TournamentHelper.tournament_id == tournament_id,
                TournamentHelper.member_id == member_id)).first():
            raise ValidationError(f"{member.full_name} ist diesem Turnier bereits zugewiesen")
        th = TournamentHelper(tournament_id=tournament_id, member_id=member_id)
        s.add(th)
        s.flush()
        th.member = member
        return th


def update_assignment(assignment_id: int, data: dict) -> TournamentHelper:
    with session_scope() as s:
        th = s.get(TournamentHelper, assignment_id)
        if th.member_id is None:
            _validate_name(data)
            for k in _OWN_FIELDS:
                setattr(th, k, _clean(data.get(k)))
        _assignment_fields(th, data)  # linked helper: member master data stays untouched
        s.flush()
        _ = th.member
        return th


def remove_assignment(assignment_id: int) -> None:
    with session_scope() as s:
        s.delete(s.get(TournamentHelper, assignment_id))


def set_confirmed(assignment_id: int, confirmed: bool) -> None:
    with session_scope() as s:
        s.get(TournamentHelper, assignment_id).confirmed = confirmed


def _validate_name(data: dict) -> None:
    if not _clean(data.get("first_name")):
        raise ValidationError("Vorname ist ein Pflichtfeld")
    if not _clean(data.get("last_name")):
        raise ValidationError("Nachname ist ein Pflichtfeld")

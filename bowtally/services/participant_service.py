# -*- coding: utf-8 -*-
"""Registration, payment and check-in status of tournament participants."""
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bowtally.database.engine import session_scope
from bowtally.database.models import (PAYMENT_STATUSES, REGISTRATION_STATUSES, Archer, EntryFee,
                                      Tournament, TournamentParticipant)
from bowtally.services import ValidationError
from bowtally.services.master_data_service import _clean_archer
from bowtally.services.tournament_service import (CapacityInfo, _add, _check_editable,
                                                  capacity_info)

REGISTRATION_LABELS = {
    "registered": "Gemeldet", "confirmed": "Bestätigt", "checked_in": "Eingecheckt",
    "dns": "Nicht gestartet", "dnf": "Abgebrochen", "dsq": "Disqualifiziert",
    "withdrawn": "Zurückgezogen", "waitlisted": "Auf Warteliste",
}
PAYMENT_LABELS = {"unpaid": "Ausstehend", "pending": "Erwartet", "paid": "Bezahlt"}


def _participant(s, participant_id: int) -> TournamentParticipant:
    p = s.get(TournamentParticipant, participant_id)
    if p is None:
        raise ValidationError("Teilnehmer nicht gefunden.")
    _check_editable(p.tournament)
    return p


def _apply_registration(p: TournamentParticipant, status: str) -> None:
    if status not in REGISTRATION_STATUSES:
        raise ValidationError(f"Unbekannter Anmeldestatus '{status}'.")
    if status in ("confirmed", "checked_in") and p.confirmation_date is None:
        p.confirmation_date = date.today()
    if status == "checked_in":
        p.checkin_time = datetime.now()
    p.registration_status = status


def _apply_payment(p: TournamentParticipant, status: str, amount=None, when=None) -> None:
    if status not in PAYMENT_STATUSES:
        raise ValidationError(f"Unbekannter Zahlungsstatus '{status}'.")
    p.payment_status = status
    if status == "paid":
        p.payment_date = when or p.payment_date or date.today()
        if amount is not None:
            p.fee_amount_paid = amount
        elif p.fee_amount_paid is None and p.entry_fee is not None:
            p.fee_amount_paid = p.entry_fee.amount
    else:
        p.payment_date = None
        p.fee_amount_paid = None


def set_registration_status(participant_id: int, status: str) -> None:
    with session_scope() as s:
        _apply_registration(_participant(s, participant_id), status)


def set_payment_status(participant_id: int, status: str, amount: float | None = None,
                       when: date | None = None) -> None:
    with session_scope() as s:
        _apply_payment(_participant(s, participant_id), status, amount, when)


def set_entry_fee(participant_id: int, fee_id: int | None) -> None:
    with session_scope() as s:
        p = _participant(s, participant_id)
        if fee_id is not None and s.get(EntryFee, fee_id).tournament_id != p.tournament_id:
            raise ValidationError("Die Startgebühr gehört nicht zu diesem Turnier.")
        p.entry_fee_id = fee_id


def checkin(participant_id: int) -> None:
    set_registration_status(participant_id, "checked_in")


def bulk_confirm(participant_ids: list[int]) -> int:
    """Confirm 'registered' participants. Returns how many changed."""
    changed = 0
    with session_scope() as s:
        for pid in participant_ids:
            p = _participant(s, pid)
            if p.registration_status == "registered":
                _apply_registration(p, "confirmed")
                changed += 1
    return changed


def confirm_with_payment(participant_ids: list[int], fee_id: int | None,
                          payment_status: str, fee_amount_paid: float | None,
                          payment_date: date | None) -> int:
    """Confirm registered/waitlisted participants and capture payment. Returns count confirmed."""
    changed = 0
    with session_scope() as s:
        for pid in participant_ids:
            p = _participant(s, pid)
            if p.registration_status not in ("registered", "waitlisted"):
                continue
            if fee_id is not None:
                p.entry_fee_id = fee_id or None
            _apply_registration(p, "confirmed")
            _apply_payment(p, payment_status, fee_amount_paid, payment_date)
            changed += 1
    return changed


def bulk_mark_paid(participant_ids: list[int]) -> int:
    changed = 0
    with session_scope() as s:
        for pid in participant_ids:
            p = _participant(s, pid)
            if p.payment_status != "paid":
                _apply_payment(p, "paid")
                changed += 1
    return changed


def search_for_checkin(tournament_id: int, query: str) -> list[TournamentParticipant]:
    """Match start number exactly, or name / club / member number as substring."""
    query = (query or "").strip().lower()
    with session_scope() as s:
        parts = list(s.scalars(
            select(TournamentParticipant)
            .options(selectinload(TournamentParticipant.archer),
                     selectinload(TournamentParticipant.bow_class),
                     selectinload(TournamentParticipant.entry_fee))
            .where(TournamentParticipant.tournament_id == tournament_id)))
    if query:
        if query.isdigit():
            exact = [p for p in parts if p.start_number == int(query)]
            if exact:
                return exact
        parts = [p for p in parts if query in " ".join(
            filter(None, (p.archer.first_name, p.archer.last_name, p.archer.club,
                          p.archer.pass_number, f"{p.archer.first_name} {p.archer.last_name}",
                          f"{p.archer.last_name} {p.archer.first_name}"))).lower()]
    return sorted(parts, key=lambda p: (p.registration_status == "checked_in",
                                        p.archer.last_name.lower(), p.archer.first_name.lower()))


def get_capacity_info(tournament_id: int) -> CapacityInfo:
    return capacity_info(tournament_id)


def register_walk_in(tournament_id: int, archer_data: dict, bow_class_id: int,
                     entry_fee_id: int | None, paid: bool) -> TournamentParticipant:
    """Create archer (or reuse by name) and check them in directly. Counts toward capacity."""
    from bowtally.services.master_data_service import find_archer
    archer_data = _clean_archer(archer_data)
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        archer = find_archer(s, archer_data.get("pass_number"), archer_data["first_name"],
                             archer_data["last_name"])
        if archer is None:
            archer = Archer(**archer_data)
            s.add(archer)
            s.flush()
        p = _add(s, t, archer, bow_class_id, entry_fee_id=entry_fee_id)
        if p is None:
            raise ValidationError(f"{archer.first_name} {archer.last_name} ist bereits "
                                  "Teilnehmer dieses Turniers.")
        s.flush()
        s.refresh(p)            # loads the entry_fee relationship for the paid amount
        _apply_registration(p, "checked_in")
        if paid:
            _apply_payment(p, "paid")
        return p

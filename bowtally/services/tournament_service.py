# -*- coding: utf-8 -*-
"""Tournaments, phase lifecycle, entry fees, participants and tournament statistics."""
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bowtally.database.engine import session_scope
from bowtally.database.models import (Archer, BowClass, EntryFee, PhaseTransitionLog, Score,
                                      ScoringRule, Tournament, TournamentParticipant)
from bowtally.database.seed import TOURNAMENT_PHASES
from bowtally.services import ValidationError
from bowtally.services.master_data_service import _bow_class_lookup, _clean_archer, find_archer

PHASES = [key for key, *_ in TOURNAMENT_PHASES]
PHASE_LABELS = {key: label for key, label, *_ in TOURNAMENT_PHASES}
PHASE_DESCRIPTIONS = {key: desc for key, _l, _o, desc in TOURNAMENT_PHASES}
# legacy status column, derived from the phase (score entry / locks still use it)
PHASE_STATUS = {"shooting": "active", "scoring": "active", "closed": "closed"}
INACTIVE_REGISTRATION = ("withdrawn", "dsq")              # do not count for capacity
EXPECTED_REGISTRATION = ("registered", "confirmed", "checked_in")
REVENUE_REGISTRATION = ("confirmed", "checked_in")
CHECKLIST_ITEMS = {
    "parcours_ready": "Parcours aufgebaut",
    "helpers_assigned": "Helfer eingeteilt",
    "checkin_desk_ready": "Einschreibetisch vorbereitet",
    "ceremony_ready": "Siegerehrung vorbereitet",
    "results_published": "Ergebnisliste ausgehängt / versendet",
}
CHECKLIST_NOTES_KEY = "helpers_notes"

BASE_FIELDS = ["name", "date", "location", "organizer", "num_targets", "shots_per_target",
               "scoring_rule_id", "start_groups", "description", "notes"]
DETAIL_FIELDS = ["registration_deadline", "max_participants", "checkin_start_time",
                 "shooting_start_time", "practice_allowed", "practice_location",
                 "bank_account_holder", "bank_iban", "bank_bic", "bank_reference_template",
                 "contact_name", "contact_phone", "contact_email", "legal_notes",
                 "additional_info"]
TOURNAMENT_FIELDS = BASE_FIELDS + DETAIL_FIELDS
PARTICIPANT_FIELDS = ["bow_class_id", "start_number", "start_group", "start_time",
                      "entry_fee_id", "notes", "payment_notes"]


def _full_load():
    return (selectinload(Tournament.scoring_rule), selectinload(Tournament.bow_classes),
            selectinload(Tournament.fees),
            selectinload(Tournament.participants).selectinload(TournamentParticipant.archer),
            selectinload(Tournament.participants).selectinload(TournamentParticipant.bow_class),
            selectinload(Tournament.participants).selectinload(TournamentParticipant.entry_fee))


def split_groups(text: str | None) -> list[str]:
    return [g.strip() for g in (text or "").split(",") if g.strip()]


def phase_index(phase: str) -> int:
    return PHASES.index(phase) if phase in PHASES else 0


def next_phase(phase: str) -> str | None:
    i = phase_index(phase)
    return PHASES[i + 1] if i + 1 < len(PHASES) else None


def prev_phase(phase: str) -> str | None:
    i = phase_index(phase)
    return PHASES[i - 1] if i > 0 else None


def is_active_participant(p) -> bool:
    return p.registration_status not in INACTIVE_REGISTRATION


def announcement_outdated(t: Tournament) -> bool:
    """True if the announcement PDF exists but tournament data changed afterwards."""
    return bool(t.announcement_generated_at and t.content_changed_at
                and t.content_changed_at > t.announcement_generated_at)


# ---------------------------------------------------------------- tournaments

def list_tournaments(phase: str | None = None, open_only: bool = False) -> list[Tournament]:
    with session_scope() as s:
        q = select(Tournament).options(*_full_load())
        if phase:
            q = q.where(Tournament.phase == phase)
        if open_only:
            q = q.where(Tournament.phase != "closed")
        return list(s.scalars(q.order_by(Tournament.date.desc(), Tournament.id.desc())))


def get_tournament(tournament_id: int) -> Tournament | None:
    with session_scope() as s:
        return s.scalar(select(Tournament).options(*_full_load())
                        .where(Tournament.id == tournament_id))


def last_tournament() -> Tournament | None:
    items = list_tournaments()
    return items[0] if items else None


def _clean_tournament(data: dict) -> dict:
    data = {k: (v.strip() or None) if isinstance(v, str) else v
            for k, v in data.items() if k in TOURNAMENT_FIELDS}
    if "max_participants" in data and not data["max_participants"]:
        data["max_participants"] = None        # 0 = unlimited
    return data


def save_tournament(data: dict, bow_class_ids: list[int], tournament_id: int | None = None,
                    fees: list[dict] | None = None) -> Tournament:
    """Create or update. fees=None on create copies the fee templates; a list replaces
    the tournament's fees (rows with 'id' are updated, missing unused ones deleted)."""
    data = _clean_tournament(data)
    if not data.get("name"):
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
            t = Tournament(status="draft", phase="draft", phase_changed_at=datetime.now(),
                           checklist_state={}, **data)
            s.add(t)
            s.flush()
            if fees is None:
                fees = [{"name": f.name, "amount": f.amount, "description": f.description}
                        for f in _fee_templates(s)]
        else:
            t = s.get(Tournament, tournament_id)
            if t is None:
                raise ValidationError("Turnier nicht gefunden.")
            if t.status == "closed":
                raise ValidationError("Abgeschlossene Turniere können nicht geändert werden.")
            for k, v in data.items():
                setattr(t, k, v)
        t.bow_classes = list(s.scalars(select(BowClass).where(BowClass.id.in_(bow_class_ids))))
        if fees is not None:
            _sync_fees(s, t, fees)
        t.content_changed_at = datetime.now()
        s.flush()
        tid = t.id
    return get_tournament(tid)


def update_tournament_fields(tournament_id: int, data: dict) -> None:
    """Partial update of detail fields (e.g. post-event notes) without re-validation."""
    data = _clean_tournament(data)
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        for k, v in data.items():
            setattr(t, k, v)
        if set(data) - {"notes"}:
            t.content_changed_at = datetime.now()


def delete_tournament(tournament_id: int) -> None:
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        if t is not None:
            s.delete(t)


def mark_announcement_generated(tournament_id: int) -> None:
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        now = datetime.now()
        t.announcement_generated_at = now
        if t.announced_at is None:
            t.announced_at = now


def mark_results_generated(tournament_id: int) -> None:
    with session_scope() as s:
        s.get(Tournament, tournament_id).results_generated_at = datetime.now()


# ---------------------------------------------------------------- entry fees

def _fee_templates(s) -> list[EntryFee]:
    return list(s.scalars(select(EntryFee).where(EntryFee.tournament_id.is_(None))
                          .order_by(EntryFee.sort_order, EntryFee.id)))


def list_fee_templates() -> list[EntryFee]:
    with session_scope() as s:
        return _fee_templates(s)


def list_fees(tournament_id: int) -> list[EntryFee]:
    with session_scope() as s:
        return list(s.scalars(select(EntryFee).where(EntryFee.tournament_id == tournament_id)
                              .order_by(EntryFee.sort_order, EntryFee.id)))


def fee_usage(tournament_id: int) -> dict[int, int]:
    """fee id -> number of participants with this fee."""
    with session_scope() as s:
        rows = s.execute(select(TournamentParticipant.entry_fee_id, func.count())
                         .where(TournamentParticipant.tournament_id == tournament_id,
                                TournamentParticipant.entry_fee_id.is_not(None))
                         .group_by(TournamentParticipant.entry_fee_id))
        return {fid: n for fid, n in rows}


def _clean_fee(data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValidationError("Name der Startgebühr ist ein Pflichtfeld.")
    try:
        amount = round(float(str(data.get("amount")).replace(",", ".")), 2)
    except (TypeError, ValueError):
        raise ValidationError(f"Ungültiger Betrag für '{name}'.") from None
    if amount < 0:
        raise ValidationError(f"Der Betrag für '{name}' darf nicht negativ sein.")
    return {"name": name, "amount": amount,
            "description": (data.get("description") or "").strip() or None}


def _sync_fees(s, t: Tournament, fees: list[dict]) -> None:
    existing = {f.id: f for f in s.scalars(select(EntryFee)
                                           .where(EntryFee.tournament_id == t.id))}
    keep = set()
    for i, raw in enumerate(fees, start=1):
        data = _clean_fee(raw)
        fee = existing.get(raw.get("id"))
        if fee is None:
            fee = EntryFee(tournament_id=t.id)
            s.add(fee)
        for k, v in data.items():
            setattr(fee, k, v)
        fee.sort_order = i
        if fee.id:
            keep.add(fee.id)
    for fid, fee in existing.items():
        if fid not in keep:
            _delete_fee(s, fee)


def _delete_fee(s, fee: EntryFee) -> None:
    used = s.scalar(select(func.count(TournamentParticipant.id))
                    .where(TournamentParticipant.entry_fee_id == fee.id))
    if used:
        raise ValidationError(f"Die Startgebühr '{fee.name}' ist {used} Teilnehmern zugewiesen "
                              "und kann nicht gelöscht werden.")
    s.delete(fee)


def save_fee(tournament_id: int, data: dict, fee_id: int | None = None) -> EntryFee:
    data = _clean_fee(data)
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        if fee_id is None:
            order = s.scalar(select(func.max(EntryFee.sort_order))
                             .where(EntryFee.tournament_id == tournament_id)) or 0
            fee = EntryFee(tournament_id=tournament_id, sort_order=order + 1, **data)
            s.add(fee)
        else:
            fee = s.get(EntryFee, fee_id)
            for k, v in data.items():
                setattr(fee, k, v)
        t.content_changed_at = datetime.now()
        s.flush()
        return fee


def delete_fee(fee_id: int) -> None:
    with session_scope() as s:
        fee = s.get(EntryFee, fee_id)
        if fee is None:
            return
        t = s.get(Tournament, fee.tournament_id)
        _check_editable(t)
        _delete_fee(s, fee)
        t.content_changed_at = datetime.now()


def load_fee_templates(tournament_id: int) -> int:
    """Append copies of the fee templates. Returns the number of fees added."""
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        order = s.scalar(select(func.max(EntryFee.sort_order))
                         .where(EntryFee.tournament_id == tournament_id)) or 0
        templates = _fee_templates(s)
        for i, tpl in enumerate(templates, start=1):
            s.add(EntryFee(tournament_id=tournament_id, name=tpl.name, amount=tpl.amount,
                           description=tpl.description, sort_order=order + i))
        t.content_changed_at = datetime.now()
        return len(templates)


# ---------------------------------------------------------------- phase lifecycle

@dataclass
class Condition:
    label: str
    severity: str            # 'blocker' | 'warning'
    ok: bool
    message: str = ""        # shown when not ok


@dataclass
class TransitionResult:
    ok: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    applied: bool = False


def _count_scores_by_participant(s, tournament_id: int) -> dict[int, int]:
    rows = s.execute(select(Score.participant_id, func.count())
                     .join(TournamentParticipant)
                     .where(TournamentParticipant.tournament_id == tournament_id)
                     .group_by(Score.participant_id))
    return {pid: n for pid, n in rows}


def get_phase_conditions(tournament_id: int, target_phase: str | None = None) -> list[Condition]:
    """Conditions for the transition into target_phase (default: the next phase)."""
    t = get_tournament(tournament_id)
    target = target_phase or next_phase(t.phase)
    parts = t.participants
    by_status = lambda st: [p for p in parts if p.registration_status == st]  # noqa: E731
    not_paid = [p for p in parts if is_active_participant(p) and p.payment_status != "paid"]
    today = date.today()
    c: list[Condition] = []
    if target == "preparation":
        c += [Condition("Regelwerk zugewiesen", "blocker", t.scoring_rule_id is not None,
                        "Kein Regelwerk zugewiesen"),
              Condition("Bogenklassen zugewiesen", "blocker", bool(t.bow_classes),
                        "Keine Bogenklassen zugewiesen"),
              Condition("Turnierdatum in der Zukunft", "blocker", t.date >= today,
                        "Das Turnierdatum liegt in der Vergangenheit"),
              Condition("Kontaktname hinterlegt", "warning", bool(t.contact_name),
                        "Kein Kontaktname hinterlegt"),
              Condition("Bankverbindung hinterlegt", "warning", bool(t.bank_iban),
                        "Keine Bankverbindung hinterlegt"),
              Condition("Ausschreibung generiert", "warning", t.announced_at is not None,
                        "Das Ausschreibungs-PDF wurde noch nie generiert")]
    elif target == "registration":
        c += [Condition("Startgebühren definiert", "blocker", bool(t.fees),
                        "Keine Startgebühren definiert"),
              Condition("Anmeldefrist gesetzt", "blocker", t.registration_deadline is not None,
                        "Anmeldefrist nicht gesetzt"),
              Condition("Ausschreibung aktuell", "warning",
                        t.announced_at is not None and not announcement_outdated(t),
                        "Das Ausschreibungs-PDF wurde seit der letzten Datenänderung nicht "
                        "neu generiert"),
              Condition("Maximale Teilnehmerzahl gesetzt", "warning",
                        t.max_participants is not None,
                        "Maximale Teilnehmerzahl nicht gesetzt")]
    elif target == "checkin":
        registered = by_status("registered")
        c += [Condition("Bestätigte Teilnehmer vorhanden", "blocker",
                        bool(by_status("confirmed") or by_status("checked_in")),
                        "Keine Teilnehmer mit bestätigter Anmeldung vorhanden"),
              Condition("Alle Anmeldungen bestätigt", "warning", not registered,
                        f"{len(registered)} Teilnehmer sind gemeldet, aber nicht bestätigt"),
              Condition("Alle Startgebühren bezahlt", "warning", not not_paid,
                        f"{len(not_paid)} Teilnehmer haben noch nicht bezahlt"),
              Condition("Anmeldefrist abgelaufen", "warning",
                        t.registration_deadline is None or t.registration_deadline <= today,
                        "Die Anmeldefrist liegt noch in der Zukunft")]
    elif target == "shooting":
        checked = by_status("checked_in")
        missing = [p for p in parts if p.registration_status in ("registered", "confirmed")]
        c += [Condition("Teilnehmer eingecheckt", "blocker", bool(checked),
                        "Noch kein Teilnehmer ist eingecheckt"),
              Condition("Alle erwarteten Teilnehmer eingecheckt", "warning", not missing,
                        f"{len(missing)} erwartete Teilnehmer haben sich nicht eingecheckt"),
              Condition("Alle Startgebühren bezahlt", "warning", not not_paid,
                        f"{len(not_paid)} Teilnehmer haben noch nicht bezahlt")]
    elif target == "scoring":
        with session_scope() as s:
            counts = _count_scores_by_participant(s, tournament_id)
        needed = t.num_targets * t.shots_per_target
        starters = _starters(parts)
        incomplete = [p for p in starters if counts.get(p.id, 0) < needed]
        c += [Condition("Ergebnisse vorhanden", "blocker", bool(counts),
                        "Es wurden noch keine Ergebnisse eingetragen"),
              Condition("Ergebnisse vollständig", "warning", not incomplete,
                        f"{len(incomplete)} Teilnehmer haben unvollständige "
                        "Scheibenergebnisse")]
    elif target == "closed":
        c += [Condition("Ergebnisliste generiert", "warning", t.results_generated_at is not None,
                        "Die Ergebnisliste wurde noch nicht generiert"),
              Condition("Alle Startgebühren bezahlt", "warning", not not_paid,
                        f"{len(not_paid)} Teilnehmer haben noch nicht bezahlt")]
    return c


def transition_phase(tournament_id: int, target_phase: str,
                     force: bool = False) -> TransitionResult:
    """Move to the next phase. Blockers always stop; warnings stop unless force=True."""
    t = get_tournament(tournament_id)
    if target_phase != next_phase(t.phase):
        return TransitionResult(False, errors=[
            f"Von „{PHASE_LABELS.get(t.phase)}“ kann nur in die nächste Phase gewechselt "
            "werden."])
    conds = get_phase_conditions(tournament_id, target_phase)
    errors = [c.message for c in conds if not c.ok and c.severity == "blocker"]
    warnings = [c.message for c in conds if not c.ok and c.severity == "warning"]
    if errors or (warnings and not force):
        return TransitionResult(False, warnings, errors)
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        s.add(PhaseTransitionLog(tournament_id=tournament_id, from_phase=t.phase,
                                 to_phase=target_phase, transitioned_at=datetime.now(),
                                 forced=bool(warnings), warnings_at_transition=warnings or None))
        t.phase = target_phase
        t.phase_changed_at = datetime.now()
        t.status = PHASE_STATUS.get(target_phase, "draft")
    return TransitionResult(True, warnings, [], applied=True)


def transition_phase_backward(tournament_id: int) -> None:
    """Revert one phase backwards. No conditions; logs as forced."""
    t = get_tournament(tournament_id)
    target = prev_phase(t.phase)
    if target is None:
        raise ValidationError("Bereits in der ersten Phase.")
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        s.add(PhaseTransitionLog(
            tournament_id=tournament_id, from_phase=t.phase, to_phase=target,
            transitioned_at=datetime.now(), forced=True,
            warnings_at_transition=["Rückwärts-Phasenwechsel (manuell)"]))
        t.phase = target
        t.phase_changed_at = datetime.now()
        t.status = PHASE_STATUS.get(target, "draft")


def list_phase_log(tournament_id: int) -> list[PhaseTransitionLog]:
    with session_scope() as s:
        return list(s.scalars(select(PhaseTransitionLog)
                              .where(PhaseTransitionLog.tournament_id == tournament_id)
                              .order_by(PhaseTransitionLog.transitioned_at)))


def phase_dates(tournament_id: int) -> dict[str, datetime]:
    """phase key -> date it was entered (from the transition log)."""
    out = {}
    for entry in list_phase_log(tournament_id):
        out[entry.to_phase] = entry.transitioned_at
    t = get_tournament(tournament_id)
    out.setdefault("announcement", t.created_at)
    return out


# ---------------------------------------------------------------- checklist

def get_checklist_state(tournament_id: int) -> dict:
    with session_scope() as s:
        return dict(s.get(Tournament, tournament_id).checklist_state or {})


def set_checklist_item(tournament_id: int, key: str, value) -> None:
    """value: bool for CHECKLIST_ITEMS, text for CHECKLIST_NOTES_KEY."""
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        state = dict(t.checklist_state or {})
        state[key] = value
        t.checklist_state = state      # new dict -> change is detected


# ---------------------------------------------------------------- statistics

@dataclass
class CapacityInfo:
    max: int | None
    active_count: int
    free_slots: int | None
    percentage: float          # 0..100, 0 when unlimited
    is_full: bool


@dataclass
class TournamentStats:
    total: int
    by_status: dict[str, int]
    paid: int
    unpaid: int
    expected: int              # registered + confirmed + checked_in
    capacity: CapacityInfo


@dataclass
class RevenueRow:
    name: str
    count: int
    amount: float
    total: float


@dataclass
class RevenueSummary:
    expected: float
    received: float
    outstanding: float
    rows: list[RevenueRow]


@dataclass
class ClassProgress:
    bow_class: str
    participants: int
    checked_in: int
    complete: int


@dataclass
class CompletionProgress:
    entered: int
    needed: int
    percentage: float
    per_class: list[ClassProgress]
    incomplete_ids: list[int]


def _capacity(t: Tournament) -> CapacityInfo:
    active = sum(is_active_participant(p) for p in t.participants)
    if not t.max_participants:
        return CapacityInfo(None, active, None, 0.0, False)
    pct = min(active / t.max_participants * 100, 100.0)
    return CapacityInfo(t.max_participants, active, max(t.max_participants - active, 0), pct,
                        active >= t.max_participants)


def capacity_info(tournament_id: int) -> CapacityInfo:
    return _capacity(get_tournament(tournament_id))


def get_active_participant_count(tournament_id: int) -> int:
    return capacity_info(tournament_id).active_count


def is_registration_open(tournament_id: int) -> bool:
    t = get_tournament(tournament_id)
    deadline_ok = t.registration_deadline is None or date.today() <= t.registration_deadline
    return phase_index(t.phase) <= phase_index("registration") and deadline_ok \
        and not _capacity(t).is_full


def get_tournament_stats(tournament_id: int) -> TournamentStats:
    t = get_tournament(tournament_id)
    parts = t.participants
    by_status = {st: sum(p.registration_status == st for p in parts)
                 for st in ("registered", "confirmed", "checked_in", "dns", "dnf", "dsq",
                            "withdrawn")}
    active = [p for p in parts if is_active_participant(p)]
    paid = sum(p.payment_status == "paid" for p in active)
    return TournamentStats(len(parts), by_status, paid, len(active) - paid,
                           sum(p.registration_status in EXPECTED_REGISTRATION for p in parts),
                           _capacity(t))


def get_revenue_summary(tournament_id: int) -> RevenueSummary:
    t = get_tournament(tournament_id)
    counted = [p for p in t.participants if p.registration_status in REVENUE_REGISTRATION]
    expected = sum(p.entry_fee.amount for p in counted if p.entry_fee)
    received = sum((p.fee_amount_paid if p.fee_amount_paid is not None
                    else (p.entry_fee.amount if p.entry_fee else 0))
                   for p in t.participants if p.payment_status == "paid")
    rows = []
    for fee in t.fees:
        n = sum(p.entry_fee_id == fee.id for p in counted)
        rows.append(RevenueRow(fee.name, n, fee.amount, n * fee.amount))
    return RevenueSummary(round(expected, 2), round(received, 2),
                          round(expected - received, 2), rows)


def _starters(parts) -> list:
    """Participants expected on the course: checked in, or (if nobody is checked in yet,
    e.g. tournaments from before the lifecycle) everybody still active."""
    checked = [p for p in parts if p.registration_status == "checked_in"]
    return checked or [p for p in parts if p.registration_status in EXPECTED_REGISTRATION]


def get_completion_progress(tournament_id: int) -> CompletionProgress:
    t = get_tournament(tournament_id)
    with session_scope() as s:
        counts = _count_scores_by_participant(s, tournament_id)
    per_target = t.num_targets * t.shots_per_target
    starters = _starters(t.participants)
    needed = len(starters) * per_target
    entered = sum(min(counts.get(p.id, 0), per_target) for p in starters)
    per_class = []
    for bc in t.bow_classes:
        in_class = [p for p in t.participants if p.bow_class_id == bc.id
                    and is_active_participant(p)]
        if not in_class:
            continue
        cls_starters = [p for p in starters if p.bow_class_id == bc.id]
        per_class.append(ClassProgress(
            bc.name, len(in_class), sum(p.registration_status == "checked_in" for p in in_class),
            sum(counts.get(p.id, 0) >= per_target for p in cls_starters)))
    incomplete = [p.id for p in starters if counts.get(p.id, 0) < per_target]
    return CompletionProgress(entered, needed, entered / needed * 100 if needed else 0.0,
                              per_class, incomplete)


@dataclass
class StatusCheck:
    label: str
    ok: bool
    detail: str = ""


def get_status_checks(tournament_id: int) -> dict[str, StatusCheck]:
    """Automatic checks shown as traffic lights in the guide (spec 4.2)."""
    t = get_tournament(tournament_id)
    parts = [p for p in t.participants if is_active_participant(p)]
    registered = sum(p.registration_status == "registered" for p in parts)
    unpaid = sum(p.payment_status != "paid" for p in parts)
    checked = sum(p.registration_status == "checked_in" for p in parts)
    progress = get_completion_progress(tournament_id)
    return {
        "contact": StatusCheck("Kontaktdaten", bool(t.contact_name and t.contact_email),
                               "Kontaktname und E-Mail hinterlegen"),
        "bank": StatusCheck("Bankverbindung", bool(t.bank_iban), "IBAN hinterlegen"),
        "fees": StatusCheck("Startgebühren", bool(t.fees), "Mindestens eine Gebühr anlegen"),
        "announced": StatusCheck("Ausschreibung generiert", t.announced_at is not None,
                                 "Ausschreibungs-PDF noch nie erstellt"),
        "announcement_current": StatusCheck(
            "Ausschreibung aktuell", t.announced_at is not None and not announcement_outdated(t),
            "Turnierdaten wurden nach der letzten Ausschreibung geändert"
            if t.announced_at else "Noch keine Ausschreibung erstellt"),
        "participants": StatusCheck("Teilnehmer vorhanden", bool(parts),
                                    "Noch keine Anmeldungen erfasst"),
        "all_confirmed": StatusCheck("Alle bestätigt", bool(parts) and registered == 0,
                                     f"{registered} Anmeldungen noch nicht bestätigt"),
        "all_paid": StatusCheck("Alle bezahlt", bool(parts) and unpaid == 0,
                                f"{unpaid} Zahlungen ausstehend"),
        "checkin_started": StatusCheck("Einschreibung gestartet", checked > 0,
                                       "Noch niemand eingecheckt"),
        "results_complete": StatusCheck(
            "Ergebnisse vollständig", progress.needed > 0 and not progress.incomplete_ids,
            f"{len(progress.incomplete_ids)} Teilnehmer mit unvollständigen Ergebnissen"),
        "results_generated": StatusCheck("Ergebnisliste generiert",
                                         t.results_generated_at is not None,
                                         "Ergebnisliste noch nicht erstellt"),
    }


# ---------------------------------------------------------------- participants

def _check_editable(t: Tournament) -> None:
    if t.status == "closed":
        raise ValidationError("Das Turnier ist abgeschlossen.")


def _check_capacity(t: Tournament, adding: int) -> None:
    cap = _capacity(t)
    if cap.max is not None and cap.active_count + adding > cap.max:
        raise ValidationError(f"Maximale Teilnehmerzahl erreicht ({cap.active_count}/{cap.max}). "
                              f"Nur noch {cap.free_slots} Plätze verfügbar.")


def _pick_class(t: Tournament, archer: Archer, wanted: int | None) -> int | None:
    ids = [bc.id for bc in t.bow_classes]
    for cid in (wanted, archer.default_bow_class_id):
        if cid in ids:
            return cid
    return ids[0] if ids else None


def _add(s, t: Tournament, archer: Archer, bow_class_id: int | None = None,
         start_number: int | None = None, start_group: str | None = None,
         **extra) -> TournamentParticipant | None:
    if any(p.archer_id == archer.id for p in t.participants):
        return None
    _check_capacity(t, 1)
    groups = split_groups(t.start_groups)
    next_no = max((p.start_number or 0 for p in t.participants), default=0) + 1
    if start_group is None and groups:
        start_group = groups[len(t.participants) % len(groups)]
    p = TournamentParticipant(
        archer=archer, bow_class_id=_pick_class(t, archer, bow_class_id),
        start_number=start_number or next_no, start_group=start_group,
        registration_date=date.today(), **extra)
    t.participants.append(p)
    return p


def add_participants(tournament_id: int, archer_ids: list[int]) -> int:
    """Add archers from master data. Returns number added (already present are skipped)."""
    added = 0
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        new = [a for a in archer_ids if all(p.archer_id != a for p in t.participants)]
        _check_capacity(t, len(new))
        for aid in new:
            added += _add(s, t, s.get(Archer, aid)) is not None
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
        for p in parts:
            p.start_number = None
        s.flush()
        for i, p in enumerate(parts):
            p.start_number = i + 1
            if groups:
                p.start_group = groups[i % len(groups)]


def _resolve_import(s, t: Tournament, records: list[dict], strategy: str):
    """Yields (record, archer or None, bow_class_id, start_number, start_group)."""
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
        cid = classes.get(str(bc_name).strip().lower()) if bc_name else None
        yield rec, archer, cid, start_number, start_group


def import_capacity_error(tournament_id: int, records: list[dict], strategy: str) -> str | None:
    """Validation for the import dialog: would the import exceed max_participants?"""
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        cap = _capacity(t)
        if cap.max is None:
            return None
        present = {p.archer_id for p in t.participants}
        adding = sum(1 for _r, archer, *_ in _resolve_import(s, t, records, strategy)
                     if archer is None or archer.id not in present)
        s.rollback()
    if adding > (cap.free_slots or 0):
        return (f"Nur noch {cap.free_slots} Plätze verfügbar, Import würde {adding} "
                "Teilnehmer hinzufügen")
    return None


def import_participants(tournament_id: int, records: list[dict], strategy: str) -> dict:
    """Records hold archer fields plus bow_class, start_number, start_group.

    strategy applies to the archer master data: 'skip' | 'update' | 'new'.
    """
    error = import_capacity_error(tournament_id, records, strategy)
    if error:
        raise ValidationError(error)
    result = {"created": 0, "updated": 0, "skipped": 0, "added": 0}
    with session_scope() as s:
        t = s.get(Tournament, tournament_id)
        _check_editable(t)
        for rec, archer, cid, start_number, start_group in list(
                _resolve_import(s, t, records, strategy)):
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
            result["added"] += _add(s, t, archer, cid, start_number, start_group) is not None
    return result

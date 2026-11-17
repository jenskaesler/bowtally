# -*- coding: utf-8 -*-
"""Member master data, helper history and import."""
import re
import shutil
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import select

from bowtally import config
from bowtally.database.engine import session_scope
from bowtally.database.models import Member, MemberFile, MemberHelperHistory, TournamentHelper
from bowtally.services import ValidationError

FILES_DIR = "member_files"      # below the app data folder: member_files/<member id>/<file>

TEXT_FIELDS = ("member_number", "first_name", "last_name", "street", "postal_code", "city",
               "phone", "email", "notes", "account_holder", "iban", "bic", "bank_name",
               "sepa_mandate_ref")
DATE_FIELDS = ("member_since", "cancelled_on", "birthday", "consent_date", "sepa_mandate_date")
BOOL_FIELDS = ("info_by_mail", "is_tournament_helper", "active", "consent_given",
               "sepa_direct_debit")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_iban(iban: str) -> bool:
    """Empty is valid (optional field); otherwise ISO 13616 check digits (mod 97)."""
    iban = (iban or "").replace(" ", "").upper()
    if not iban:
        return True
    if len(iban) < 15 or not iban.isalnum():
        return False
    moved = iban[4:] + iban[:4]
    return int("".join(str(int(c, 36)) for c in moved)) % 97 == 1


def member_status(m: Member) -> str:
    return "Gekündigt" if m.cancelled_on and m.cancelled_on <= date.today() else "Aktiv"


def _next_number(s) -> str:
    numbers = [int(n) for n in s.scalars(select(Member.member_number)) if n.isdigit()]
    return str(max(numbers, default=0) + 1)


def next_member_number() -> str:
    with session_scope() as s:
        return _next_number(s)


def list_members(include_inactive: bool = True, only_helpers: bool = False) -> list[Member]:
    with session_scope() as s:
        q = select(Member).order_by(Member.last_name, Member.first_name)
        if not include_inactive:
            q = q.where(Member.active == True)  # noqa: E712
        if only_helpers:
            q = q.where(Member.is_tournament_helper == True)  # noqa: E712
        return s.scalars(q).all()


def get_member(member_id: int) -> Member:
    with session_scope() as s:
        return s.get(Member, member_id)


def _validate(s, data: dict, member_id: int | None = None) -> None:
    if not (data.get("first_name") or "").strip():
        raise ValidationError("Vorname ist ein Pflichtfeld")
    if not (data.get("last_name") or "").strip():
        raise ValidationError("Nachname ist ein Pflichtfeld")
    number = (data.get("member_number") or "").strip()
    if not number:
        raise ValidationError("Mitgliedsnummer ist ein Pflichtfeld")
    other = s.scalars(select(Member.id).where(Member.member_number == number)).first()
    if other is not None and other != member_id:
        raise ValidationError(f"Mitgliedsnummer {number} ist bereits vergeben")
    email = (data.get("email") or "").strip()
    if email and not _EMAIL_RE.match(email):
        raise ValidationError("Bitte eine gültige E-Mail-Adresse eingeben")
    if not is_valid_iban(data.get("iban") or ""):
        raise ValidationError("Die IBAN ist ungültig")


def _apply(m: Member, data: dict) -> None:
    """Only keys present in `data` are written, so partial updates keep other fields."""
    for k in TEXT_FIELDS:
        if k in data:
            value = (data[k] or "").strip() or None
            if k == "iban" and value:
                value = value.replace(" ", "").upper()
            setattr(m, k, value)
    for k in DATE_FIELDS:
        if k in data:
            setattr(m, k, data[k])
    for k in BOOL_FIELDS:
        if k in data:
            setattr(m, k, bool(data[k]))


def create_member(data: dict) -> Member:
    with session_scope() as s:
        _validate(s, data)
        m = Member()
        _apply(m, data)
        s.add(m)
        s.flush()
        return m


def update_member(member_id: int, data: dict) -> Member:
    with session_scope() as s:
        _validate(s, data, member_id)
        m = s.get(Member, member_id)
        _apply(m, data)
        s.flush()
        return m


def set_active(member_id: int, active: bool) -> None:
    with session_scope() as s:
        s.get(Member, member_id).active = active


def delete_member(member_id: int) -> None:
    with session_scope() as s:
        if s.scalars(select(TournamentHelper.id).where(
                TournamentHelper.member_id == member_id)).first() is not None:
            raise ValidationError("Das Mitglied war bereits bei Turnieren eingesetzt und kann "
                                  "nicht gelöscht werden. Bitte stattdessen als inaktiv markieren.")
        s.delete(s.get(Member, member_id))
    shutil.rmtree(config.APP_DATA_DIR / FILES_DIR / str(member_id), ignore_errors=True)


# ---------------------------------------------------------------- files
def list_member_files(member_id: int) -> list[MemberFile]:
    with session_scope() as s:
        return s.scalars(select(MemberFile).where(MemberFile.member_id == member_id)
                         .order_by(MemberFile.id)).all()


def member_file_path(stored: MemberFile) -> Path:
    return config.APP_DATA_DIR / stored.stored_path


def add_member_file(member_id: int, source) -> MemberFile:
    """Copy a file into the app data folder and attach it to the member."""
    source = Path(source)
    if not source.is_file():
        raise ValidationError(f"Datei '{source.name}' wurde nicht gefunden.")
    safe_name = re.sub(r"[^\w.\- ]+", "_", source.name).strip() or "datei"
    stored_path = f"{FILES_DIR}/{member_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    with session_scope() as s:
        if s.get(Member, member_id) is None:
            raise ValidationError("Mitglied nicht gefunden.")
        target = config.APP_DATA_DIR / stored_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        stored = MemberFile(member_id=member_id, filename=source.name, stored_path=stored_path,
                            size_bytes=target.stat().st_size)
        s.add(stored)
        s.flush()
        return stored


def remove_member_file(file_id: int) -> None:
    with session_scope() as s:
        stored = s.get(MemberFile, file_id)
        path = member_file_path(stored)
        s.delete(stored)
    path.unlink(missing_ok=True)


# ---------------------------------------------------------------- helper history
def list_history(member_id: int) -> list[MemberHelperHistory]:
    with session_scope() as s:
        return s.scalars(select(MemberHelperHistory)
                         .where(MemberHelperHistory.member_id == member_id)
                         .order_by(MemberHelperHistory.date.desc())).all()


def _apply_history(h: MemberHelperHistory, data: dict) -> None:
    name = (data.get("tournament_name") or "").strip()
    if not name:
        raise ValidationError("Turnier ist ein Pflichtfeld")
    h.tournament_name = name
    h.date = data.get("date")
    h.role = (data.get("role") or "").strip() or None
    h.hours = data.get("hours")


def add_history(member_id: int, data: dict) -> MemberHelperHistory:
    with session_scope() as s:
        h = MemberHelperHistory(member_id=member_id)
        _apply_history(h, data)
        s.add(h)
        s.flush()
        return h


def _manual_entry(s, history_id: int) -> MemberHelperHistory:
    h = s.get(MemberHelperHistory, history_id)
    if h.tournament_id is not None:
        raise ValidationError("Automatisch erfasste Einsätze können nicht geändert werden")
    return h


def update_history(history_id: int, data: dict) -> None:
    with session_scope() as s:
        _apply_history(_manual_entry(s, history_id), data)


def delete_history(history_id: int) -> None:
    with session_scope() as s:
        s.delete(_manual_entry(s, history_id))


# ---------------------------------------------------------------- data request (Art. 15 DSGVO)
def mask_iban(iban: str) -> str:
    """All characters except the last four become '*', grouped in fours from the right."""
    compact = "".join((iban or "").split()).upper()
    masked = "*" * max(len(compact) - 4, 0) + compact[-4:]
    groups = [masked[max(end - 4, 0):end] for end in range(len(masked), 0, -4)]
    return " ".join(reversed(groups))


def _yes_no(value: bool) -> str:
    return "Ja" if value else "Nein"


def data_summary(member_id: int) -> str:
    """Plain-text overview of everything stored about a member; the IBAN is masked."""
    with session_scope() as s:
        m = s.get(Member, member_id)
        history = list(m.history)
        file_names = [f.filename for f in m.files]
    fmt = lambda d: f"{d:%d.%m.%Y}" if d else ""  # noqa: E731
    address = ", ".join(filter(None, [m.street, " ".join(filter(None, [m.postal_code, m.city]))]))
    consent = _yes_no(m.consent_given) + (f" (seit {fmt(m.consent_date)})" if m.consent_date else "")
    sections = [
        ("Stammdaten", [
            ("Mitgliedsnummer", m.member_number), ("Name", f"{m.first_name} {m.last_name}"),
            ("Anschrift", address), ("Telefon", m.phone), ("E-Mail", m.email),
            ("Geburtstag", fmt(m.birthday)), ("Mitglied seit", fmt(m.member_since)),
            ("Gekündigt zum", fmt(m.cancelled_on)), ("Status", member_status(m)),
            ("Notizen", m.notes), ("Infos per E-Mail", _yes_no(m.info_by_mail)),
            ("Turnierhelfer", _yes_no(m.is_tournament_helper)),
            ("Einwilligung Datenverarbeitung", consent)]),
        ("Bankverbindung", [
            ("Kontoinhaber", m.account_holder), ("IBAN", mask_iban(m.iban)), ("BIC", m.bic),
            ("Name der Bank", m.bank_name),
            ("Einzugsermächtigung", _yes_no(m.sepa_direct_debit) if m.iban else ""),
            ("SEPA-Mandatsreferenz", m.sepa_mandate_ref),
            ("Datum der Mandatserteilung", fmt(m.sepa_mandate_date))]),
    ]
    blocks = [f"{title}\n" + "\n".join(f"{label}: {value}" for label, value in rows if value)
              for title, rows in sections]
    if history:
        lines = [f"- {fmt(h.date) or 'ohne Datum'}: {h.tournament_name}"
                 + (f", {h.role}" if h.role else "")
                 + (f", {h.hours:.1f}".replace(".", ",") + " Std." if h.hours is not None else "")
                 for h in history]
        blocks.append("Helferhistorie\n" + "\n".join(lines))
    if file_names:
        blocks.append("Dateien\n" + "\n".join(f"- {name}" for name in file_names))
    return "\n\n".join(blocks)


# ---------------------------------------------------------------- import
def import_members(records: list[dict], strategy: str) -> dict:
    created = updated = skipped = 0
    with session_scope() as s:
        for r in records:
            number = (r.get("member_number") or "").strip()
            first = (r.get("first_name") or "").strip()
            last = (r.get("last_name") or "").strip()
            existing = number and s.scalars(
                select(Member).where(Member.member_number == number)).first()
            if not existing:
                existing = s.scalars(select(Member).where(
                    Member.first_name == first, Member.last_name == last)).first()
            if existing:
                if strategy == "skip":
                    skipped += 1
                    continue
                _apply(existing, {k: v for k, v in r.items() if k != "member_number"})
                updated += 1
            else:
                m = Member(member_number=number or _next_number(s), active=True)
                _apply(m, {k: v for k, v in r.items() if k != "member_number"})
                s.add(m)
                s.flush()
                created += 1
    return {"created": created, "updated": updated, "skipped": skipped}

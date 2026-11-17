# -*- coding: utf-8 -*-
"""Logbuch: aggregates log entries from multiple sources."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select

from bowtally.database.engine import session_scope
from bowtally.database.models import (Archer, BackupLog, PhaseTransitionLog, Score,
                                       Tournament, TournamentParticipant)

PAGE_SIZE = 100

TARGET_LABELS = {"local": "Lokal", "network": "Netzwerk", "nextcloud": "Nextcloud"}


def _phase_labels():
    from bowtally.services.tournament_service import PHASE_LABELS
    return PHASE_LABELS


@dataclass
class LogEntry:
    log_type: str
    created_at: datetime | None
    description: str
    context: str
    detail: dict = field(default_factory=dict)


def _collect_backup(s) -> list[LogEntry]:
    rows = s.execute(select(BackupLog).order_by(BackupLog.created_at.desc())).scalars().all()
    result = []
    for r in rows:
        target_lbl = TARGET_LABELS.get(r.target or "", r.target or "")
        if r.success:
            ctx = f"{r.file_name or ''} → {target_lbl}".strip(" →")
        else:
            ctx = f"{target_lbl}: {r.error_message or 'Unbekannter Fehler'}"
        result.append(LogEntry(
            log_type="backup",
            created_at=r.created_at,
            description="Backup erstellt" if r.success else "Backup fehlgeschlagen",
            context=ctx,
        ))
    return result


def _collect_phases(s, tournament_id=None) -> list[LogEntry]:
    stmt = select(PhaseTransitionLog, Tournament).join(
        Tournament, Tournament.id == PhaseTransitionLog.tournament_id
    ).order_by(PhaseTransitionLog.transitioned_at.desc())
    if tournament_id:
        stmt = stmt.where(PhaseTransitionLog.tournament_id == tournament_id)
    rows = s.execute(stmt).all()
    labels = _phase_labels()
    result = []
    for log, t in rows:
        from_lbl = labels.get(log.from_phase or "", log.from_phase or "–")
        to_lbl = labels.get(log.to_phase or "", log.to_phase or "–")
        forced = " (erzwungen)" if log.forced else ""
        result.append(LogEntry(
            log_type="phase",
            created_at=log.transitioned_at,
            description=f"{from_lbl} → {to_lbl}{forced}",
            context=t.name,
        ))
    return result


def _collect_scores(s, tournament_id=None) -> list[LogEntry]:
    stmt = (
        select(Score, TournamentParticipant, Archer, Tournament)
        .join(TournamentParticipant, TournamentParticipant.id == Score.participant_id)
        .join(Archer, Archer.id == TournamentParticipant.archer_id)
        .join(Tournament, Tournament.id == TournamentParticipant.tournament_id)
        .order_by(Score.entered_at.desc())
        .limit(500)
    )
    if tournament_id:
        stmt = stmt.where(TournamentParticipant.tournament_id == tournament_id)
    rows = s.execute(stmt).all()
    result = []
    for score, _part, archer, t in rows:
        zone = f" ({score.zone_hit})" if score.zone_hit else ""
        desc = f"Scheibe {score.target_number}: {score.points} Pt.{zone}"
        result.append(LogEntry(
            log_type="score",
            created_at=score.entered_at,
            description=desc,
            context=f"{archer.full_name} – {t.name}",
        ))
    return result


def _collect_checkins(s, tournament_id=None) -> list[LogEntry]:
    stmt = (
        select(TournamentParticipant, Archer, Tournament)
        .join(Archer, Archer.id == TournamentParticipant.archer_id)
        .join(Tournament, Tournament.id == TournamentParticipant.tournament_id)
        .where(TournamentParticipant.checkin_time.isnot(None))
        .order_by(TournamentParticipant.checkin_time.desc())
    )
    if tournament_id:
        stmt = stmt.where(TournamentParticipant.tournament_id == tournament_id)
    rows = s.execute(stmt).all()
    result = []
    for part, archer, t in rows:
        result.append(LogEntry(
            log_type="checkin",
            created_at=part.checkin_time,
            description="Eingecheckt",
            context=f"{archer.full_name} – {t.name}",
        ))
    return result


def list_entries(
    tournament_id: int | None = None,
    log_types: set | None = None,
    period_days: int | None = None,
    search: str = "",
    offset: int = 0,
    limit: int = PAGE_SIZE,
) -> tuple[list[LogEntry], int]:
    """Return (entries_page, total_count). Entries sorted newest-first."""
    with session_scope() as s:
        all_entries: list[LogEntry] = []
        all_entries.extend(_collect_backup(s))
        all_entries.extend(_collect_phases(s, tournament_id))
        all_entries.extend(_collect_scores(s, tournament_id))
        all_entries.extend(_collect_checkins(s, tournament_id))

    if log_types:
        all_entries = [e for e in all_entries if e.log_type in log_types]
    if period_days is not None:
        cutoff = datetime.now() - timedelta(days=period_days)
        all_entries = [e for e in all_entries if e.created_at and e.created_at >= cutoff]
    if search:
        needle = search.strip().lower()
        all_entries = [e for e in all_entries
                       if needle in e.description.lower() or needle in e.context.lower()]

    all_entries.sort(key=lambda e: e.created_at or datetime.min, reverse=True)
    total = len(all_entries)
    return all_entries[offset:offset + limit], total


def list_tournaments_with_log() -> list[tuple[int, str]]:
    """Return [(id, name)] for all tournaments."""
    with session_scope() as s:
        rows = s.execute(
            select(Tournament.id, Tournament.name).order_by(Tournament.date.desc())
        ).all()
    return [(r.id, r.name) for r in rows]

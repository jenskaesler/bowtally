# -*- coding: utf-8 -*-
"""ORM models for all BowTally tables."""
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, CheckConstraint, Column, Date, DateTime, Float,
                        ForeignKey, Integer, String, Table, Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now():
    return datetime.now()


# ---------------------------------------------------------------- configuration

class AppSetting(Base):
    __tablename__ = "app_settings"
    __table_args__ = (
        CheckConstraint("value_type IN ('string', 'integer', 'boolean', 'color', 'path')",
                        name="ck_app_settings_value_type"),
    )

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(Text, default="string")
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now, onupdate=_now)


class ClubProfile(Base):
    __tablename__ = "club_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    club_name: Mapped[str | None] = mapped_column(Text)
    street: Mapped[str | None] = mapped_column(Text)
    zip_code: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text, default="Deutschland")
    phone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    logo_path: Mapped[str | None] = mapped_column(Text)
    federation: Mapped[str | None] = mapped_column(Text)
    club_number: Mapped[str | None] = mapped_column(Text)
    bank_account_holder: Mapped[str | None] = mapped_column(Text)
    bank_iban: Mapped[str | None] = mapped_column(Text)
    bank_bic: Mapped[str | None] = mapped_column(Text)
    bank_reference_template: Mapped[str | None] = mapped_column(Text)
    course_description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # Vereinsvorstand (first/last name per role)
    first_board_fname: Mapped[str | None] = mapped_column(Text)
    first_board_lname: Mapped[str | None] = mapped_column(Text)
    second_board_fname: Mapped[str | None] = mapped_column(Text)
    second_board_lname: Mapped[str | None] = mapped_column(Text)
    treasurer_fname: Mapped[str | None] = mapped_column(Text)
    treasurer_lname: Mapped[str | None] = mapped_column(Text)
    sports_dir_fname: Mapped[str | None] = mapped_column(Text)
    sports_dir_lname: Mapped[str | None] = mapped_column(Text)
    bow_ref_fname: Mapped[str | None] = mapped_column(Text)
    bow_ref_lname: Mapped[str | None] = mapped_column(Text)
    # phone + email per board role
    first_board_phone: Mapped[str | None] = mapped_column(Text)
    first_board_email: Mapped[str | None] = mapped_column(Text)
    second_board_phone: Mapped[str | None] = mapped_column(Text)
    second_board_email: Mapped[str | None] = mapped_column(Text)
    treasurer_phone: Mapped[str | None] = mapped_column(Text)
    treasurer_email: Mapped[str | None] = mapped_column(Text)
    sports_dir_phone: Mapped[str | None] = mapped_column(Text)
    sports_dir_email: Mapped[str | None] = mapped_column(Text)
    bow_ref_phone: Mapped[str | None] = mapped_column(Text)
    bow_ref_email: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now, onupdate=_now)


# ---------------------------------------------------------------- master data

class ScoringRule(Base):
    __tablename__ = "scoring_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    ring_values: Mapped[list] = mapped_column(JSON, default=list)
    max_shots_per_target: Mapped[int] = mapped_column(Integer, default=1)
    allow_retry_shot: Mapped[bool] = mapped_column(Boolean, default=False)
    rules_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)


class BowClass(Base):
    __tablename__ = "bow_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(Text)
    age_group: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Archer(Base):
    __tablename__ = "archers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date)
    club: Mapped[str | None] = mapped_column(Text)
    member_number: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    default_bow_class_id: Mapped[int | None] = mapped_column(ForeignKey("bow_classes.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)

    default_bow_class: Mapped["BowClass | None"] = relationship()

    @property
    def full_name(self) -> str:
        return f"{self.last_name}, {self.first_name}"


# ---------------------------------------------------------------- tournaments

class TournamentPhase(Base):
    """Reference data (seeded by migration 0003, not user editable)."""
    __tablename__ = "tournament_phases"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)


tournament_bow_classes = Table(
    "tournament_bow_classes", Base.metadata,
    Column("tournament_id", ForeignKey("tournaments.id", ondelete="CASCADE"), primary_key=True),
    Column("bow_class_id", ForeignKey("bow_classes.id"), primary_key=True),
)


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'closed')", name="ck_tournaments_status"),
        CheckConstraint("scoring_mode IN ('per_target', 'per_round', 'total_only')",
                        name="ck_tournaments_scoring_mode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    organizer: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="draft")
    num_targets: Mapped[int] = mapped_column(Integer, nullable=False)
    shots_per_target: Mapped[int] = mapped_column(Integer, default=1)
    scoring_rule_id: Mapped[int | None] = mapped_column(ForeignKey("scoring_rules.id"))
    # Comma separated start group names, e.g. "A, B, C" (set in the wizard)
    start_groups: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)

    # lifecycle
    phase: Mapped[str] = mapped_column(ForeignKey("tournament_phases.key"),
                                       default="announcement")
    phase_changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    # organisation / announcement
    # string annotation: the column 'date' above shadows the type name in the class body
    registration_deadline: Mapped["date | None"] = mapped_column(Date)
    max_participants: Mapped[int | None] = mapped_column(Integer)
    checkin_start_time: Mapped[str | None] = mapped_column(Text)
    shooting_start_time: Mapped[str | None] = mapped_column(Text)
    practice_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    practice_location: Mapped[str | None] = mapped_column(Text)
    bank_account_holder: Mapped[str | None] = mapped_column(Text)
    bank_iban: Mapped[str | None] = mapped_column(Text)
    bank_bic: Mapped[str | None] = mapped_column(Text)
    bank_reference_template: Mapped[str | None] = mapped_column(Text)
    contact_name: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    legal_notes: Mapped[str | None] = mapped_column(Text)
    additional_info: Mapped[str | None] = mapped_column(Text)
    checklist_state: Mapped[dict | None] = mapped_column(JSON, default=dict)
    announced_at: Mapped[datetime | None] = mapped_column(DateTime)      # first PDF
    # Not in the original spec, needed for "announcement outdated" / "results generated"
    announcement_generated_at: Mapped[datetime | None] = mapped_column(DateTime)   # last PDF
    content_changed_at: Mapped[datetime | None] = mapped_column(DateTime)
    results_generated_at: Mapped[datetime | None] = mapped_column(DateTime)

    num_rounds: Mapped[int] = mapped_column(Integer, default=1)
    scoring_mode: Mapped[str] = mapped_column(Text, default="per_target")

    scoring_rule: Mapped["ScoringRule | None"] = relationship()
    phase_info: Mapped["TournamentPhase"] = relationship()
    fees: Mapped[list["EntryFee"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan",
        order_by="EntryFee.sort_order, EntryFee.id")
    bow_classes: Mapped[list["BowClass"]] = relationship(
        secondary=tournament_bow_classes, order_by="BowClass.sort_order")
    participants: Mapped[list["TournamentParticipant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan")
    rounds: Mapped[list["TournamentRound"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan",
        order_by="TournamentRound.sort_order, TournamentRound.round_number")


REGISTRATION_STATUSES = ("registered", "confirmed", "checked_in", "dns", "dnf", "dsq",
                         "withdrawn", "waitlisted")
PAYMENT_STATUSES = ("unpaid", "pending", "paid")


class EntryFee(Base):
    __tablename__ = "entry_fees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # NULL = template, copied into every new tournament
    tournament_id: Mapped[int | None] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    tournament: Mapped["Tournament | None"] = relationship(back_populates="fees")


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"
    __table_args__ = (
        CheckConstraint("registration_status IN ('registered', 'confirmed', 'checked_in', "
                        "'dns', 'dnf', 'dsq', 'withdrawn', 'waitlisted')",
                        name="ck_participants_registration"),
        CheckConstraint("payment_status IN ('unpaid', 'pending', 'paid')",
                        name="ck_participants_payment"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    archer_id: Mapped[int] = mapped_column(ForeignKey("archers.id"))
    bow_class_id: Mapped[int | None] = mapped_column(ForeignKey("bow_classes.id"))
    start_number: Mapped[int | None] = mapped_column(Integer)
    start_group: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[str | None] = mapped_column(Text)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)
    registration_status: Mapped[str] = mapped_column(Text, default="registered")
    payment_status: Mapped[str] = mapped_column(Text, default="unpaid")
    entry_fee_id: Mapped[int | None] = mapped_column(ForeignKey("entry_fees.id"))
    fee_amount_paid: Mapped[float | None] = mapped_column(Float)
    payment_date: Mapped[date | None] = mapped_column(Date)
    payment_notes: Mapped[str | None] = mapped_column(Text)
    registration_date: Mapped[date | None] = mapped_column(Date, default=date.today)
    confirmation_date: Mapped[date | None] = mapped_column(Date)
    checkin_time: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)

    tournament: Mapped["Tournament"] = relationship(back_populates="participants")
    archer: Mapped["Archer"] = relationship()
    bow_class: Mapped["BowClass | None"] = relationship()
    entry_fee: Mapped["EntryFee | None"] = relationship()
    scores: Mapped[list["Score"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan")


class TournamentRound(Base):
    __tablename__ = "tournament_rounds"
    __table_args__ = (
        CheckConstraint("distance_type IN ('known', 'unknown') OR distance_type IS NULL",
                        name="ck_rounds_distance_type"),
        UniqueConstraint("tournament_id", "round_number", name="uq_rounds_tournament_round"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    num_targets: Mapped[int | None] = mapped_column(Integer)
    scoring_rule_id: Mapped[int | None] = mapped_column(ForeignKey("scoring_rules.id"))
    distance_type: Mapped[str | None] = mapped_column(Text)
    shots_per_target: Mapped[int | None] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    tournament: Mapped["Tournament"] = relationship(back_populates="rounds")
    scoring_rule: Mapped["ScoringRule | None"] = relationship()


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("participant_id", "round_number", "target_number",
                                       "shot_number",
                                       name="uq_scores_participant_round_target_shot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="CASCADE"))
    round_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_number: Mapped[int] = mapped_column(Integer, nullable=False)
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    zone_hit: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    entered_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now, onupdate=_now)

    participant: Mapped["TournamentParticipant"] = relationship(back_populates="scores")


class Helper(Base):
    __tablename__ = "helpers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def full_name(self) -> str:
        return f"{self.last_name}, {self.first_name}"


class TournamentHelper(Base):
    __tablename__ = "tournament_helpers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    helper_id: Mapped[int] = mapped_column(ForeignKey("helpers.id", ondelete="CASCADE"))
    task: Mapped[str | None] = mapped_column(Text)
    time_from: Mapped[str | None] = mapped_column(Text)
    time_to: Mapped[str | None] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    helper: Mapped["Helper"] = relationship()


class PhaseTransitionLog(Base):
    __tablename__ = "phase_transition_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    from_phase: Mapped[str | None] = mapped_column(Text)
    to_phase: Mapped[str] = mapped_column(Text)
    transitioned_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    forced: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings_at_transition: Mapped[list | None] = mapped_column(JSON)

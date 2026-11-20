# -*- coding: utf-8 -*-
"""ORM models for all BowTally tables."""
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, CheckConstraint, Column, Date, DateTime, Float,
                        ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint)
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
    tracked_specials: Mapped[list] = mapped_column(JSON, default=list)
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
    pass_number: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    default_bow_class_id: Mapped[int | None] = mapped_column(ForeignKey("bow_classes.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_new_tournament: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_results: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)

    default_bow_class: Mapped["BowClass | None"] = relationship()
    files: Mapped[list["ArcherFile"]] = relationship(cascade="all, delete-orphan",
                                                     order_by="ArcherFile.id")

    @property
    def full_name(self) -> str:
        return f"{self.last_name}, {self.first_name}"


class ArcherFile(Base):
    """File attached to an archer; stored in the app data folder, `stored_path` is relative to it."""
    __tablename__ = "archer_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    archer_id: Mapped[int] = mapped_column(ForeignKey("archers.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    added_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)


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
    use_draw: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)          # Hinweise zum Parcours (Ausschreibung)
    internal_notes: Mapped[str | None] = mapped_column(Text)  # Tab "Notizen", nie in der Ausschreibung
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
    prizes: Mapped[list["Prize"]] = relationship(
        cascade="all, delete-orphan", order_by="Prize.sort_order, Prize.rank, Prize.id")
    course_targets: Mapped[list["CourseTarget"]] = relationship(
        cascade="all, delete-orphan", order_by="CourseTarget.sort_order, CourseTarget.id")
    schedule_groups: Mapped[list["ScheduleGroup"]] = relationship(
        cascade="all, delete-orphan", order_by="ScheduleGroup.id")
    course_items: Mapped[list["CourseItem"]] = relationship(
        cascade="all, delete-orphan", order_by="CourseItem.sort_order, CourseItem.id")


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
        # an archer (database id) takes part in a tournament at most once
        Index("uq_participants_tournament_archer", "tournament_id", "archer_id", unique=True),
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
    shoot_off_points: Mapped[int | None] = mapped_column(Integer)    # result of a shoot-off, higher wins

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
    specials: Mapped[dict] = mapped_column(JSON, default=dict)
    entered_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now, onupdate=_now)

    participant: Mapped["TournamentParticipant"] = relationship(back_populates="scores")


class Member(Base):
    """Club member master data (formerly `helpers`); also the source of tournament helpers."""
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    street: Mapped[str | None] = mapped_column(Text)
    postal_code: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    member_since: Mapped[date | None] = mapped_column(Date)
    cancelled_on: Mapped[date | None] = mapped_column(Date)
    birthday: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    info_by_mail: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    is_tournament_helper: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    consent_date: Mapped[date | None] = mapped_column(Date)
    # bank data: never part of general exports, only of the password-protected backup
    account_holder: Mapped[str | None] = mapped_column(Text)
    iban: Mapped[str | None] = mapped_column(Text)
    bic: Mapped[str | None] = mapped_column(Text)
    bank_name: Mapped[str | None] = mapped_column(Text)
    sepa_direct_debit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    sepa_mandate_ref: Mapped[str | None] = mapped_column(Text)
    sepa_mandate_date: Mapped[date | None] = mapped_column(Date)

    history: Mapped[list["MemberHelperHistory"]] = relationship(
        back_populates="member", cascade="all, delete-orphan",
        order_by="MemberHelperHistory.date.desc()")
    files: Mapped[list["MemberFile"]] = relationship(cascade="all, delete-orphan",
                                                     order_by="MemberFile.id")

    @property
    def full_name(self) -> str:
        return f"{self.last_name}, {self.first_name}"


class MemberFile(Base):
    """File attached to a member; stored in the app data folder, `stored_path` is relative to it."""
    __tablename__ = "member_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    added_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)


class MemberHelperHistory(Base):
    """One helper service of a member: written automatically when a tournament is closed."""
    __tablename__ = "member_helper_history"
    __table_args__ = (UniqueConstraint("member_id", "tournament_id",
                                       name="uq_member_history_tournament"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    tournament_id: Mapped[int | None] = mapped_column(ForeignKey("tournaments.id",
                                                                 ondelete="SET NULL"))
    tournament_name: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=True)
    role: Mapped[str | None] = mapped_column(Text)
    hours: Mapped[float | None] = mapped_column(Float)
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    member: Mapped["Member"] = relationship(back_populates="history")


class TournamentHelper(Base):
    """Helper of one tournament: either linked to a member, or entered manually (own name fields)."""
    __tablename__ = "tournament_helpers"
    __table_args__ = (UniqueConstraint("tournament_id", "member_id",
                                       name="uq_tournament_helpers_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    member_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"))
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    task: Mapped[str | None] = mapped_column(Text)
    time_from: Mapped[str | None] = mapped_column(Text)
    time_to: Mapped[str | None] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    member: Mapped["Member | None"] = relationship()


class ScoreSheetTemplate(Base):
    __tablename__ = "score_sheet_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    tournament_type: Mapped[str] = mapped_column(Text, nullable=False, default="custom")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    column_config: Mapped[str] = mapped_column(Text, default="[]")
    header_fields: Mapped[str] = mapped_column(Text, default='["name","bow_class","start_number"]')


class Prize(Base):
    __tablename__ = "prizes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    bow_class_id: Mapped[int | None] = mapped_column(ForeignKey("bow_classes.id"))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    value: Mapped[float | None] = mapped_column(Float)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    bow_class: Mapped["BowClass | None"] = relationship()


class CourseTarget(Base):
    __tablename__ = "course_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    animal_name: Mapped[str | None] = mapped_column(Text)
    distance_m: Mapped[float | None] = mapped_column(Float)
    arrow_stop_class: Mapped[str | None] = mapped_column(Text)
    terrain_type: Mapped[str | None] = mapped_column(Text)
    max_group_size: Mapped[int | None] = mapped_column(Integer)
    helper_note: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ScheduleGroup(Base):
    __tablename__ = "schedule_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    group_name: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[str | None] = mapped_column(Text)
    estimated_duration_min: Mapped[int | None] = mapped_column(Integer)


class PhaseTransitionLog(Base):
    __tablename__ = "phase_transition_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    from_phase: Mapped[str | None] = mapped_column(Text)
    to_phase: Mapped[str] = mapped_column(Text)
    transitioned_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    forced: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings_at_transition: Mapped[list | None] = mapped_column(JSON)


class BackupLog(Base):
    __tablename__ = "backup_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)
    file_name: Mapped[str | None] = mapped_column(Text)
    target: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    log_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)
    tournament_id: Mapped[int | None] = mapped_column(Integer)
    participant_id: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    detail_json: Mapped[dict | None] = mapped_column(JSON)


class InventoryCategory(Base):
    __tablename__ = "inventory_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("inventory_categories.id"))
    size: Mapped[str | None] = mapped_column(Text)
    shop_url: Mapped[str | None] = mapped_column(Text)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    use_in_course: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                                server_default="0")
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")

    category: Mapped["InventoryCategory | None"] = relationship()
    files: Mapped[list["InventoryFile"]] = relationship(cascade="all, delete-orphan",
                                                        order_by="InventoryFile.id")
    repairs: Mapped[list["InventoryRepair"]] = relationship(
        cascade="all, delete-orphan", order_by="InventoryRepair.date, InventoryRepair.id")


class InventoryFile(Base):
    """File attached to an inventory item; `stored_path` is relative to the app data folder."""
    __tablename__ = "inventory_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    added_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)


class InventoryRepair(Base):
    __tablename__ = "inventory_repairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    performed_by: Mapped[str | None] = mapped_column(Text)
    invoice_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_files.id", ondelete="SET NULL"))

    invoice_file: Mapped["InventoryFile | None"] = relationship()


class CourseItem(Base):
    """Inventory item (or one-off item) a tournament needs for its course."""
    __tablename__ = "course_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    inventory_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    is_one_off: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                             server_default="0")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    inventory_item: Mapped["InventoryItem | None"] = relationship()

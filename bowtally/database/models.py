# -*- coding: utf-8 -*-
"""ORM models for all BowTally tables."""
from datetime import date, datetime

from sqlalchemy import (JSON, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey,
                        Integer, String, Table, Text, UniqueConstraint)
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
    notes: Mapped[str | None] = mapped_column(Text)
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

tournament_bow_classes = Table(
    "tournament_bow_classes", Base.metadata,
    Column("tournament_id", ForeignKey("tournaments.id", ondelete="CASCADE"), primary_key=True),
    Column("bow_class_id", ForeignKey("bow_classes.id"), primary_key=True),
)


class Tournament(Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'active', 'closed')", name="ck_tournaments_status"),
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

    scoring_rule: Mapped["ScoringRule | None"] = relationship()
    bow_classes: Mapped[list["BowClass"]] = relationship(
        secondary=tournament_bow_classes, order_by="BowClass.sort_order")
    participants: Mapped[list["TournamentParticipant"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan")


class TournamentParticipant(Base):
    __tablename__ = "tournament_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"))
    archer_id: Mapped[int] = mapped_column(ForeignKey("archers.id"))
    bow_class_id: Mapped[int | None] = mapped_column(ForeignKey("bow_classes.id"))
    start_number: Mapped[int | None] = mapped_column(Integer)
    start_group: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[str | None] = mapped_column(Text)
    registered_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now)

    tournament: Mapped["Tournament"] = relationship(back_populates="participants")
    archer: Mapped["Archer"] = relationship()
    bow_class: Mapped["BowClass | None"] = relationship()
    scores: Mapped[list["Score"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan")


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("participant_id", "target_number", "shot_number",
                                       name="uq_scores_participant_target_shot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="CASCADE"))
    target_number: Mapped[int] = mapped_column(Integer, nullable=False)
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    zone_hit: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    entered_at: Mapped[datetime | None] = mapped_column(DateTime, default=_now, onupdate=_now)

    participant: Mapped["TournamentParticipant"] = relationship(back_populates="scores")

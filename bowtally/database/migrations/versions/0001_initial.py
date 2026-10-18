# -*- coding: utf-8 -*-
"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_settings",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.Text),
        sa.Column("value_type", sa.Text, nullable=False, server_default="string"),
        sa.Column("updated_at", sa.DateTime),
        sa.CheckConstraint("value_type IN ('string', 'integer', 'boolean', 'color', 'path')",
                           name="ck_app_settings_value_type"),
    )
    op.create_table(
        "club_profile",
        sa.Column("id", sa.Integer, primary_key=True, server_default="1"),
        sa.Column("club_name", sa.Text),
        sa.Column("street", sa.Text),
        sa.Column("zip_code", sa.Text),
        sa.Column("city", sa.Text),
        sa.Column("country", sa.Text, server_default="Deutschland"),
        sa.Column("phone", sa.Text),
        sa.Column("email", sa.Text),
        sa.Column("website", sa.Text),
        sa.Column("logo_path", sa.Text),
        sa.Column("federation", sa.Text),
        sa.Column("club_number", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_table(
        "scoring_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("is_builtin", sa.Boolean, server_default=sa.false()),
        sa.Column("ring_values", sa.JSON),
        sa.Column("max_shots_per_target", sa.Integer, server_default="1"),
        sa.Column("allow_retry_shot", sa.Boolean, server_default=sa.false()),
        sa.Column("rules_json", sa.JSON),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "bow_classes",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("abbreviation", sa.Text),
        sa.Column("age_group", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("is_builtin", sa.Boolean, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )
    op.create_table(
        "archers",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("first_name", sa.Text, nullable=False),
        sa.Column("last_name", sa.Text, nullable=False),
        sa.Column("birth_date", sa.Date),
        sa.Column("club", sa.Text),
        sa.Column("member_number", sa.Text),
        sa.Column("email", sa.Text),
        sa.Column("phone", sa.Text),
        sa.Column("default_bow_class_id", sa.Integer, sa.ForeignKey("bow_classes.id")),
        sa.Column("notes", sa.Text),
        sa.Column("active", sa.Boolean, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("location", sa.Text),
        sa.Column("organizer", sa.Text),
        sa.Column("status", sa.String(10), server_default="draft"),
        sa.Column("num_targets", sa.Integer, nullable=False),
        sa.Column("shots_per_target", sa.Integer, server_default="1"),
        sa.Column("scoring_rule_id", sa.Integer, sa.ForeignKey("scoring_rules.id")),
        sa.Column("start_groups", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime),
        sa.CheckConstraint("status IN ('draft', 'active', 'closed')",
                           name="ck_tournaments_status"),
    )
    op.create_table(
        "tournament_bow_classes",
        sa.Column("tournament_id", sa.Integer,
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("bow_class_id", sa.Integer, sa.ForeignKey("bow_classes.id"), primary_key=True),
    )
    op.create_table(
        "tournament_participants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tournament_id", sa.Integer,
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE")),
        sa.Column("archer_id", sa.Integer, sa.ForeignKey("archers.id")),
        sa.Column("bow_class_id", sa.Integer, sa.ForeignKey("bow_classes.id")),
        sa.Column("start_number", sa.Integer),
        sa.Column("start_group", sa.Text),
        sa.Column("start_time", sa.Text),
        sa.Column("registered_at", sa.DateTime),
    )
    op.create_table(
        "scores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("participant_id", sa.Integer,
                  sa.ForeignKey("tournament_participants.id", ondelete="CASCADE")),
        sa.Column("target_number", sa.Integer, nullable=False),
        sa.Column("shot_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("zone_hit", sa.Text),
        sa.Column("points", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("entered_at", sa.DateTime),
        sa.UniqueConstraint("participant_id", "target_number", "shot_number",
                            name="uq_scores_participant_target_shot"),
    )


def downgrade():
    for t in ("scores", "tournament_participants", "tournament_bow_classes", "tournaments",
              "archers", "bow_classes", "scoring_rules", "club_profile", "app_settings"):
        op.drop_table(t)

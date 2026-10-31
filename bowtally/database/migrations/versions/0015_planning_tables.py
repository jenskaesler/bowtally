# -*- coding: utf-8 -*-
"""Add course_targets and schedule_groups tables for parcours planning and scheduling.

Revision ID: 0015_planning_tables
Revises: 0014_more_builtin_rules
Create Date: 2026-10-31
"""
import sqlalchemy as sa
from alembic import op

revision = "0015_planning_tables"
down_revision = "0014_more_builtin_rules"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "course_targets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("animal_name", sa.Text()),
        sa.Column("distance_m", sa.Float()),
        sa.Column("arrow_stop_class", sa.Text()),
        sa.Column("terrain_type", sa.Text()),
        sa.Column("max_group_size", sa.Integer()),
        sa.Column("helper_note", sa.Text()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "schedule_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("group_name", sa.Text(), nullable=False),
        sa.Column("start_time", sa.Text()),
        sa.Column("estimated_duration_min", sa.Integer()),
    )


def downgrade():
    op.drop_table("schedule_groups")
    op.drop_table("course_targets")

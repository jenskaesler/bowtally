# -*- coding: utf-8 -*-
"""Add helpers master table and tournament_helpers assignment table

Revision ID: 0010_helpers
Revises: 0009_waitlisted
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_helpers"
down_revision = "0009_waitlisted"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "helpers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "tournament_helpers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("helper_id", sa.Integer(),
                  sa.ForeignKey("helpers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task", sa.Text()),
        sa.Column("time_from", sa.Text()),
        sa.Column("time_to", sa.Text()),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default="0"),
    )


def downgrade():
    op.drop_table("tournament_helpers")
    op.drop_table("helpers")

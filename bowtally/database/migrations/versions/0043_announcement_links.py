# -*- coding: utf-8 -*-
"""Ausschreibungslinks: Links zu bereits veröffentlichten Ausschreibungen je Turnier

Neue, leere Tabelle; keine Datenmigration.

Revision ID: 0043_announcement_links
Revises: 0042_participant_unique_archer
Create Date: 2026-11-22
"""
import sqlalchemy as sa
from alembic import op

revision = "0043_announcement_links"
down_revision = "0042_participant_unique_archer"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "announcement_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("platform_label", sa.Text()),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )


def downgrade():
    op.drop_table("announcement_links")

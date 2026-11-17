# -*- coding: utf-8 -*-
"""Dateien zu Mitgliedern (liegen im Datenordner der App)

Revision ID: 0034_member_files
Revises: 0033_remove_unverified_rules
Create Date: 2026-11-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0034_member_files"
down_revision = "0033_remove_unverified_rules"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "member_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(),
                  sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("added_at", sa.DateTime()),
    )


def downgrade():
    op.drop_table("member_files")

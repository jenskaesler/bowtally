# -*- coding: utf-8 -*-
"""Dateien zu Schützen (liegen im Datenordner der App)

Revision ID: 0036_archer_files
Revises: 0035_logo_folder
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0036_archer_files"
down_revision = "0035_logo_folder"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "archer_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("archer_id", sa.Integer(),
                  sa.ForeignKey("archers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("added_at", sa.DateTime()),
    )


def downgrade():
    op.drop_table("archer_files")

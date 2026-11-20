# -*- coding: utf-8 -*-
"""Schützen: Passnummer

Revision ID: 0040_archer_pass_number
Revises: 0039_helper_history_manual
Create Date: 2026-11-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0040_archer_pass_number"
down_revision = "0039_helper_history_manual"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("archers") as batch_op:
        batch_op.add_column(sa.Column("pass_number", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("archers") as batch_op:
        batch_op.drop_column("pass_number")

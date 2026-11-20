# -*- coding: utf-8 -*-
"""Schützen: Mitgliedsnummer entfällt (bisherige Werte wandern in die leere Passnummer)

Revision ID: 0041_archer_drop_member_number
Revises: 0040_archer_pass_number
Create Date: 2026-11-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0041_archer_drop_member_number"
down_revision = "0040_archer_pass_number"
branch_labels = None
depends_on = None


def upgrade():
    # keep the numbers: up to now the import mapped "Passnummer" to the member number
    op.execute("UPDATE archers SET pass_number = member_number "
               "WHERE (pass_number IS NULL OR pass_number = '') "
               "AND member_number IS NOT NULL AND member_number <> ''")
    with op.batch_alter_table("archers") as batch_op:
        batch_op.drop_column("member_number")


def downgrade():
    with op.batch_alter_table("archers") as batch_op:
        batch_op.add_column(sa.Column("member_number", sa.Text(), nullable=True))

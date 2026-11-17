# -*- coding: utf-8 -*-
"""Helferhistorie: manuell erfasste Einsätze dürfen mit einem Turnier verknüpft sein

Revision ID: 0039_helper_history_manual
Revises: 0038_inventory_active_repair_file
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0039_helper_history_manual"
down_revision = "0038_inventory_active_repair_file"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("member_helper_history") as batch_op:
        batch_op.add_column(sa.Column("is_manual", sa.Boolean(), nullable=False,
                                      server_default="0"))


def downgrade():
    with op.batch_alter_table("member_helper_history") as batch_op:
        batch_op.drop_column("is_manual")

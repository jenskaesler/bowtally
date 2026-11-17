# -*- coding: utf-8 -*-
"""Inventar: Artikel aktiv/inaktiv, Rechnung (Dokument) zur Reparatur

Revision ID: 0038_inventory_active_repair_file
Revises: 0037_inventory_rebuild
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0038_inventory_active_repair_file"
down_revision = "0037_inventory_rebuild"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default="1"))
    with op.batch_alter_table("inventory_repairs") as batch_op:
        batch_op.add_column(sa.Column("invoice_file_id", sa.Integer()))
        batch_op.create_foreign_key("fk_repairs_invoice_file", "inventory_files",
                                    ["invoice_file_id"], ["id"], ondelete="SET NULL")


def downgrade():
    with op.batch_alter_table("inventory_repairs") as batch_op:
        batch_op.drop_constraint("fk_repairs_invoice_file", type_="foreignkey")
        batch_op.drop_column("invoice_file_id")
    with op.batch_alter_table("inventory_items") as batch_op:
        batch_op.drop_column("active")

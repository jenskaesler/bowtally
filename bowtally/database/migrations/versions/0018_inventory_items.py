# -*- coding: utf-8 -*-
"""Add inventory_items table."""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("manufacturer", sa.Text()),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("condition", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.CheckConstraint("item_type IN ('target_face', '3d_target')", name="ck_inventory_type"),
        sa.CheckConstraint("condition IN ('gut', 'mittel', 'schlecht') OR condition IS NULL",
                           name="ck_inventory_condition"),
    )


def downgrade():
    op.drop_table("inventory_items")

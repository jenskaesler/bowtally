# -*- coding: utf-8 -*-
"""Inventar-Neuaufbau: Kategorien, Preise, Dateien, Reparaturen, Parcours-Posten

Das alte Inventar (Scheiben / 3D-Ziele) wird bewusst nicht übernommen.

Revision ID: 0037_inventory_rebuild
Revises: 0036_archer_files
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0037_inventory_rebuild"
down_revision = "0036_archer_files"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("inventory_items")
    op.create_table(
        "inventory_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("inventory_categories.id")),
        sa.Column("size", sa.Text()),
        sa.Column("shop_url", sa.Text()),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("use_in_course", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "inventory_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(),
                  sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("added_at", sa.DateTime()),
    )
    op.create_table(
        "inventory_repairs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(),
                  sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("cost", sa.Float(), nullable=False),
        sa.Column("performed_by", sa.Text()),
    )
    op.create_table(
        "course_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_item_id", sa.Integer(),
                  sa.ForeignKey("inventory_items.id", ondelete="SET NULL")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_one_off", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )


def downgrade():
    for table in ("course_items", "inventory_repairs", "inventory_files", "inventory_items",
                  "inventory_categories"):
        op.drop_table(table)
    op.create_table(
        "inventory_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_type", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("manufacturer", sa.Text()),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("condition", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("active", sa.Boolean(), server_default="1"),
        sa.CheckConstraint("item_type IN ('target_face', '3d_target')", name="ck_inventory_type"),
        sa.CheckConstraint("condition IN ('gut', 'mittel', 'schlecht') OR condition IS NULL",
                           name="ck_inventory_condition"),
    )

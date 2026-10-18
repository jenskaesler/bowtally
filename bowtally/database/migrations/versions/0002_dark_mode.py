# -*- coding: utf-8 -*-
"""Dark mode settings

Revision ID: 0002_dark_mode
Revises: 0001_initial
Create Date: 2026-10-18
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0002_dark_mode"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

KEYS = ["color_text", "color_dark_background", "color_dark_surface", "color_dark_border",
        "color_dark_text", "color_dark_text_secondary", "ui_theme_mode"]


def upgrade():
    conn = op.get_bind()
    # Fresh database: table is empty and seed.py inserts everything after the migrations.
    if not conn.execute(sa.text("SELECT COUNT(*) FROM app_settings")).scalar():
        return
    from bowtally.database.seed import DEFAULT_SETTINGS
    existing = set(conn.execute(sa.text("SELECT key FROM app_settings")).scalars())
    for key, value, category, value_type, description in DEFAULT_SETTINGS:
        if key in KEYS and key not in existing:
            conn.execute(sa.text(
                "INSERT INTO app_settings (key, value, category, value_type, description, "
                "updated_at) VALUES (:k, :v, :c, :t, :d, :u)"),
                {"k": key, "v": value, "c": category, "t": value_type, "d": description,
                 "u": datetime.now().isoformat(sep=" ")})


def downgrade():
    op.execute(sa.text("DELETE FROM app_settings WHERE key IN ("
                       + ", ".join(f"'{k}'" for k in KEYS) + ")"))

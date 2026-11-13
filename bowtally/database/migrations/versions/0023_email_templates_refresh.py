# -*- coding: utf-8 -*-
"""Refresh the default e-mail templates.

Revision ID: 0023_email_templates_refresh
Revises: 0022_archer_notify
Create Date: 2026-11-13
"""
from alembic import op

revision = "0023_email_templates_refresh"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    from bowtally.database.seed import DEFAULT_SETTINGS
    from sqlalchemy import text

    bind = op.get_bind()
    for key, value, category, value_type, description in DEFAULT_SETTINGS:
        if not key.startswith("email_"):
            continue
        bind.execute(
            text("UPDATE app_settings SET value = :v WHERE key = :k"),
            {"v": value, "k": key},
        )


def downgrade():
    pass
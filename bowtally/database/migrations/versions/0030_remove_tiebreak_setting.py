# -*- coding: utf-8 -*-
"""Die globale Tie-Break-Einstellung entfällt: der Gleichstand wird je Regelwerk festgelegt

Revision ID: 0030_remove_tiebreak_setting
Revises: 0029_members
Create Date: 2026-11-18
"""
from alembic import op

revision = "0030_remove_tiebreak_setting"
down_revision = "0029_members"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM app_settings WHERE key = 'result_tiebreak_mode'")


def downgrade():
    pass

# -*- coding: utf-8 -*-
"""Add waitlisted registration status and waitlist_mode setting

Revision ID: 0009_waitlisted
Revises: 0008_email_templates
Create Date: 2026-10-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_waitlisted"
down_revision = "0008_email_templates"
branch_labels = None
depends_on = None

_NEW_CHECK = ("registration_status IN ('registered', 'confirmed', 'checked_in', "
              "'dns', 'dnf', 'dsq', 'withdrawn', 'waitlisted')")
_OLD_CHECK = ("registration_status IN ('registered', 'confirmed', 'checked_in', "
              "'dns', 'dnf', 'dsq', 'withdrawn')")


def upgrade():
    with op.batch_alter_table("tournament_participants") as batch_op:
        batch_op.drop_constraint("ck_participants_registration", type_="check")
        batch_op.create_check_constraint("ck_participants_registration", _NEW_CHECK)
    tbl = sa.table("app_settings",
                   sa.column("key"), sa.column("value"), sa.column("category"),
                   sa.column("value_type"), sa.column("description"))
    op.bulk_insert(tbl, [{"key": "waitlist_mode", "value": "auto", "category": "behavior",
                          "value_type": "string",
                          "description": "Warteliste: auto (automatisch) oder block (sperren)"}])


def downgrade():
    with op.batch_alter_table("tournament_participants") as batch_op:
        batch_op.drop_constraint("ck_participants_registration", type_="check")
        batch_op.create_check_constraint("ck_participants_registration", _OLD_CHECK)
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM app_settings WHERE key = 'waitlist_mode'"))

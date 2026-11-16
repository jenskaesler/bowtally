# -*- coding: utf-8 -*-
"""Results e-mail template: the result list is now an attachment, not on the club website.

Only the unchanged default text is replaced, edited templates stay as they are.

Revision ID: 0026_email_results_attachment
Revises: 0025_archer_notify_results
Create Date: 2026-11-16
"""
from alembic import op
from sqlalchemy import text

revision = "0026_email_results_attachment"
down_revision = "0025_archer_notify_results"
branch_labels = None
depends_on = None

OLD = "Die vollständige Ergebnisliste findest du auf der Vereinswebsite. "
NEW = "Die vollständige Ergebnisliste findest du im Anhang. "


def upgrade():
    op.get_bind().execute(
        text("UPDATE app_settings SET value = REPLACE(value, :old, :new) "
             "WHERE key = 'email_results_body'"), {"old": OLD, "new": NEW})


def downgrade():
    pass

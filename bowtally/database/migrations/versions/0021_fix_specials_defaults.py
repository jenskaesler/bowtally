# -*- coding: utf-8 -*-
"""Fix malformed tracked_specials / specials values left by server_default quirk in 0020."""
from alembic import op
import sqlalchemy as sa

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # server_default="'[]'" on SQLite stored the literal text "'[]'" for pre-existing rows
    # instead of the JSON value [].  Fix any value that is not a valid JSON array/object.
    conn.execute(sa.text(
        "UPDATE scoring_rules SET tracked_specials = '[]' "
        "WHERE tracked_specials IS NULL OR tracked_specials = '' "
        "OR (tracked_specials NOT LIKE '[%' AND tracked_specials NOT LIKE 'n%')"
    ))
    conn.execute(sa.text(
        "UPDATE scores SET specials = '{}' "
        "WHERE specials IS NULL OR specials = '' "
        "OR (specials NOT LIKE '{%' AND specials NOT LIKE 'n%')"
    ))


def downgrade():
    pass  # data-only fix, not reversible

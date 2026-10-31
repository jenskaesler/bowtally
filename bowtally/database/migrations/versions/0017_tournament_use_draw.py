# -*- coding: utf-8 -*-
"""Add use_draw flag to tournaments."""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016_score_sheets_prizes"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tournaments") as batch:
        batch.add_column(sa.Column("use_draw", sa.Boolean(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("tournaments") as batch:
        batch.drop_column("use_draw")

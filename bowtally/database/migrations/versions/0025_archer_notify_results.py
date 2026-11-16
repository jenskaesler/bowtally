# -*- coding: utf-8 -*-
"""Add notify_results flag to archers."""
from alembic import op
import sqlalchemy as sa

revision = "0025_archer_notify_results"
down_revision = "0024_rules_text_fields"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("archers") as batch_op:
        batch_op.add_column(sa.Column("notify_results", sa.Boolean(),
                                      nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("archers") as batch_op:
        batch_op.drop_column("notify_results")

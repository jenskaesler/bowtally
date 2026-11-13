# -*- coding: utf-8 -*-
"""Add notify_new_tournament flag to archers."""
from alembic import op
import sqlalchemy as sa

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("archers") as batch_op:
        batch_op.add_column(sa.Column("notify_new_tournament", sa.Boolean(),
                                      nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("archers") as batch_op:
        batch_op.drop_column("notify_new_tournament")

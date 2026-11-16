# -*- coding: utf-8 -*-
"""Add internal_notes to tournaments (Tab Notizen, getrennt von den Parcours-Hinweisen)."""
from alembic import op
import sqlalchemy as sa

revision = "0027_internal_notes"
down_revision = "0026_email_results_attachment"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tournaments") as batch_op:
        batch_op.add_column(sa.Column("internal_notes", sa.Text()))


def downgrade():
    with op.batch_alter_table("tournaments") as batch_op:
        batch_op.drop_column("internal_notes")

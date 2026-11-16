# -*- coding: utf-8 -*-
"""Add tournament_rules and participation_conditions to scoring_rules.

Revision ID: 0024_rules_text_fields
Revises: 0023
Create Date: 2026-11-15
"""
import sqlalchemy as sa
from alembic import op

revision = "0024_rules_text_fields"
down_revision = "0023_email_templates_refresh"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("scoring_rules") as batch_op:
        batch_op.add_column(sa.Column("tournament_rules", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("participation_conditions", sa.Text(), nullable=True))
    # Standard-Regelwerk (3D Standard 3-Pfeil) setzt seed.run beim Start.


def downgrade():
    with op.batch_alter_table("scoring_rules") as batch_op:
        batch_op.drop_column("participation_conditions")
        batch_op.drop_column("tournament_rules")

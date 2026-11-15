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
    # point 10: make "3D Standard 3-Pfeil" the default rule set if none is set yet
    conn = op.get_bind()
    set_already = conn.execute(
        sa.text("SELECT value FROM app_settings WHERE key = 'default_scoring_rule_id'")
    ).scalar()
    if not set_already:
        default_id = conn.execute(
            sa.text("SELECT id FROM scoring_rules WHERE name = '3D Standard 3-Pfeil'")
        ).scalar()
        if default_id is not None:
            conn.execute(
                sa.text("UPDATE app_settings SET value = :v WHERE key = 'default_scoring_rule_id'"),
                {"v": str(default_id)},
            )


def downgrade():
    with op.batch_alter_table("scoring_rules") as batch_op:
        batch_op.drop_column("participation_conditions")
        batch_op.drop_column("tournament_rules")

# -*- coding: utf-8 -*-
"""Club profile: bank data and course description fields

Revision ID: 0004_club_profile_extended
Revises: 0003_tournament_lifecycle
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_club_profile_extended"
down_revision = "0003_tournament_lifecycle"
branch_labels = None
depends_on = None


def upgrade():
    for col in ("bank_account_holder", "bank_iban", "bank_bic", "bank_reference_template",
                "course_description"):
        op.add_column("club_profile", sa.Column(col, sa.Text))


def downgrade():
    for col in ("bank_account_holder", "bank_iban", "bank_bic", "bank_reference_template",
                "course_description"):
        op.drop_column("club_profile", col)

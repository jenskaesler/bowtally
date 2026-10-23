# -*- coding: utf-8 -*-
"""Club profile: phone and email per board role

Revision ID: 0007_contacts_phone_email
Revises: 0006_draft_phase
Create Date: 2026-10-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_contacts_phone_email"
down_revision = "0006_draft_phase"
branch_labels = None
depends_on = None

_COLS = ("first_board_phone", "first_board_email",
         "second_board_phone", "second_board_email",
         "treasurer_phone", "treasurer_email",
         "sports_dir_phone", "sports_dir_email",
         "bow_ref_phone", "bow_ref_email")


def upgrade():
    for col in _COLS:
        op.add_column("club_profile", sa.Column(col, sa.Text))


def downgrade():
    for col in _COLS:
        op.drop_column("club_profile", col)

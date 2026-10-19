# -*- coding: utf-8 -*-
"""Club profile: Vereinsvorstand contact person fields

Revision ID: 0005_club_contacts
Revises: 0004_club_profile_extended
Create Date: 2026-10-19
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_club_contacts"
down_revision = "0004_club_profile_extended"
branch_labels = None
depends_on = None

_COLS = ("first_board_fname", "first_board_lname", "second_board_fname", "second_board_lname",
         "treasurer_fname", "treasurer_lname", "sports_dir_fname", "sports_dir_lname",
         "bow_ref_fname", "bow_ref_lname")


def upgrade():
    for col in _COLS:
        op.add_column("club_profile", sa.Column(col, sa.Text))


def downgrade():
    for col in _COLS:
        op.drop_column("club_profile", col)

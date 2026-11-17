# -*- coding: utf-8 -*-
"""Ergebnis des Stechens je Teilnehmer (entscheidet nur noch Gleichstände)

Revision ID: 0032_shoot_off_points
Revises: 0031_builtin_zone_types
Create Date: 2026-11-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0032_shoot_off_points"
down_revision = "0031_builtin_zone_types"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tournament_participants", sa.Column("shoot_off_points", sa.Integer()))


def downgrade():
    op.drop_column("tournament_participants", "shoot_off_points")

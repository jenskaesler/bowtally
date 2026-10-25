# -*- coding: utf-8 -*-
"""Add active flag to helpers table

Revision ID: 0011_helper_active
Revises: 0010_helpers
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0011_helper_active"
down_revision = "0010_helpers"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("helpers", sa.Column("active", sa.Boolean(), nullable=False, server_default="1"))


def downgrade():
    op.drop_column("helpers", "active")

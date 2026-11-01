# -*- coding: utf-8 -*-
"""Add backup_log and activity_log tables."""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "backup_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("file_name", sa.Text()),
        sa.Column("target", sa.Text()),
        sa.Column("file_size_bytes", sa.Integer()),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("error_message", sa.Text()),
    )
    op.create_table(
        "activity_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("log_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("tournament_id", sa.Integer()),
        sa.Column("participant_id", sa.Integer()),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("detail_json", sa.JSON()),
    )


def downgrade():
    op.drop_table("activity_log")
    op.drop_table("backup_log")

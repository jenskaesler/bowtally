# -*- coding: utf-8 -*-
"""Add multi-round tournament support

Revision ID: 0012_multi_round
Revises: 0011_helper_active
Create Date: 2026-10-25
"""
import sqlalchemy as sa
from alembic import op

revision = "0012_multi_round"
down_revision = "0011_helper_active"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tournaments",
                  sa.Column("num_rounds", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("tournaments",
                  sa.Column("scoring_mode", sa.Text(), nullable=False,
                            server_default="per_target"))

    op.create_table(
        "tournament_rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("num_targets", sa.Integer(), nullable=True),
        sa.Column("scoring_rule_id", sa.Integer(),
                  sa.ForeignKey("scoring_rules.id"), nullable=True),
        sa.Column("distance_type", sa.Text(), nullable=True),
        sa.Column("shots_per_target", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "distance_type IN ('known', 'unknown') OR distance_type IS NULL",
            name="ck_rounds_distance_type"),
        sa.UniqueConstraint("tournament_id", "round_number",
                            name="uq_rounds_tournament_round"),
    )

    with op.batch_alter_table("scores") as batch_op:
        batch_op.add_column(
            sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"))
        batch_op.drop_constraint("uq_scores_participant_target_shot", type_="unique")
        batch_op.create_unique_constraint(
            "uq_scores_participant_round_target_shot",
            ["participant_id", "round_number", "target_number", "shot_number"])


def downgrade():
    with op.batch_alter_table("scores") as batch_op:
        batch_op.drop_constraint("uq_scores_participant_round_target_shot", type_="unique")
        batch_op.create_unique_constraint(
            "uq_scores_participant_target_shot",
            ["participant_id", "target_number", "shot_number"])
        batch_op.drop_column("round_number")

    op.drop_table("tournament_rounds")
    op.drop_column("tournaments", "scoring_mode")
    op.drop_column("tournaments", "num_rounds")

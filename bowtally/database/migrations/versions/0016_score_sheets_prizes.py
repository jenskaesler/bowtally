# -*- coding: utf-8 -*-
"""Add score_sheet_templates and prizes tables.

Revision ID: 0016_score_sheets_prizes
Revises: 0015_planning_tables
Create Date: 2026-10-31
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0016_score_sheets_prizes"
down_revision = "0015_planning_tables"
branch_labels = None
depends_on = None

_BUILTIN_TEMPLATES = [
    {
        "name": "3D-Standard",
        "tournament_type": "3d",
        "column_config": json.dumps([
            {"name": "Pfeil 1", "type": "number", "width_mm": 14},
            {"name": "Pfeil 2", "type": "number", "width_mm": 14},
            {"name": "Bester Pfeil", "type": "number", "width_mm": 18},
        ]),
        "header_fields": json.dumps(["name", "bow_class", "start_number", "start_group", "club"]),
    },
    {
        "name": "Feld-Standard",
        "tournament_type": "field",
        "column_config": json.dumps([
            {"name": "X", "type": "checkbox", "width_mm": 10},
            {"name": "Wert", "type": "number", "width_mm": 12},
            {"name": "Pfeil 2", "type": "number", "width_mm": 12},
            {"name": "Pfeil 3", "type": "number", "width_mm": 12},
            {"name": "Summe", "type": "number", "width_mm": 16},
        ]),
        "header_fields": json.dumps(["name", "bow_class", "start_number", "start_group", "club"]),
    },
    {
        "name": "Halle 10-Ring",
        "tournament_type": "indoor",
        "column_config": json.dumps([
            {"name": "Pfeil 1", "type": "number", "width_mm": 12},
            {"name": "Pfeil 2", "type": "number", "width_mm": 12},
            {"name": "Pfeil 3", "type": "number", "width_mm": 12},
            {"name": "Summe", "type": "number", "width_mm": 16},
        ]),
        "header_fields": json.dumps(["name", "bow_class", "start_number", "start_group", "club"]),
    },
    {
        "name": "Blasrohr-Standard",
        "tournament_type": "blowpipe",
        "column_config": json.dumps([
            {"name": "Wertung", "type": "number", "width_mm": 20},
            {"name": "Punkte", "type": "number", "width_mm": 16},
        ]),
        "header_fields": json.dumps(["name", "bow_class", "start_number", "start_group", "club"]),
    },
]


def upgrade():
    op.create_table(
        "score_sheet_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("tournament_type", sa.Text(), nullable=False, server_default="custom"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("column_config", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("header_fields", sa.Text(), nullable=False,
                  server_default='["name","bow_class","start_number"]'),
    )
    op.create_table(
        "prizes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bow_class_id", sa.Integer(), sa.ForeignKey("bow_classes.id")),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("value", sa.Float()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    conn = op.get_bind()
    for tmpl in _BUILTIN_TEMPLATES:
        conn.execute(sa.text(
            "INSERT INTO score_sheet_templates (name, tournament_type, is_builtin, "
            "column_config, header_fields) VALUES (:name, :tournament_type, 1, "
            ":column_config, :header_fields)"
        ), tmpl)


def downgrade():
    op.drop_table("prizes")
    op.drop_table("score_sheet_templates")

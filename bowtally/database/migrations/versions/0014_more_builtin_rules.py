# -*- coding: utf-8 -*-
"""Add 5 more builtin scoring rules (DBSV Wald/Jagd, IBO 12-Ring, NFAA, WA 25m)

Revision ID: 0014_more_builtin_rules
Revises: 0013_builtin_rules
Create Date: 2026-10-25
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0014_more_builtin_rules"
down_revision = "0013_builtin_rules"
branch_labels = None
depends_on = None


def upgrade():
    from bowtally.database.seed import DEFAULT_SCORING_RULES
    new_rules = DEFAULT_SCORING_RULES[9:]  # first 9 were added in 0001/0013
    conn = op.get_bind()
    existing = {row[0] for row in conn.execute(
        sa.text("SELECT name FROM scoring_rules WHERE is_builtin = 1"))}
    for rule in new_rules:
        if rule["name"] not in existing:
            conn.execute(sa.text(
                "INSERT INTO scoring_rules "
                "(is_builtin, name, description, ring_values, "
                " max_shots_per_target, allow_retry_shot, rules_json) "
                "VALUES (:is_builtin, :name, :description, :ring_values, "
                "        :max_shots_per_target, :allow_retry_shot, :rules_json)"
            ), {
                "is_builtin": 1,
                "name": rule["name"],
                "description": rule.get("description", ""),
                "ring_values": json.dumps(rule.get("ring_values", [])),
                "max_shots_per_target": rule.get("max_shots_per_target", 1),
                "allow_retry_shot": int(rule.get("allow_retry_shot", False)),
                "rules_json": json.dumps(rule.get("rules_json", {})),
            })


def downgrade():
    from bowtally.database.seed import DEFAULT_SCORING_RULES
    names = [r["name"] for r in DEFAULT_SCORING_RULES[9:]]
    placeholders = ", ".join(f":n{i}" for i in range(len(names)))
    params = {f"n{i}": n for i, n in enumerate(names)}
    op.get_bind().execute(
        sa.text(f"DELETE FROM scoring_rules WHERE is_builtin = 1 AND name IN ({placeholders})"),
        params,
    )

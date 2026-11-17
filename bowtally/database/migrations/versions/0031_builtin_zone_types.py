# -*- coding: utf-8 -*-
"""Eingebaute Regelwerke: Zonen mit Typ versehen, damit Kills, X und Fehlschüsse "Pro Ziel" gezählt werden

Nur eindeutige Zonen: "Killzone" -> Kill, Zone "Miss" -> Fehlschuss, Zonen die mit "X" beginnen -> X.

Revision ID: 0031_builtin_zone_types
Revises: 0030_remove_tiebreak_setting
Create Date: 2026-11-18
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0031_builtin_zone_types"
down_revision = "0030_remove_tiebreak_setting"
branch_labels = None
depends_on = None


def _zone_type(name: str) -> str:
    lower = name.lower()
    if "killzone" in lower:
        return "kill"
    if lower == "miss":
        return "miss"
    return "x" if lower.startswith("x") else ""


def upgrade():
    conn = op.get_bind()
    for rule_id, ring_values in conn.execute(
            sa.text("SELECT id, ring_values FROM scoring_rules WHERE is_builtin = 1")).fetchall():
        zones = json.loads(ring_values) if isinstance(ring_values, str) else ring_values
        for zone in zones:
            if not zone.get("type") and _zone_type(zone["zone"]):
                zone["type"] = _zone_type(zone["zone"])
        conn.execute(sa.text("UPDATE scoring_rules SET ring_values = :v WHERE id = :i"),
                     {"v": json.dumps(zones, ensure_ascii=False), "i": rule_id})


def downgrade():
    pass

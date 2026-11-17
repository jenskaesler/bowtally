# -*- coding: utf-8 -*-
"""Eingebaute Regelwerke ohne belegbare Quelle entfernen

Wird ein Regelwerk noch von einem Turnier genutzt, bleibt es als eigenes Regelwerk erhalten.

Revision ID: 0033_remove_unverified_rules
Revises: 0032_shoot_off_points
Create Date: 2026-11-18
"""
import sqlalchemy as sa
from alembic import op

revision = "0033_remove_unverified_rules"
down_revision = "0032_shoot_off_points"
branch_labels = None
depends_on = None

REMOVED = ["ASA 3D", "NFAA 3D", "3D Standard 3-Pfeil", "DBSV 3D-Jagdrunde", "Blasrohr Standard"]


def upgrade():
    conn = op.get_bind()
    for name in REMOVED:
        rule_id = conn.execute(sa.text(
            "SELECT id FROM scoring_rules WHERE name = :n AND is_builtin = 1"), {"n": name}).scalar()
        if rule_id is None:
            continue
        used = conn.execute(sa.text(
            "SELECT (SELECT COUNT(*) FROM tournaments WHERE scoring_rule_id = :i) + "
            "(SELECT COUNT(*) FROM tournament_rounds WHERE scoring_rule_id = :i)"), {"i": rule_id}).scalar()
        if used:
            conn.execute(sa.text("UPDATE scoring_rules SET is_builtin = 0 WHERE id = :i"), {"i": rule_id})
        else:
            conn.execute(sa.text("DELETE FROM scoring_rules WHERE id = :i"), {"i": rule_id})


def downgrade():
    pass

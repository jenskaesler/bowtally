# -*- coding: utf-8 -*-
"""Teilnehmer: ein Schütze (Datenbank-ID) höchstens einmal je Turnier

Revision ID: 0042_participant_unique_archer
Revises: 0041_archer_drop_member_number
Create Date: 2026-11-20
"""
import logging

import sqlalchemy as sa
from alembic import op

revision = "0042_participant_unique_archer"
down_revision = "0041_archer_drop_member_number"
branch_labels = None
depends_on = None

log = logging.getLogger(__name__)
INDEX = "uq_participants_tournament_archer"


def upgrade():
    conn = op.get_bind()
    duplicates = conn.execute(sa.text(
        "SELECT tournament_id, archer_id, COUNT(*) FROM tournament_participants "
        "GROUP BY tournament_id, archer_id HAVING COUNT(*) > 1")).fetchall()
    if duplicates:
        # never delete participants (and their scores) silently: the app check still applies
        log.warning("Eindeutiger Index %s nicht angelegt, doppelte Teilnehmer vorhanden: %s",
                    INDEX, duplicates)
        return
    op.create_index(INDEX, "tournament_participants", ["tournament_id", "archer_id"],
                    unique=True)


def downgrade():
    op.execute(f"DROP INDEX IF EXISTS {INDEX}")

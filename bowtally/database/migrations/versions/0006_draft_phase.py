# -*- coding: utf-8 -*-
"""Add 'Entwurf' (draft) phase before 'Ausschreibung'

Revision ID: 0006_draft_phase
Revises: 0005_club_contacts
Create Date: 2026-10-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_draft_phase"
down_revision = "0005_club_contacts"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Idempotent: skip if 'draft' already exists
    if conn.execute(sa.text("SELECT 1 FROM tournament_phases WHERE key = 'draft'")).scalar():
        return

    # Shift sort_order of all existing phases up by 1
    op.execute("UPDATE tournament_phases SET sort_order = sort_order + 1")
    # Insert the new draft phase at position 1
    op.execute(
        "INSERT INTO tournament_phases (key, label, sort_order, description) VALUES "
        "('draft', 'Entwurf', 1, "
        "'Das Turnier wird angelegt. Alle Turnierdaten können frei bearbeitet werden. "
        "Wechsle zur Ausschreibung, wenn alles fertig ist.')"
    )


def downgrade():
    op.execute("DELETE FROM tournament_phases WHERE key = 'draft'")
    op.execute("UPDATE tournament_phases SET sort_order = sort_order - 1")
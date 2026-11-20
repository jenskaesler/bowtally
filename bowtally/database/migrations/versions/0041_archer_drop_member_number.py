# -*- coding: utf-8 -*-
"""Schützen: Mitgliedsnummer entfällt (bisherige Werte wandern in die leere Passnummer)

Revision ID: 0041_archer_drop_member_number
Revises: 0040_archer_pass_number
Create Date: 2026-11-20
"""
import sqlite3

from alembic import op

revision = "0041_archer_drop_member_number"
down_revision = "0040_archer_pass_number"
branch_labels = None
depends_on = None


def _native_drop_column() -> bool:
    """SQLite 3.35+ drops a column in place. A batch rebuild would DROP TABLE archers, which
    fails while participants and archer files point to it (foreign keys are on)."""
    return tuple(int(x) for x in sqlite3.sqlite_version.split(".")[:2]) >= (3, 35)


def upgrade():
    # keep the numbers: up to now the import mapped "Passnummer" to the member number
    op.execute("UPDATE archers SET pass_number = member_number "
               "WHERE (pass_number IS NULL OR pass_number = '') "
               "AND member_number IS NOT NULL AND member_number <> ''")
    if _native_drop_column():
        op.execute("ALTER TABLE archers DROP COLUMN member_number")
        return
    # old SQLite: rebuild the table, check the foreign keys only at commit (ids stay the same)
    op.execute("PRAGMA defer_foreign_keys = ON")
    with op.batch_alter_table("archers") as batch_op:
        batch_op.drop_column("member_number")


def downgrade():
    op.execute("ALTER TABLE archers ADD COLUMN member_number TEXT")

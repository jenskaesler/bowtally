# -*- coding: utf-8 -*-
"""Vereinslogo liegt im Unterordner "logo" des Datenordners (wie im Backup)

Revision ID: 0035_logo_folder
Revises: 0034_member_files
Create Date: 2026-11-18
"""
import shutil
from pathlib import Path

import sqlalchemy as sa
from alembic import op

from bowtally import config

revision = "0035_logo_folder"
down_revision = "0034_member_files"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    logo_path = conn.execute(sa.text("SELECT logo_path FROM club_profile WHERE id = 1")).scalar()
    if not logo_path:
        return
    source = Path(logo_path)
    if not source.is_file() or source.resolve().parent != config.APP_DATA_DIR.resolve():
        return          # already moved, or lives somewhere else: leave it alone
    dest = config.APP_DATA_DIR / "logo" / source.name
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), dest)
    except OSError:
        return          # keep the old path; the logo still works from there
    conn.execute(sa.text("UPDATE club_profile SET logo_path = :p WHERE id = 1"), {"p": str(dest)})


def downgrade():
    pass

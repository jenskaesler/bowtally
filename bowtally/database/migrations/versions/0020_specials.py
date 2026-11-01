# -*- coding: utf-8 -*-
"""Add tracked_specials to scoring_rules, specials to scores."""
import json
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

# Backfill data for existing builtin rules keyed by exact name.
_KM = [{"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
       {"key": "miss", "label": "M",    "track": True, "tiebreak": False}]
_XM = [{"key": "x",    "label": "X",    "track": True, "tiebreak": True},
       {"key": "miss", "label": "M",    "track": True, "tiebreak": False}]
_K12M = [{"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
         {"key": "x",    "label": "12",   "track": True, "tiebreak": False},
         {"key": "miss", "label": "M",    "track": True, "tiebreak": False}]
_KXM  = [{"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
         {"key": "x",    "label": "X",    "track": True, "tiebreak": False},
         {"key": "miss", "label": "M",    "track": True, "tiebreak": False}]

_BACKFILL = {
    "IBO 3D Standard":                     _KXM,
    "ASA 3D":                              _K12M,
    "WA 3D":                               _XM,
    "3D Hunter (IBO)":                     _KM,
    "3D Standard 3-Pfeil":                 _KM,
    "Feldbogen IFAA (bekannte Entfernung)": _XM,
    "Feldbogen IFAA (unbekannte Entfernung)": _XM,
    "WA Halle 18m":                        _XM,
    "Blasrohr Standard":                   _XM,
    "DBSV 3D-Waldrunde":                   _KM,
    "DBSV 3D-Jagdrunde":                   _KM,
    "IBO 3D mit 12-Ring":                  _K12M,
    "NFAA 3D":                             _KM,
    "WA Halle 25m":                        _XM,
}


def upgrade():
    op.add_column("scoring_rules",
                  sa.Column("tracked_specials", sa.JSON(), server_default="'[]'"))
    op.add_column("scores",
                  sa.Column("specials", sa.JSON(), server_default="'{}'"))

    conn = op.get_bind()
    for name, specials in _BACKFILL.items():
        conn.execute(
            sa.text("UPDATE scoring_rules SET tracked_specials = :val WHERE name = :name"),
            {"val": json.dumps(specials, ensure_ascii=False), "name": name},
        )


def downgrade():
    op.drop_column("scoring_rules", "tracked_specials")
    op.drop_column("scores", "specials")

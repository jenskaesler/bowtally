# -*- coding: utf-8 -*-
"""Turnierregeln und Teilnahmebedingungen: von scoring_rules in app_settings (global) verschieben."""
from alembic import op
import sqlalchemy as sa

revision = "0028_global_rule_texts"
down_revision = "0027_internal_notes"
branch_labels = None
depends_on = None

# Setting-Key -> frühere Spalte von scoring_rules
TEXTS = {"tournament_rules_text": "tournament_rules",
         "participation_terms_text": "participation_conditions"}


def upgrade():
    conn = op.get_bind()
    default_id = conn.execute(sa.text(
        "SELECT value FROM app_settings WHERE key = 'default_scoring_rule_id'")).scalar()
    for key, column in TEXTS.items():
        # Text des Standard-Regelwerks, sonst der erste nicht-leere
        text = conn.execute(sa.text(
            f"SELECT {column} FROM scoring_rules WHERE COALESCE({column}, '') <> '' "
            "ORDER BY (id = :d) DESC, id LIMIT 1"), {"d": int(default_id or 0)}).scalar() or ""
        if conn.execute(sa.text("SELECT 1 FROM app_settings WHERE key = :k"), {"k": key}).scalar():
            conn.execute(sa.text("UPDATE app_settings SET value = :v WHERE key = :k"),
                         {"k": key, "v": text})
        else:
            conn.execute(sa.text(
                "INSERT INTO app_settings (key, value, category, value_type, description) "
                "VALUES (:k, :v, 'internal', 'string', :d)"),
                {"k": key, "v": text, "d": "Globaler Text für den Turnierregeln-Aushang und die Ausschreibung"})
    # Natives DROP COLUMN (SQLite >= 3.35): batch würde scoring_rules neu anlegen, was an den Fremdschlüsseln scheitert.
    for column in TEXTS.values():
        op.execute(f"ALTER TABLE scoring_rules DROP COLUMN {column}")


def downgrade():
    with op.batch_alter_table("scoring_rules") as batch_op:
        batch_op.add_column(sa.Column("tournament_rules", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("participation_conditions", sa.Text(), nullable=True))

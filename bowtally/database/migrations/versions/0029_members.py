# -*- coding: utf-8 -*-
"""Helfer-Stammdaten werden zu Mitglieder-Stammdaten (einmalig, nicht rückgängig zu machen)

Revision ID: 0029_members
Revises: 0028_global_rule_texts
Create Date: 2026-11-17
"""
import sqlalchemy as sa
from alembic import op

from bowtally.database.member_migration import helpers_to_members

revision = "0029_members"
down_revision = "0028_global_rule_texts"
branch_labels = None
depends_on = None

MEMBER_COLUMNS = ["id", "member_number", "first_name", "last_name", "phone", "email", "notes",
                  "active", "is_tournament_helper"]
ASSIGNMENT_COLUMNS = ["id", "tournament_id", "member_id", "task", "time_from", "time_to",
                      "confirmed"]


def _bool(default: bool) -> dict:
    return dict(nullable=False, server_default="1" if default else "0")


def upgrade():
    conn = op.get_bind()
    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_number", sa.Text(), nullable=False, unique=True),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("street", sa.Text()),
        sa.Column("postal_code", sa.Text()),
        sa.Column("city", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("member_since", sa.Date()),
        sa.Column("cancelled_on", sa.Date()),
        sa.Column("birthday", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("info_by_mail", sa.Boolean(), **_bool(False)),
        sa.Column("is_tournament_helper", sa.Boolean(), **_bool(False)),
        sa.Column("active", sa.Boolean(), **_bool(True)),
        sa.Column("consent_given", sa.Boolean(), **_bool(False)),
        sa.Column("consent_date", sa.Date()),
        sa.Column("account_holder", sa.Text()),
        sa.Column("iban", sa.Text()),
        sa.Column("bic", sa.Text()),
        sa.Column("bank_name", sa.Text()),
        sa.Column("sepa_direct_debit", sa.Boolean(), **_bool(False)),
        sa.Column("sepa_mandate_ref", sa.Text()),
        sa.Column("sepa_mandate_date", sa.Date()),
    )
    op.create_table(
        "tournament_helpers_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.Integer(), sa.ForeignKey("members.id", ondelete="CASCADE")),
        sa.Column("first_name", sa.Text()),
        sa.Column("last_name", sa.Text()),
        sa.Column("phone", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("task", sa.Text()),
        sa.Column("time_from", sa.Text()),
        sa.Column("time_to", sa.Text()),
        sa.Column("confirmed", sa.Boolean(), **_bool(False)),
        sa.UniqueConstraint("tournament_id", "member_id", name="uq_tournament_helpers_member"),
    )

    def rows(sql):
        return [dict(r) for r in conn.execute(sa.text(sql)).mappings()]

    members, assignments = helpers_to_members(
        rows("SELECT * FROM helpers"), rows("SELECT * FROM tournament_helpers"))
    for table, columns, data in (("members", MEMBER_COLUMNS, members),
                                 ("tournament_helpers_new", ASSIGNMENT_COLUMNS, assignments)):
        if data:
            conn.execute(sa.text(f"INSERT INTO {table} ({', '.join(columns)}) "
                                 f"VALUES ({', '.join(':' + c for c in columns)})"), data)

    op.drop_table("tournament_helpers")
    op.drop_table("helpers")
    op.rename_table("tournament_helpers_new", "tournament_helpers")

    op.create_table(
        "member_helper_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("member_id", sa.Integer(),
                  sa.ForeignKey("members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="SET NULL")),
        sa.Column("tournament_name", sa.Text(), nullable=False),
        sa.Column("date", sa.Date()),
        sa.Column("role", sa.Text()),
        sa.Column("hours", sa.Float()),
        sa.UniqueConstraint("member_id", "tournament_id", name="uq_member_history_tournament"),
    )


def downgrade():
    """Nur für Entwicklung/Tests, verlustbehaftet: Bankdaten, Historie, Mitglieder ohne Helfer-Flag
    und manuelle Turnier-Helfer gehen verloren. Echter Schutz ist die Kopie vor der Migration."""
    conn = op.get_bind()
    op.drop_table("member_helper_history")
    op.create_table(
        "helpers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=False),
        sa.Column("phone", sa.Text()),
        sa.Column("email", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("active", sa.Boolean(), **_bool(True)),
    )
    op.create_table(
        "tournament_helpers_old",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournament_id", sa.Integer(),
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("helper_id", sa.Integer(),
                  sa.ForeignKey("helpers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("task", sa.Text()),
        sa.Column("time_from", sa.Text()),
        sa.Column("time_to", sa.Text()),
        sa.Column("confirmed", sa.Boolean(), **_bool(False)),
    )
    conn.execute(sa.text(
        "INSERT INTO helpers (id, first_name, last_name, phone, email, notes, active) "
        "SELECT id, first_name, last_name, phone, email, notes, active FROM members "
        "WHERE is_tournament_helper = 1"))
    conn.execute(sa.text(
        "INSERT INTO tournament_helpers_old (id, tournament_id, helper_id, task, time_from, "
        "time_to, confirmed) SELECT id, tournament_id, member_id, task, time_from, time_to, "
        "confirmed FROM tournament_helpers WHERE member_id IN (SELECT id FROM helpers)"))
    op.drop_table("tournament_helpers")
    op.drop_table("members")
    op.rename_table("tournament_helpers_old", "tournament_helpers")

# -*- coding: utf-8 -*-
"""Tournament lifecycle: phases, entry fees, participant status, transition log

Revision ID: 0003_tournament_lifecycle
Revises: 0002_dark_mode
Create Date: 2026-10-19
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0003_tournament_lifecycle"
down_revision = "0002_dark_mode"
branch_labels = None
depends_on = None

NEW_SETTINGS = ["announcement_payment_hint", "announcement_group_hint", "default_legal_notes",
                "print_announcement_logo_footer", "last_active_tournament_id"]
STATUS_TO_PHASE = {"draft": "announcement", "active": "shooting", "closed": "closed"}


def upgrade():
    from bowtally.database.seed import (DEFAULT_ENTRY_FEES, DEFAULT_SETTINGS,
                                        TOURNAMENT_PHASES)
    phases = op.create_table(
        "tournament_phases",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("label", sa.Text),
        sa.Column("sort_order", sa.Integer),
        sa.Column("description", sa.Text),
    )
    op.bulk_insert(phases, [{"key": k, "label": label, "sort_order": o, "description": d}
                            for k, label, o, d in TOURNAMENT_PHASES])

    op.create_table(
        "entry_fees",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tournament_id", sa.Integer,
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE")),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("sort_order", sa.Integer, server_default="0"),
    )

    with op.batch_alter_table("tournaments") as b:
        b.add_column(sa.Column("phase", sa.Text, nullable=False, server_default="announcement"))
        b.add_column(sa.Column("phase_changed_at", sa.DateTime))
        b.add_column(sa.Column("registration_deadline", sa.Date))
        b.add_column(sa.Column("max_participants", sa.Integer))
        b.add_column(sa.Column("checkin_start_time", sa.Text))
        b.add_column(sa.Column("shooting_start_time", sa.Text))
        b.add_column(sa.Column("practice_allowed", sa.Boolean, server_default=sa.true()))
        b.add_column(sa.Column("practice_location", sa.Text))
        for col in ("bank_account_holder", "bank_iban", "bank_bic", "bank_reference_template",
                    "contact_name", "contact_phone", "contact_email", "legal_notes",
                    "additional_info"):
            b.add_column(sa.Column(col, sa.Text))
        b.add_column(sa.Column("checklist_state", sa.JSON))
        b.add_column(sa.Column("announced_at", sa.DateTime))
        b.add_column(sa.Column("announcement_generated_at", sa.DateTime))
        b.add_column(sa.Column("content_changed_at", sa.DateTime))
        b.add_column(sa.Column("results_generated_at", sa.DateTime))
        b.create_foreign_key("fk_tournaments_phase", "tournament_phases", ["phase"], ["key"])

    with op.batch_alter_table("tournament_participants") as b:
        b.add_column(sa.Column("registration_status", sa.Text, nullable=False,
                               server_default="registered"))
        b.add_column(sa.Column("payment_status", sa.Text, nullable=False,
                               server_default="unpaid"))
        b.add_column(sa.Column("entry_fee_id", sa.Integer))
        b.add_column(sa.Column("fee_amount_paid", sa.Float))
        b.add_column(sa.Column("payment_date", sa.Date))
        b.add_column(sa.Column("payment_notes", sa.Text))
        b.add_column(sa.Column("registration_date", sa.Date))
        b.add_column(sa.Column("confirmation_date", sa.Date))
        b.add_column(sa.Column("checkin_time", sa.DateTime))
        b.add_column(sa.Column("notes", sa.Text))
        b.create_foreign_key("fk_participants_entry_fee", "entry_fees", ["entry_fee_id"], ["id"])
        b.create_check_constraint(
            "ck_participants_registration",
            "registration_status IN ('registered', 'confirmed', 'checked_in', 'dns', 'dnf', "
            "'dsq', 'withdrawn')")
        b.create_check_constraint("ck_participants_payment",
                                  "payment_status IN ('unpaid', 'pending', 'paid')")

    op.create_table(
        "phase_transition_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tournament_id", sa.Integer,
                  sa.ForeignKey("tournaments.id", ondelete="CASCADE")),
        sa.Column("from_phase", sa.Text),
        sa.Column("to_phase", sa.Text),
        sa.Column("transitioned_at", sa.DateTime),
        sa.Column("forced", sa.Boolean, server_default=sa.false()),
        sa.Column("warnings_at_transition", sa.JSON),
    )

    conn = op.get_bind()
    # existing tournaments: phase from the old status, registration date from registered_at
    for status, phase in STATUS_TO_PHASE.items():
        conn.execute(sa.text("UPDATE tournaments SET phase = :p WHERE status = :s"),
                     {"p": phase, "s": status})
    conn.execute(sa.text("UPDATE tournament_participants SET registration_date = "
                         "date(registered_at) WHERE registration_date IS NULL"))

    # Fresh database: app_settings is empty and seed.py inserts settings + fee templates.
    if not conn.execute(sa.text("SELECT COUNT(*) FROM app_settings")).scalar():
        return
    now = datetime.now().isoformat(sep=" ")
    existing = set(conn.execute(sa.text("SELECT key FROM app_settings")).scalars())
    for key, value, category, value_type, description in DEFAULT_SETTINGS:
        if key in NEW_SETTINGS and key not in existing:
            conn.execute(sa.text(
                "INSERT INTO app_settings (key, value, category, value_type, description, "
                "updated_at) VALUES (:k, :v, :c, :t, :d, :u)"),
                {"k": key, "v": value, "c": category, "t": value_type, "d": description,
                 "u": now})
    for i, (name, amount) in enumerate(DEFAULT_ENTRY_FEES, start=1):
        conn.execute(sa.text("INSERT INTO entry_fees (tournament_id, name, amount, sort_order) "
                             "VALUES (NULL, :n, :a, :o)"), {"n": name, "a": amount, "o": i})


def downgrade():
    op.drop_table("phase_transition_log")
    with op.batch_alter_table("tournament_participants") as b:
        b.drop_constraint("ck_participants_payment", type_="check")
        b.drop_constraint("ck_participants_registration", type_="check")
        b.drop_constraint("fk_participants_entry_fee", type_="foreignkey")
        for col in ("registration_status", "payment_status", "entry_fee_id", "fee_amount_paid",
                    "payment_date", "payment_notes", "registration_date", "confirmation_date",
                    "checkin_time", "notes"):
            b.drop_column(col)
    with op.batch_alter_table("tournaments") as b:
        b.drop_constraint("fk_tournaments_phase", type_="foreignkey")
        for col in ("phase", "phase_changed_at", "registration_deadline", "max_participants",
                    "checkin_start_time", "shooting_start_time", "practice_allowed",
                    "practice_location", "bank_account_holder", "bank_iban", "bank_bic",
                    "bank_reference_template", "contact_name", "contact_phone",
                    "contact_email", "legal_notes", "additional_info", "checklist_state",
                    "announced_at", "announcement_generated_at", "content_changed_at",
                    "results_generated_at"):
            b.drop_column(col)
    op.drop_table("entry_fees")
    op.drop_table("tournament_phases")

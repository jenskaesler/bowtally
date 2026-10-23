# -*- coding: utf-8 -*-
"""E-Mail-Vorlagen in app_settings

Revision ID: 0008_email_templates
Revises: 0007_contacts_phone_email
Create Date: 2026-10-24
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_email_templates"
down_revision = "0007_contacts_phone_email"
branch_labels = None
depends_on = None

_ROWS = [
    ("email_reg_subject", "Anmeldebestätigung – {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Anmeldebestätigung"),
    ("email_reg_body",
     "Hallo {name},\n\ndeine Anmeldung zum Turnier {turniername} am {datum} wurde erfolgreich "
     "registriert.\n\nKlasse: {klasse}\nVerein: {verein}\n\nBis dahin!\nDein Team",
     "email", "string", "E-Mail-Vorlage: Text Anmeldebestätigung"),
    ("email_payment_subject", "Zahlungserinnerung – {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Zahlungserinnerung"),
    ("email_payment_body",
     "Hallo {name},\n\nfür deine Anmeldung zum Turnier {turniername} am {datum} liegt noch "
     "eine offene Zahlung vor. Bitte überweise das Startgeld rechtzeitig.\n\nBis dahin!\nDein Team",
     "email", "string", "E-Mail-Vorlage: Text Zahlungserinnerung"),
    ("email_docs_subject", "Startunterlagen – {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Startunterlagen"),
    ("email_docs_body",
     "Hallo {name},\n\nanbei erhältst du die Startunterlagen für das Turnier {turniername} am "
     "{datum}.\n\nKlasse: {klasse}\nVerein: {verein}\n\nBis dahin!\nDein Team",
     "email", "string", "E-Mail-Vorlage: Text Startunterlagen"),
    ("email_results_subject", "Ergebnisse – {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Ergebnisversand"),
    ("email_results_body",
     "Hallo {name},\n\nhier sind die Ergebnisse des Turniers {turniername} vom {datum}.\n\n"
     "Klasse: {klasse}\nVerein: {verein}\n\nBis zum nächsten Turnier!\nDein Team",
     "email", "string", "E-Mail-Vorlage: Text Ergebnisversand"),
    ("email_waitlist_subject", "Nachrücken – {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Wartelisten-Nachrücker"),
    ("email_waitlist_body",
     "Hallo {name},\n\nes ist ein Platz frei geworden! Du kannst für das Turnier {turniername} "
     "am {datum} nachrücken.\n\nKlasse: {klasse}\nVerein: {verein}\n\nBitte melde dich schnell "
     "zurück!\nDein Team",
     "email", "string", "E-Mail-Vorlage: Text Wartelisten-Nachrücker"),
    ("email_helper_subject", "Helfer-Bestätigung – {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Helfer-Bestätigung"),
    ("email_helper_body",
     "Hallo {name},\n\nvielen Dank, dass du beim Turnier {turniername} am {datum} als Helfer "
     "dabei bist! Wir freuen uns auf dich.\n\nDein Team",
     "email", "string", "E-Mail-Vorlage: Text Helfer-Bestätigung"),
]


def upgrade():
    tbl = sa.table("app_settings",
                   sa.column("key"), sa.column("value"), sa.column("category"),
                   sa.column("value_type"), sa.column("description"))
    op.bulk_insert(tbl, [{"key": k, "value": v, "category": c, "value_type": t, "description": d}
                         for k, v, c, t, d in _ROWS])


def downgrade():
    conn = op.get_bind()
    for k, *_ in _ROWS:
        conn.execute(sa.text("DELETE FROM app_settings WHERE key = :k"), {"k": k})

# -*- coding: utf-8 -*-
"""Initial data set: settings, builtin scoring rules and bow classes."""
from sqlalchemy.orm import Session

from bowtally.database.models import AppSetting, BowClass, ClubProfile, EntryFee, ScoringRule

# (key, value, category, value_type, description)
DEFAULT_SETTINGS = [
    ("color_primary", "#00357D", "ui", "color", "Primärfarbe (Header, Primary Buttons)"),
    ("color_secondary", "#0258CF", "ui", "color", "Sekundärfarbe (Links, Hover)"),
    ("color_accent", "#e51e1e", "ui", "color", "Akzentfarbe (Warnungen, Delete)"),
    ("color_text_secondary", "#777777", "ui", "color", "Sekundärer Text"),
    ("color_background", "#F4F6F9", "ui", "color", "App-Hintergrund"),
    ("color_surface", "#FFFFFF", "ui", "color", "Karten und Dialoge"),
    ("color_border", "#D0D7E0", "ui", "color", "Rahmenlinien"),
    ("color_text", "#1A1F26", "ui", "color", "Textfarbe"),
    ("color_dark_background", "#0E1116", "ui", "color", "App-Hintergrund (Dunkel)"),
    ("color_dark_surface", "#161B22", "ui", "color", "Karten und Dialoge (Dunkel)"),
    ("color_dark_border", "#2A313B", "ui", "color", "Rahmenlinien (Dunkel)"),
    ("color_dark_text", "#E6EAF0", "ui", "color", "Textfarbe (Dunkel)"),
    ("color_dark_text_secondary", "#8D96A3", "ui", "color", "Sekundärer Text (Dunkel)"),
    ("ui_theme_mode", "system", "ui", "string", "Darstellung: system, light oder dark"),
    ("font_family", "Open Sans", "ui", "string", "Schriftart (Fallback: Segoe UI, Arial)"),
    ("print_paper_size", "A4", "print", "string", "Papiergröße für PDF/Druck"),
    ("print_orientation", "portrait", "print", "string", "portrait oder landscape"),
    ("print_show_logo", "true", "print", "boolean", "Vereinslogo in Ergebnisliste anzeigen"),
    ("print_show_scores_per_target", "true", "print", "boolean",
     "Einzelwertungen je Scheibe drucken"),
    ("result_tiebreak_mode", "most_top_scores", "behavior", "string",
     "Tie-Break-Logik: most_top_scores oder total_highest"),
    ("result_auto_rank", "true", "behavior", "boolean",
     "Rang automatisch neu berechnen bei Änderung"),
    ("ui_language", "de", "ui", "string", "Sprache (Vorbereitung für i18n, aktuell nur de)"),
    ("announcement_payment_hint",
     "Überweisungen ohne vorherige Anmeldung werden nicht als Startgeld anerkannt und gehen "
     "als Spende an den Verein.", "templates", "string",
     "Ausschreibung: Hinweis zur Überweisung"),
    ("announcement_group_hint",
     "Die Gruppeneinteilung erfolgt selbstständig durch die Teilnehmer beim Einschreiben.",
     "templates", "string", "Ausschreibung: Hinweis zur Gruppeneinteilung"),
    ("default_legal_notes",
     "Die Teilnahme erfolgt auf eigene Gefahr und eigenes Risiko.\n"
     "Jeder Schütze haftet für seinen Schuss.\n"
     "Für Sach- und Personenschäden übernimmt der Veranstalter keine Haftung.\n"
     "Eltern haften für ihre Kinder.\n"
     "Aus sicherheitstechnischen Gründen ist die Teilnahme von Zuschauern am Turniergelände "
     "leider nicht möglich.", "templates", "string",
     "Vorbelegung „Wichtige Hinweise“ für neue Turniere (eine Zeile je Hinweis)"),
    ("print_announcement_logo_footer", "true", "print", "boolean",
     "Vereinslogo klein am Ende der Ausschreibung wiederholen"),
    ("last_active_tournament_id", "", "internal", "string",
     "Zuletzt geöffnetes Turnier (wird beim Start wiederhergestellt)"),
    # email templates
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
     "Hallo {name},\n\nhier sind deine Ergebnisse des Turniers {turniername} vom {datum}.\n\n"
     "Klasse: {klasse}\nPlatz: {platz}\nPunkte: {punkte}\nVerein: {verein}\n\n"
     "Bis zum nächsten Turnier!\nDein Team",
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
    # behavior
    ("waitlist_mode", "block", "behavior", "string",
     "Warteliste: auto (automatisch) oder block (sperren)"),
]

# Reference data, inserted by migration 0003 (key, label, sort_order, description)
TOURNAMENT_PHASES = [
    ("draft", "Entwurf", 1,
     "Das Turnier wird angelegt. Alle Turnierdaten können frei bearbeitet werden. "
     "Wechsle zur Ausschreibung, wenn alles fertig ist."),
    ("announcement", "Ausschreibung", 2,
     "Das Turnier wird geplant und ausgeschrieben. Lege Kontakt- und Bankdaten sowie die "
     "Startgebühren fest und erstelle das Ausschreibungs-PDF zum Versenden."),
    ("preparation", "Vorbereitung", 3,
     "Die Ausschreibung ist versendet. Jetzt werden Parcours und Helfer geplant und die "
     "Anmeldung vorbereitet."),
    ("registration", "Anmeldung", 4,
     "Anmeldungen gehen ein. Erfasse Teilnehmer, bestätige Anmeldungen und verbuche "
     "Zahlungseingänge."),
    ("checkin", "Einschreibung", 5,
     "Turniertag: Die Teilnehmer melden sich vor Ort an. Checke sie in der Einschreibe-Ansicht "
     "ein und kläre offene Zahlungen."),
    ("shooting", "Schießen", 6,
     "Der Parcours läuft. Trage die Ergebnisse der Schießkarten ein und behalte den "
     "Fortschritt je Klasse im Blick."),
    ("scoring", "Auswertung", 7,
     "Alle Gruppen sind zurück. Prüfe die Ergebnisse auf Vollständigkeit, erstelle die "
     "Ergebnisliste und bereite die Siegerehrung vor."),
    ("closed", "Abgeschlossen", 8,
     "Das Turnier ist beendet. Ergebnisse und Teilnehmerdaten sind gesperrt und bleiben "
     "für Auswertungen und Exporte erhalten."),
]

# (name, amount) templates with tournament_id = NULL
DEFAULT_ENTRY_FEES = [("Erwachsene", 20.00), ("Schüler und Jugendliche", 10.00)]

DEFAULT_SCORING_RULES = [
    {
        "name": "IBO 3D Standard",
        "description": "IBO 3D-Wertung, ein Pfeil je Scheibe.",
        "ring_values": [
            {"zone": "Vital innen", "points": 20},
            {"zone": "Vital außen", "points": 10},
            {"zone": "Körper", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 1,
        "allow_retry_shot": False,
        "rules_json": {"tiebreak": "most_top_scores"},
    },
    {
        "name": "ASA 3D",
        "description": "ASA 3D-Wertung mit Doppelring.",
        "ring_values": [
            {"zone": "Doppelring rot", "points": 12},
            {"zone": "Vital innen", "points": 10},
            {"zone": "Vital außen", "points": 8},
            {"zone": "Körper", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 1,
        "allow_retry_shot": False,
        "rules_json": {"tiebreak": "most_top_scores"},
    },
    {
        "name": "WA 3D",
        "description": "World Archery 3D, zwei Pfeile je Scheibe.",
        "ring_values": [
            {"zone": "X-Ring", "points": 10},
            {"zone": "Ring 10", "points": 10},
            {"zone": "Ring 8", "points": 8},
            {"zone": "Ring 5", "points": 5},
            {"zone": "Ring 3", "points": 3},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 2,
        "allow_retry_shot": True,
        "rules_json": {
            "tiebreak": "most_top_scores",
            "shot2_penalty": True,
            "note": "1. Schuss Vital: volle Punkte. 2. Schuss nötig: reduzierte Punkte "
                    "gemäß Trefferzone.",
        },
    },
    {
        "name": "3D Hunter (IBO)",
        "description": "Hunterrunde: 1 Pfeil je Tier, reduzierte Wertung.",
        "ring_values": [
            {"zone": "Vital innen", "points": 11},
            {"zone": "Vital außen", "points": 10},
            {"zone": "Körper", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 1,
        "allow_retry_shot": False,
        "rules_json": {"tiebreak": "most_top_scores",
                       "note": "Typische Hunterrunde: 1 Pfeil, max. 11 Punkte je Tier"},
    },
    {
        "name": "3D Standard 3-Pfeil",
        "description": "Klassische 3D-Runde mit 3 Pfeilen je Tier.",
        "ring_values": [
            {"zone": "Vital innen 1. Pfeil", "points": 20},
            {"zone": "Vital innen 2. Pfeil", "points": 16},
            {"zone": "Vital innen 3. Pfeil", "points": 14},
            {"zone": "Vital außen 1. Pfeil", "points": 10},
            {"zone": "Vital außen 2. Pfeil", "points": 8},
            {"zone": "Vital außen 3. Pfeil", "points": 4},
            {"zone": "Körper", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 3,
        "allow_retry_shot": True,
        "rules_json": {"tiebreak": "most_top_scores", "shot_penalty": True,
                       "note": "Volle Punkte nur für 1. Pfeil in Vitalzone."},
    },
    {
        "name": "Feldbogen IFAA (bekannte Entfernung)",
        "description": "IFAA Feldturnier, Runde mit bekannten Entfernungen.",
        "ring_values": [
            {"zone": "X-Ring", "points": 5},
            {"zone": "Innenring", "points": 5},
            {"zone": "Außenring", "points": 3},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 3,
        "allow_retry_shot": True,
        "rules_json": {"tiebreak": "most_top_scores", "distance_type": "known",
                       "note": "3 Pfeile je Scheibe. Bekannte Entfernung."},
    },
    {
        "name": "Feldbogen IFAA (unbekannte Entfernung)",
        "description": "IFAA Feldturnier, Runde mit unbekannten Entfernungen.",
        "ring_values": [
            {"zone": "X-Ring", "points": 5},
            {"zone": "Innenring", "points": 5},
            {"zone": "Außenring", "points": 3},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 3,
        "allow_retry_shot": True,
        "rules_json": {"tiebreak": "most_top_scores", "distance_type": "unknown",
                       "note": "3 Pfeile je Scheibe. Unbekannte Entfernung."},
    },
    {
        "name": "WA Halle 18m",
        "description": "World Archery Indoor, 18 Meter, 10-Ring-Wertung.",
        "ring_values": [
            {"zone": "X (10 innen)", "points": 10},
            {"zone": "10", "points": 10},
            {"zone": "9", "points": 9},
            {"zone": "8", "points": 8},
            {"zone": "7", "points": 7},
            {"zone": "6", "points": 6},
            {"zone": "5", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 3,
        "allow_retry_shot": False,
        "rules_json": {"tiebreak": "most_x_rings",
                       "note": "3 Pfeile je Scheibe, 10 Scheiben je Runde."},
    },
    {
        "name": "Blasrohr Standard",
        "description": "Standard-Wertung für Blasrohrturnier.",
        "ring_values": [
            {"zone": "Innenring", "points": 10},
            {"zone": "Außenring", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 1,
        "allow_retry_shot": False,
        "rules_json": {"tiebreak": "most_top_scores"},
    },
    {
        "name": "DBSV 3D-Waldrunde",
        "description": "Deutsche Waldrunde nach DBSV-Regelwerk. Bis zu 3 Pfeile je Tier.",
        "ring_values": [
            {"zone": "Innere Killzone (1. Pfeil)", "points": 15},
            {"zone": "Äußere Killzone (1. Pfeil)", "points": 10},
            {"zone": "Körpertreffer (1. Pfeil)", "points": 5},
            {"zone": "Innere Killzone (2. Pfeil)", "points": 12},
            {"zone": "Äußere Killzone (2. Pfeil)", "points": 8},
            {"zone": "Körpertreffer (2. Pfeil)", "points": 4},
            {"zone": "Innere Killzone (3. Pfeil)", "points": 10},
            {"zone": "Äußere Killzone (3. Pfeil)", "points": 6},
            {"zone": "Körpertreffer (3. Pfeil)", "points": 3},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 3,
        "allow_retry_shot": True,
        "rules_json": {
            "tiebreak": "most_top_scores",
            "scoring_note": "Nur erster im Ziel platzierter Pfeil zählt.",
            "source": "DBSV WKO Teil 9, 2024-1, Abschnitt 9.5.3",
        },
    },
    {
        "name": "DBSV 3D-Jagdrunde",
        "description": "Deutsche Jagdrunde nach DBSV-Regelwerk. 1 Pfeil je Tier.",
        "ring_values": [
            {"zone": "Innere Killzone", "points": 15},
            {"zone": "Äußere Killzone", "points": 10},
            {"zone": "Körpertreffer", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 1,
        "allow_retry_shot": False,
        "rules_json": {
            "tiebreak": "most_top_scores",
            "tiebreak_secondary": "most_15_scores",
            "scoring_note": "1 Pfeil je Tier. Schießzeit 1:30 min je Paar.",
            "source": "DBSV WKO Teil 9, 2024-1, Abschnitt 9.6.3 und 9.7.4",
        },
    },
    {
        "name": "IBO 3D mit 12-Ring",
        "description": "IBO-Variante mit zusätzlichem 12-Punkte-Kleinstkreis. 1 Pfeil je Tier.",
        "ring_values": [
            {"zone": "12-Ring (Kleinstkreis)", "points": 12},
            {"zone": "Vital innen (10)", "points": 10},
            {"zone": "Vital außen (8)", "points": 8},
            {"zone": "Körper (5)", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 1,
        "allow_retry_shot": False,
        "rules_json": {
            "tiebreak": "most_top_scores",
            "source": "TTHA Tournament Rules 2023/2024",
        },
    },
    {
        "name": "NFAA 3D",
        "description": "US-amerikanisches NFAA-Regelwerk. 1 Pfeil je Tier.",
        "ring_values": [
            {"zone": "Innenring (10)", "points": 10},
            {"zone": "Außenring (8)", "points": 8},
            {"zone": "Körper (5)", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 1,
        "allow_retry_shot": False,
        "rules_json": {
            "tiebreak": "most_top_scores",
            "source": "NFAA Official Rules",
        },
    },
    {
        "name": "WA Halle 25m",
        "description": "World Archery Indoor, 25 Meter, 10-Ring-Wertung.",
        "ring_values": [
            {"zone": "X (10 innen)", "points": 10},
            {"zone": "10", "points": 10},
            {"zone": "9", "points": 9},
            {"zone": "8", "points": 8},
            {"zone": "7", "points": 7},
            {"zone": "6", "points": 6},
            {"zone": "5", "points": 5},
            {"zone": "Miss", "points": 0},
        ],
        "max_shots_per_target": 3,
        "allow_retry_shot": False,
        "rules_json": {
            "tiebreak": "most_x_rings",
            "source": "World Archery Rules",
        },
    },
]

# (name, abbreviation, age_group)
DEFAULT_BOW_CLASSES = [
    ("Recurve Herren", "RH", "Erwachsene"),
    ("Recurve Damen", "RD", "Erwachsene"),
    ("Recurve Jugend U18", "RJ", "U18"),
    ("Compound Herren", "CH", "Erwachsene"),
    ("Compound Damen", "CD", "Erwachsene"),
    ("Compound Jugend U18", "CJ", "U18"),
    ("Blankbogen Herren", "BH", "Erwachsene"),
    ("Blankbogen Damen", "BD", "Erwachsene"),
    ("Langbogen / Traditionell", "LB", None),
    ("Instinktiv", "IB", None),
]


def run(session: Session) -> None:
    """Insert the initial data set. Caller commits."""
    for key, value, category, value_type, description in DEFAULT_SETTINGS:
        session.add(AppSetting(key=key, value=value, category=category,
                               value_type=value_type, description=description))
    if session.get(ClubProfile, 1) is None:
        session.add(ClubProfile(id=1, country="Deutschland"))
    for rule in DEFAULT_SCORING_RULES:
        session.add(ScoringRule(is_builtin=True, **rule))
    for i, (name, abbr, age) in enumerate(DEFAULT_BOW_CLASSES, start=1):
        session.add(BowClass(name=name, abbreviation=abbr, age_group=age,
                             is_builtin=True, sort_order=i))
    for i, (name, amount) in enumerate(DEFAULT_ENTRY_FEES, start=1):
        session.add(EntryFee(tournament_id=None, name=name, amount=amount, sort_order=i))

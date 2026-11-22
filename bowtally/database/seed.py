# -*- coding: utf-8 -*-
"""Initial data set: settings, builtin scoring rules and bow classes."""
from sqlalchemy import select
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
    # Druckfarben (PDF); beim ersten Anlegen aus der passenden UI-Farbe übernommen, siehe run()
    ("print_color_primary", "#00357D", "print", "color",
     "Hauptfarbe (Überschriften, Tabellenköpfe)"),
    ("print_color_secondary", "#0258CF", "print", "color", "Sekundärfarbe (Zwischentitel)"),
    ("print_color_text_secondary", "#777777", "print", "color", "Sekundärer Text"),
    ("print_color_border", "#D0D7E0", "print", "color", "Rahmenlinien"),
    ("ui_theme_mode", "system", "ui", "string", "Darstellung: system, light oder dark"),
    ("font_family", "Open Sans", "ui", "string", "Schriftart (Open Sans, Inter, Source Sans 3 oder Segoe UI; Fallback: Segoe UI, Arial)"),
    ("print_paper_size", "A4", "print", "string", "Papiergröße für PDF/Druck"),
    ("print_orientation", "portrait", "print", "string", "portrait oder landscape"),
    ("print_show_logo", "true", "print", "boolean", "Vereinslogo in Ergebnisliste anzeigen"),
    ("print_show_scores_per_target", "true", "print", "boolean",
     "Einzelwertungen je Scheibe drucken"),
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
    ("default_scoring_rule_id", "", "internal", "string",
     "Standard-Regelwerk für neue Runden (wird beim Start gesetzt, falls leer)"),
    ("last_active_tournament_id", "", "internal", "string",
     "Zuletzt geöffnetes Turnier (wird beim Start wiederhergestellt)"),
    # E-Mail-Vorlagen. Platzhalter: {name} {first_name} {last_name} {verein} {klasse}
    # {turniername} {datum} {ort} {startnummer} {startgruppe} {startzeit} {anmeldefrist}
    # {platz} {punkte} {verwendungszweck} {iban} {kontakt_name} {kontakt_email}
    # {kontakt_telefon}. Das Vereinslogo wird beim Senden automatisch unter den Text
    # gehängt, wenn unter Einstellungen → Vereinsprofil ein Logo gesetzt ist.
    ("email_reg_subject",
     "Anmeldung bestätigt: {turniername} am {datum}", "email", "string",
     "E-Mail-Vorlage: Betreff Anmeldebestätigung"),
    ("email_reg_body",
     "Hallo {first_name},\n\n"
     "vielen Dank für deine Anmeldung – der Platz ist dir sicher.\n\n"
     "Turnier: {turniername}\n"
     "Datum: {datum}\n"
     "Ort: {ort}\n"
     "Klasse: {klasse}\n"
     "Verein: {verein}\n"
     "Startgruppe: {startgruppe}\n"
     "Startnummer: {startnummer}\n\n"
     "Bitte bringe deine Startunterlagen und Schießausrüstung mit. "
     "Die Einschreibung beginnt vor dem Schießbeginn.\n\n"
     "Bei Fragen erreichst du uns unter {kontakt_email} oder {kontakt_telefon}.\n\n"
     "Wir freuen uns auf dich!\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Anmeldebestätigung"),
    ("email_payment_subject",
     "Zahlungserinnerung: Startgeld für {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Zahlungserinnerung"),
    ("email_payment_body",
     "Hallo {first_name},\n\n"
     "für deine Anmeldung zum Turnier {turniername} am {datum} ist der Startgeld-Eingang "
     "noch nicht bei uns registriert.\n\n"
     "Kontoinhaber: {bank_account_holder}\n"
     "IBAN: {iban}\n"
     "Verwendungszweck: {verwendungszweck}\n\n"
     "Bitte überweise den Betrag zeitnah, damit deine Anmeldung bestätigt werden kann. "
     "Bei Fragen erreichst du uns unter {kontakt_email} oder {kontakt_telefon}.\n\n"
     "Vielen Dank!\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Zahlungserinnerung"),
    ("email_docs_subject",
     "Startunterlagen und Check-in: {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Startunterlagen"),
    ("email_docs_body",
     "Hallo {first_name},\n\n"
     "hier sind die wichtigsten Infos für den Turniertag.\n\n"
     "Turnier: {turniername}\n"
     "Datum: {datum}\n"
     "Treffpunkt: {ort}\n"
     "Einschreibung: ab {checkin_start_time} Uhr\n"
     "Schießbeginn: {shooting_start_time} Uhr\n"
     "Klasse: {klasse}\n"
     "Startgruppe: {startgruppe}\n"
     "Startzeit: {startzeit}\n\n"
     "Bitte sei rechtzeitig zur Einschreibung da und bringe deine Ausrüstung mit.\n\n"
     "Wir freuen uns auf einen schönen Turniertag!\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Startunterlagen"),
    ("email_results_subject",
     "Ergebnisse: {turniername} – Platz {platz}", "email", "string",
     "E-Mail-Vorlage: Betreff Ergebnisversand"),
    ("email_results_body",
     "Hallo {first_name},\n\n"
     "vielen Dank für deine Teilnahme am {turniername} am {datum}.\n\n"
     "Dein Ergebnis:\n"
     "Klasse: {klasse}\n"
     "Platz: {platz}\n"
     "Punkte: {punkte}\n\n"
     "Die vollständige Ergebnisliste findest du im Anhang. "
     "Wir freuen uns auf das nächste Turnier mit dir!\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Ergebnisversand"),
    ("email_waitlist_subject",
     "Platz frei geworden: {turniername}", "email", "string",
     "E-Mail-Vorlage: Betreff Wartelisten-Nachrücker"),
    ("email_waitlist_body",
     "Hallo {first_name},\n\n"
     "für das Turnier {turniername} am {datum} ist ein Platz frei geworden.\n"
     "Du stehst auf der Warteliste und kannst jetzt nachrücken.\n\n"
     "Klasse: {klasse}\n"
     "Verein: {verein}\n\n"
     "Bitte bestätige kurz per E-Mail an {kontakt_email}, ob du teilnimmst – "
     "sonst vergeben wir den Platz weiter.\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Wartelisten-Nachrücker"),
    ("email_helper_subject",
     "Helfer-Bestätigung: {turniername} am {datum}", "email", "string",
     "E-Mail-Vorlage: Betreff Helfer-Bestätigung"),
    ("email_helper_body",
     "Hallo {first_name},\n\n"
     "vielen Dank, dass du uns beim {turniername} am {datum} in {ort} unterstützt.\n\n"
     "Einschreibung: ab {checkin_start_time} Uhr\n"
     "Schießbeginn: {shooting_start_time} Uhr\n\n"
     "Bitte melde dich vor Beginn bei {kontakt_name} ({kontakt_telefon}). "
     "Wir freuen uns auf deine Unterstützung!\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Helfer-Bestätigung"),
    ("email_data_request_subject",
     "Auskunft über deine gespeicherten Daten – {vereinsname}", "email", "string",
     "E-Mail-Vorlage: Betreff Datenauskunft"),
    ("email_data_request_body",
     "Hallo {first_name},\n\n"
     "auf deine Anfrage teilen wir dir mit, welche personenbezogenen Daten {vereinsname} "
     "über dich gespeichert hat (Auskunft nach Art. 15 DSGVO):\n\n"
     "{daten}\n\n"
     "Zu deiner Sicherheit ist die IBAN bis auf die letzten vier Stellen unkenntlich gemacht.\n\n"
     "Du kannst jederzeit die Berichtigung oder Löschung deiner Daten verlangen. "
     "Melde dich dazu einfach bei uns.\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Datenauskunft"),
    # WhatsApp templates (wa.me click-to-chat): short texts, no subject, no attachment;
    # same placeholders as the e-mail templates except {logo}
    ("whatsapp_target", "app", "whatsapp", "string",
     "WhatsApp öffnen mit: app (wa.me, WhatsApp-App) oder web (WhatsApp Web im Browser)"),
    ("whatsapp_reg_body",
     "Hallo {first_name}, deine Anmeldung zum {turniername} am {datum} in {ort} ist "
     "bestätigt. Klasse: {klasse}, Startgruppe: {startgruppe}, Startnummer: {startnummer}. "
     "Wir freuen uns auf dich! Viele Grüße, {kontakt_name} ({vereinsname})",
     "whatsapp", "string", "WhatsApp-Vorlage: Anmeldebestätigung"),
    ("whatsapp_payment_body",
     "Hallo {first_name}, für deine Anmeldung zum {turniername} am {datum} ist das Startgeld "
     "noch nicht bei uns eingegangen. Kontoinhaber: {bank_account_holder}, IBAN: {iban}, "
     "Verwendungszweck: {verwendungszweck}. Vielen Dank! Viele Grüße, {kontakt_name} "
     "({vereinsname})",
     "whatsapp", "string", "WhatsApp-Vorlage: Zahlungserinnerung"),
    ("whatsapp_docs_body",
     "Hallo {first_name}, die Infos für den {turniername} am {datum}: Treffpunkt {ort}, "
     "Einschreibung ab {checkin_start_time} Uhr, Schießbeginn {shooting_start_time} Uhr. "
     "Klasse: {klasse}, Startgruppe: {startgruppe}, Startzeit: {startzeit}. Bis bald! "
     "Viele Grüße, {kontakt_name} ({vereinsname})",
     "whatsapp", "string", "WhatsApp-Vorlage: Startunterlagen"),
    ("whatsapp_waitlist_body",
     "Hallo {first_name}, für den {turniername} am {datum} ist ein Platz frei geworden und du "
     "kannst von der Warteliste nachrücken (Klasse: {klasse}). Gib uns bitte kurz Bescheid, "
     "ob du teilnimmst. Viele Grüße, {kontakt_name} ({vereinsname})",
     "whatsapp", "string", "WhatsApp-Vorlage: Wartelisten-Nachrücker"),
    ("whatsapp_helper_body",
     "Hallo {first_name}, vielen Dank, dass du uns beim {turniername} am {datum} in {ort} "
     "hilfst. Aufgabe: {aufgabe}, von {von} bis {bis} Uhr. Bitte melde dich vor Beginn bei "
     "{kontakt_name} ({kontakt_telefon}). Viele Grüße, {vereinsname}",
     "whatsapp", "string", "WhatsApp-Vorlage: Helfer-Bestätigung"),
    ("whatsapp_data_request_body",
     "Hallo {first_name}, auf deine Anfrage hier die Auskunft, welche Daten {vereinsname} über "
     "dich gespeichert hat (Art. 15 DSGVO):\n\n{daten}\n\nDie IBAN ist bis auf die letzten "
     "vier Stellen unkenntlich gemacht. Du kannst jederzeit Berichtigung oder Löschung "
     "verlangen. Viele Grüße, {kontakt_name}",
     "whatsapp", "string", "WhatsApp-Vorlage: Datenauskunft (Mitglieder)"),
    ("email_tpl_tournament_announce_subject",
     "Turnierankündigung: {turniername} am {datum}", "email", "string",
     "E-Mail-Vorlage: Betreff Turnierankündigung"),
    ("email_tpl_tournament_announce_body",
     "Hallo zusammen,\n\n"
     "wir freuen uns, das Turnier {turniername} am {datum} in {ort} ankündigen zu können.\n\n"
     "Turnier: {turniername}\n"
     "Datum: {datum}\n"
     "Ort: {ort}\n"
     "Klassen: {klassen}\n"
     "Startgeld: {startgeld}\n"
     "Anmeldung bis: {anmeldefrist}\n\n"
     "Alle weiteren Informationen findet ihr in der beigefügten Ausschreibung.\n\n"
     "Mit sportlichen Grüßen\n{kontakt_name}\n{vereinsname}",
     "email", "string", "E-Mail-Vorlage: Text Turnierankündigung"),
    # behavior
    ("waitlist_mode", "auto", "behavior", "string",
     "Warteliste: auto (automatisch) oder block (sperren)"),
    ("participants_per_group", "5", "behavior", "integer",
     "Teilnehmer pro Gruppe (Startgruppen = max. Teilnehmerzahl / Teilnehmer pro Gruppe)"),
    ("update_check_enabled", "true", "system", "boolean",
     "Automatische Update-Prüfung beim Start"),
    ("log_level", "info", "advanced", "string", "Logging-Modus der Logdatei: info, warning, debug"),
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
        "tracked_specials": [
            {"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
            {"key": "x", "label": "X", "track": True, "tiebreak": False},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "x", "label": "X", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "x", "label": "X", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "x", "label": "X", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "x", "label": "X", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
            {"key": "x", "label": "12", "track": True, "tiebreak": False},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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
        "tracked_specials": [
            {"key": "x", "label": "X", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False},
        ],
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


# Tie-break options of built-in rules as the rule books define them (research 2026-11-17):
#  WA/DBSV indoor: most 10s, then 9s; WA 3D: most 11s, then 10s; IBO: most 11s and a shoot-off for
#  the top places (no "Kill"); DBSV Waldrunde: most 15s; IFAA field: shoot-off for every award.
# Rules without a verifiable source (ASA 3D, NFAA 3D, 3D Standard 3-Pfeil, DBSV 3D-Jagdrunde,
# Blasrohr Standard) were removed (migration 0033).
_WA_INDOOR = ("target", {"top_hits": True})
_IBO = ("3d", {"top_hits": True, "shoot_off": True})
_IFAA_FIELD = ("target", {"count_x": True, "shoot_off": True})
BUILTIN_RULE_OPTIONS = {
    "WA Halle 18m": _WA_INDOOR, "WA Halle 25m": _WA_INDOOR,
    "WA 3D": ("3d", {"top_hits": True}),
    "3D Hunter (IBO)": _IBO, "IBO 3D Standard": _IBO, "IBO 3D mit 12-Ring": _IBO,
    "DBSV 3D-Waldrunde": ("3d", {"count_kill": True, "top_hits": True}),
    "Feldbogen IFAA (bekannte Entfernung)": _IFAA_FIELD,
    "Feldbogen IFAA (unbekannte Entfernung)": _IFAA_FIELD,
}


def _zone_type(name: str) -> str:
    lower = name.lower()
    if "killzone" in lower:
        return "kill"
    if lower == "miss":
        return "miss"
    return "x" if lower.startswith("x") else ""


def _sync_builtin_rule(rule: ScoringRule) -> None:
    """Built-in rules are read-only for users, so code is the source of truth at every start."""
    from bowtally.services.scoring_service import rule_options_to_data
    zones = []
    for z in rule.ring_values:
        zone = dict(z)
        if not zone.get("type") and _zone_type(z["zone"]):
            zone["type"] = _zone_type(z["zone"])
        zones.append(zone)
    if zones != rule.ring_values:
        rule.ring_values = zones
    options = BUILTIN_RULE_OPTIONS.get(rule.name)
    if options:
        data = rule_options_to_data(options[0], options[1], zones, rule.tracked_specials or [],
                                    rule.rules_json)
        if data["tracked_specials"] != rule.tracked_specials:
            rule.tracked_specials = data["tracked_specials"]
        if data["rules_json"] != rule.rules_json:
            rule.rules_json = data["rules_json"]


def run(session: Session) -> None:
    """Insert the initial data set. Idempotent: skips what already exists. Caller commits."""
    existing_settings = set(session.scalars(select(AppSetting.key)))
    for key, value, category, value_type, description in DEFAULT_SETTINGS:
        if key not in existing_settings:
            if key.startswith("print_color_"):      # keep the look of existing installs
                ui = session.get(AppSetting, key.removeprefix("print_"))
                value = ui.value if ui is not None and ui.value else value
            session.add(AppSetting(key=key, value=value, category=category,
                                   value_type=value_type, description=description))
    if session.get(ClubProfile, 1) is None:
        session.add(ClubProfile(id=1, country="Deutschland"))
    existing_rules = set(session.scalars(
        select(ScoringRule.name).where(ScoringRule.is_builtin.is_(True))))
    for rule in DEFAULT_SCORING_RULES:
        if rule["name"] not in existing_rules:
            session.add(ScoringRule(is_builtin=True, **rule))
    session.flush()
    for rule in session.scalars(select(ScoringRule).where(ScoringRule.is_builtin.is_(True))):
        _sync_builtin_rule(rule)
    session.flush()
    default = session.get(AppSetting, "default_scoring_rule_id")
    if not default.value or session.get(ScoringRule, int(default.value)) is None:
        default.value = str(session.scalar(
            select(ScoringRule.id).where(ScoringRule.name == "3D Hunter (IBO)")))
    existing_classes = {bc.name for bc in session.scalars(
        select(BowClass).where(BowClass.is_builtin.is_(True)))}
    for i, (name, abbr, age) in enumerate(DEFAULT_BOW_CLASSES, start=1):
        if name not in existing_classes:
            session.add(BowClass(name=name, abbreviation=abbr, age_group=age,
                                 is_builtin=True, sort_order=i))
    if not session.scalar(select(EntryFee).where(EntryFee.tournament_id.is_(None)).limit(1)):
        for i, (name, amount) in enumerate(DEFAULT_ENTRY_FEES, start=1):
            session.add(EntryFee(tournament_id=None, name=name, amount=amount, sort_order=i))

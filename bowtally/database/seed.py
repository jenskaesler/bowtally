# -*- coding: utf-8 -*-
"""Initial data set: settings, builtin scoring rules and bow classes."""
from sqlalchemy.orm import Session

from bowtally.database.models import AppSetting, BowClass, ClubProfile, ScoringRule

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
]

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

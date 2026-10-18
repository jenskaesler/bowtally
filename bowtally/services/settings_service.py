# -*- coding: utf-8 -*-
"""CRUD for app_settings and club_profile."""
from sqlalchemy import select

from bowtally.database.engine import session_scope
from bowtally.database.models import AppSetting, ClubProfile
from bowtally.database.seed import DEFAULT_SETTINGS

KEY_COLOR_PRIMARY = "color_primary"
KEY_COLOR_SECONDARY = "color_secondary"
KEY_COLOR_ACCENT = "color_accent"
KEY_COLOR_TEXT_SECONDARY = "color_text_secondary"
KEY_COLOR_BACKGROUND = "color_background"
KEY_COLOR_SURFACE = "color_surface"
KEY_COLOR_BORDER = "color_border"
KEY_COLOR_TEXT = "color_text"
KEY_COLOR_DARK_BACKGROUND = "color_dark_background"
KEY_COLOR_DARK_SURFACE = "color_dark_surface"
KEY_COLOR_DARK_BORDER = "color_dark_border"
KEY_COLOR_DARK_TEXT = "color_dark_text"
KEY_COLOR_DARK_TEXT_SECONDARY = "color_dark_text_secondary"
KEY_UI_THEME_MODE = "ui_theme_mode"
KEY_FONT_FAMILY = "font_family"
KEY_PRINT_PAPER_SIZE = "print_paper_size"
KEY_PRINT_ORIENTATION = "print_orientation"
KEY_PRINT_SHOW_LOGO = "print_show_logo"
KEY_PRINT_SHOW_SCORES_PER_TARGET = "print_show_scores_per_target"
KEY_RESULT_TIEBREAK_MODE = "result_tiebreak_mode"
KEY_RESULT_AUTO_RANK = "result_auto_rank"
KEY_UI_LANGUAGE = "ui_language"

COLOR_PREFIX = "color_"

# Fixed choices for string settings -> rendered as combo box in the settings dialog.
OPTIONS = {
    KEY_PRINT_PAPER_SIZE: ["A4", "A5", "A3", "Letter"],
    KEY_PRINT_ORIENTATION: ["portrait", "landscape"],
    KEY_RESULT_TIEBREAK_MODE: ["most_top_scores", "total_highest"],
    KEY_UI_LANGUAGE: ["de"],
    KEY_UI_THEME_MODE: ["system", "light", "dark"],
}
THEME_MODE_LABELS = {"system": "Wie Windows", "light": "Hell", "dark": "Dunkel"}

DEFAULTS = {key: value for key, value, *_ in DEFAULT_SETTINGS}

CLUB_FIELDS = ["club_name", "street", "zip_code", "city", "country", "phone", "email",
               "website", "logo_path", "federation", "club_number", "notes"]


def all_settings() -> list[AppSetting]:
    """Seed order first; settings added later by migrations follow alphabetically."""
    order = {key: i for i, key in enumerate(DEFAULTS)}
    with session_scope() as s:
        items = list(s.scalars(select(AppSetting)))
    return sorted(items, key=lambda st: (order.get(st.key, len(order)), st.key))


def get_all() -> dict[str, str]:
    return {st.key: st.value for st in all_settings()}


def get(key: str, default: str | None = None) -> str | None:
    with session_scope() as s:
        st = s.get(AppSetting, key)
        return st.value if st is not None and st.value is not None else default


def get_bool(key: str) -> bool:
    return (get(key, DEFAULTS.get(key, "false")) or "").lower() in ("1", "true", "yes", "ja")


def set_many(values: dict[str, str]) -> None:
    with session_scope() as s:
        for key, value in values.items():
            st = s.get(AppSetting, key)
            if st is None:
                st = AppSetting(key=key, value_type="string")
                s.add(st)
            st.value = value


def set_value(key: str, value: str) -> None:
    set_many({key: value})


def color_defaults() -> dict[str, str]:
    return {k: v for k, v in DEFAULTS.items() if k.startswith(COLOR_PREFIX)}


def get_club_profile() -> dict:
    with session_scope() as s:
        cp = s.get(ClubProfile, 1)
        if cp is None:
            cp = ClubProfile(id=1)
            s.add(cp)
            s.flush()
        return {f: getattr(cp, f) for f in CLUB_FIELDS}


def save_club_profile(data: dict) -> None:
    with session_scope() as s:
        cp = s.get(ClubProfile, 1)
        if cp is None:
            cp = ClubProfile(id=1)
            s.add(cp)
        for f in CLUB_FIELDS:
            if f in data:
                setattr(cp, f, data[f] or None)

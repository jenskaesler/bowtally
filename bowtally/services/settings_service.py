# -*- coding: utf-8 -*-
"""CRUD for app_settings and club_profile."""
import logging
import shutil
from pathlib import Path

from sqlalchemy import select

from bowtally import config
from bowtally.database.engine import session_scope
from bowtally.database.models import AppSetting, ClubProfile
from bowtally.database.seed import DEFAULT_SETTINGS

KEY_PARTICIPANTS_PER_GROUP = "participants_per_group"
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
KEY_RESULT_AUTO_RANK = "result_auto_rank"
KEY_UI_LANGUAGE = "ui_language"
KEY_TOURNAMENT_RULES_TEXT = "tournament_rules_text"
KEY_PARTICIPATION_TERMS_TEXT = "participation_terms_text"
KEY_LOG_LEVEL = "log_level"

# Email template key prefixes — each maps to {key}_subject and {key}_body in app_settings
KEY_EMAIL_TPL_CONFIRMATION = "email_reg"
KEY_EMAIL_TPL_PAYMENT = "email_payment"
KEY_EMAIL_TPL_DOCS = "email_docs"
KEY_EMAIL_TPL_RESULTS = "email_results"
KEY_EMAIL_TPL_WAITLIST = "email_waitlist"
KEY_EMAIL_TPL_HELPER = "email_helper"
KEY_EMAIL_TPL_DATA_REQUEST = "email_data_request"
KEY_EMAIL_TPL_TOURNAMENT_ANNOUNCE = "email_tpl_tournament_announce"
# WhatsApp templates (click-to-chat wa.me): only a body, full settings key
KEY_WHATSAPP_TARGET = "whatsapp_target"          # app (wa.me) | web (web.whatsapp.com)
KEY_WHATSAPP_TPL_CONFIRMATION = "whatsapp_reg_body"
KEY_WHATSAPP_TPL_PAYMENT = "whatsapp_payment_body"
KEY_WHATSAPP_TPL_DOCS = "whatsapp_docs_body"
KEY_WHATSAPP_TPL_WAITLIST = "whatsapp_waitlist_body"
KEY_WHATSAPP_TPL_HELPER = "whatsapp_helper_body"
KEY_WHATSAPP_TPL_DATA_REQUEST = "whatsapp_data_request_body"

COLOR_PREFIX = "color_"

# Fixed choices for string settings -> rendered as combo box in the settings dialog.
OPTIONS = {
    KEY_PRINT_PAPER_SIZE: ["A4", "A5", "A3", "Letter"],
    KEY_PRINT_ORIENTATION: ["portrait", "landscape"],
    KEY_UI_LANGUAGE: ["de"],
    KEY_UI_THEME_MODE: ["system", "light", "dark"],
    "waitlist_mode": ["block", "auto"],
    KEY_WHATSAPP_TARGET: ["app", "web"],
    KEY_LOG_LEVEL: ["info", "warning", "debug"],
    KEY_FONT_FAMILY: [*config.BUNDLED_FONTS, "Segoe UI"],
}
LOG_LEVELS = {"info": logging.INFO, "warning": logging.WARNING, "debug": logging.DEBUG}
THEME_MODE_LABELS = {"system": "System", "light": "Hell", "dark": "Dunkel"}

DEFAULTS = {key: value for key, value, *_ in DEFAULT_SETTINGS}

CLUB_FIELDS = ["club_name", "street", "zip_code", "city", "country", "phone", "email",
               "website", "logo_path", "federation", "club_number",
               "bank_account_holder", "bank_iban", "bank_bic", "bank_reference_template",
               "course_description", "notes",
               "first_board_fname", "first_board_lname",
               "second_board_fname", "second_board_lname",
               "treasurer_fname", "treasurer_lname",
               "sports_dir_fname", "sports_dir_lname",
               "bow_ref_fname", "bow_ref_lname",
               "first_board_phone", "first_board_email",
               "second_board_phone", "second_board_email",
               "treasurer_phone", "treasurer_email",
               "sports_dir_phone", "sports_dir_email",
               "bow_ref_phone", "bow_ref_email"]


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


def participants_per_group() -> int:
    """Group size for the automatic start groups of a tournament (at least 1)."""
    try:
        return max(1, int(get(KEY_PARTICIPANTS_PER_GROUP, DEFAULTS.get(
            KEY_PARTICIPANTS_PER_GROUP, "5")) or 5))
    except ValueError:
        return 5


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


def apply_log_level(value: str | None = None) -> None:
    """Sets the root logger level from the saved setting (or from `value`); unknown = info."""
    value = value or get(KEY_LOG_LEVEL, DEFAULTS[KEY_LOG_LEVEL])
    logging.getLogger().setLevel(LOG_LEVELS.get(value, logging.INFO))
    if value == "debug":    # also reached silently after a restore, so leave a trace in app.log
        logging.getLogger(__name__).warning(
            "Debug-Logging ist aktiv: app.log wächst schnell und kann personenbezogene Daten enthalten.")


def color_defaults() -> dict[str, str]:
    return {k: v for k, v in DEFAULTS.items() if k.startswith(COLOR_PREFIX)}


LOGO_DIR = "logo"       # below the app data folder, also the folder name inside a backup


def store_logo(source) -> Path:
    """Copy a logo into <app data>/logo/ and return its path there."""
    source = Path(source)
    dest = config.APP_DATA_DIR / LOGO_DIR / source.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != dest.resolve():
        shutil.copy2(source, dest)
    return dest


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

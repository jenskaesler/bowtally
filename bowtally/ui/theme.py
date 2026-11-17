# -*- coding: utf-8 -*-
"""Builds palette, QSS and icons from the color settings in app_settings.

Light and dark mode share the brand colors (primary / secondary / accent); neutrals
(background, surface, border, text) come from separate light and dark settings.
"""
import os as _os
import tempfile as _tf

from PySide6.QtCore import QByteArray, QObject, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from bowtally.services import settings_service as ss

FONT_FALLBACKS = ["Segoe UI", "Arial", "sans-serif"]
MODE_LIGHT, MODE_DARK, MODE_SYSTEM = "light", "dark", "system"

# Fixed semantic colors (adjusted for contrast per mode in tokens())
SUCCESS = "#2E7D32"
WARNING = "#E65100"
DANGER = "#C62828"
GOLD, SILVER, BRONZE = "#D4AF37", "#A7B1BC", "#CD7F32"
NAV_HOVER_LIGHT = "#E8F0FE"

_current: dict[str, str] = {}


class _Notifier(QObject):
    changed = Signal()


# Widgets that paint theme colors themselves connect to notifier.changed
notifier = _Notifier()

_check_svg_cache: dict[str, str] = {}


def _write_check_svg(color: str) -> str:
    if color in _check_svg_cache:
        return _check_svg_cache[color]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">'
        f'<path d="M3 8.5 6.5 12 13 5" fill="none" stroke="{color}" '
        'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    fd, path = _tf.mkstemp(suffix=".svg", prefix="btchk_")
    _os.write(fd, svg.encode())
    _os.close(fd)
    _check_svg_cache[color] = path.replace("\\", "/")
    return _check_svg_cache[color]


_arrow_svg_cache: dict[str, str] = {}


def _write_arrow_svg(color: str, d: str) -> str:
    key = f"{color}_{d}"
    if key in _arrow_svg_cache:
        return _arrow_svg_cache[key]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24">'
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.5" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    fd, path = _tf.mkstemp(suffix=".svg", prefix="btarr_")
    _os.write(fd, svg.encode())
    _os.close(fd)
    _arrow_svg_cache[key] = path.replace("\\", "/")
    return _arrow_svg_cache[key]


# ---------------------------------------------------------------- color helpers

def _mix(a: str, b: str, t: float) -> str:
    """Blend a towards b by t (0..1)."""
    ca, cb = QColor(a), QColor(b)
    return QColor(round(ca.red() + (cb.red() - ca.red()) * t),
                  round(ca.green() + (cb.green() - ca.green()) * t),
                  round(ca.blue() + (cb.blue() - ca.blue()) * t)).name()


def _luminance(c: str) -> float:
    q = QColor(c)
    return (0.299 * q.red() + 0.587 * q.green() + 0.114 * q.blue()) / 255


def _readable_on(bg: str, color: str, min_diff: float = 0.38) -> str:
    """Shift HSL lightness until color stands out enough from bg (keeps hue + saturation)."""
    q = QColor(color)
    h, s, lightness, _a = q.getHslF()
    direction = 1 if _luminance(bg) < 0.5 else -1
    for step in range(21):
        c = QColor.fromHslF(max(h, 0.0), s, min(max(lightness + direction * step * 0.03, 0.0),
                                                1.0)).name()
        if abs(_luminance(c) - _luminance(bg)) >= min_diff:
            return c
    return "#FFFFFF" if direction > 0 else "#000000"


def _on(color: str) -> str:
    return "#FFFFFF" if _luminance(color) < 0.6 else "#111418"


# ---------------------------------------------------------------- tokens

def effective_mode(values: dict[str, str]) -> str:
    mode = values.get(ss.KEY_UI_THEME_MODE) or MODE_SYSTEM
    if mode == MODE_SYSTEM:
        hints = QGuiApplication.styleHints() if QGuiApplication.instance() else None
        dark = hints is not None and hints.colorScheme() == Qt.ColorScheme.Dark
        return MODE_DARK if dark else MODE_LIGHT
    return mode


def tokens(overrides: dict[str, str] | None = None) -> dict[str, str]:
    values = {**ss.DEFAULTS, **{k: v for k, v in ss.get_all().items() if v},
              **(overrides or {})}
    mode = effective_mode(values)
    prefix = "color_dark_" if mode == MODE_DARK else "color_"
    bg = values[prefix + "background"]
    surface = values[prefix + "surface"]
    text = values[prefix + "text"]
    # Dark mode uses the (usually brighter) secondary brand color as accent color
    base = values[ss.KEY_COLOR_SECONDARY if mode == MODE_DARK else ss.KEY_COLOR_PRIMARY]
    primary = _readable_on(surface, base, 0.30)
    accent = _readable_on(surface, values[ss.KEY_COLOR_ACCENT], 0.25)
    t = {
        "mode": mode, "bg": bg, "surface": surface, "text": text,
        "text2": values[prefix + "text_secondary"], "border": values[prefix + "border"],
        "primary": primary, "primary_hover": _readable_on(surface, values[ss.KEY_COLOR_SECONDARY],
                                                          0.38 if mode == MODE_DARK else 0.25),
        "on_primary": _on(primary), "accent": accent,
        "primary_soft": _mix(surface, primary, 0.16 if mode == MODE_DARK else 0.10),
        "accent_soft": _mix(surface, accent, 0.14),
        "hover": _mix(surface, text, 0.06),
        "pressed": _mix(surface, text, 0.11),
        "alt_row": _mix(surface, text, 0.025),
        "grid": _mix(surface, text, 0.08),
        "disabled": _mix(surface, text, 0.35),
        "sidebar": bg,
        "nav_hover": NAV_HOVER_LIGHT if mode == MODE_LIGHT else _mix(surface, text, 0.08),
        "success": _readable_on(surface, SUCCESS, 0.25),
        "success_soft": _mix(surface, SUCCESS, 0.20 if mode == MODE_DARK else 0.13),
        "danger": _readable_on(surface, DANGER, 0.25),
        "warning": _readable_on(surface, WARNING, 0.25),
        "warning_soft": _mix(surface, WARNING, 0.20 if mode == MODE_DARK else 0.13),
        "secondary": _readable_on(surface, values[ss.KEY_COLOR_SECONDARY], 0.25),
        "miss_soft": _mix(surface, accent, 0.18 if mode == MODE_DARK else 0.10),
        "gold_soft": _mix(surface, GOLD, 0.24 if mode == MODE_DARK else 0.20),
        "silver_soft": _mix(surface, SILVER, 0.22 if mode == MODE_DARK else 0.20),
        "bronze_soft": _mix(surface, BRONZE, 0.22 if mode == MODE_DARK else 0.17),
    }
    return t


def current() -> dict[str, str]:
    """Tokens of the theme applied last (for widgets that paint colors themselves)."""
    return _current or tokens()


# ---------------------------------------------------------------- stylesheet

def build_stylesheet(overrides: dict[str, str] | None = None) -> str:
    return _qss(tokens(overrides))


def _qss(t: dict[str, str]) -> str:
    _chk = _write_check_svg(t['on_primary'])
    _arr_d = _write_arrow_svg(t['text'], "M6 9l6 6 6-6")
    _arr_u = _write_arrow_svg(t['text'], "M18 15l-6-6-6 6")
    return f"""
QWidget {{ color: {t['text']}; font-size: 10pt; }}
QMainWindow, QDialog, QWizard, QWizardPage, QWidget#contentArea, QScrollArea,
QScrollArea > QWidget > QWidget {{ background: {t['bg']}; }}
QScrollArea {{ border: none; }}
QTabWidget > QStackedWidget > QWidget {{ background: transparent; }}

/* sidebar */
QWidget#sidebar {{ background: {t['sidebar']}; border-right: 1px solid {t['border']}; }}
QLabel#appTitle {{ font-size: 14pt; font-weight: 700; background: transparent; }}
QListWidget#dashChips {{ background: transparent; border: none; outline: 0; padding: 4px 20px; }}
QListWidget#navigation {{ background: transparent; border: none; outline: 0; padding: 0 10px; }}
QListWidget#navigation::item {{
    color: {t['text2']}; padding: 9px 10px; margin: 1px 0; border-radius: 8px;
}}
QListWidget#navigation::item:hover {{ background: {t['nav_hover']}; color: {t['text']}; }}
QListWidget#navigation::item:selected {{
    background: {t['primary']}; color: {t['on_primary']}; font-weight: 600;
}}
QPushButton#themeToggle {{
    background: transparent; border: none; color: {t['text2']}; text-align: left;
    padding: 8px 12px; border-radius: 8px;
}}
QPushButton#themeToggle:hover {{ background: {t['hover']}; color: {t['text']}; }}

/* typography */
QLabel#pageTitle {{ font-size: 19pt; font-weight: 700; padding: 2px 0 6px 0; }}
QLabel#sectionTitle {{ font-size: 9pt; font-weight: 600; color: {t['text2']}; }}
QLabel[secondary="true"] {{ color: {t['text2']}; }}
QFrame#card {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 12px; }}
QFrame#card QLabel {{ background: transparent; }}
QLabel#cardValue {{ font-size: 26pt; font-weight: 700; }}

/* buttons */
QPushButton {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px;
    padding: 7px 16px; font-weight: 600; min-height: 18px;
}}
QPushButton:hover {{ background: {t['hover']}; }}
QPushButton:pressed {{ background: {t['pressed']}; }}
QPushButton:disabled {{ color: {t['disabled']}; background: {t['bg']}; }}
QPushButton[primary="true"] {{
    background: {t['primary']}; color: {t['on_primary']}; border: 1px solid {t['primary']};
}}
QPushButton[primary="true"]:hover {{
    background: {t['primary_hover']}; border-color: {t['primary_hover']};
}}
QPushButton[primary="true"]:disabled {{
    background: {t['primary_soft']}; border-color: {t['primary_soft']}; color: {t['disabled']};
}}
QPushButton[primary="true"][dirty="true"] {{
    background: {t['danger']}; border-color: {t['danger']}; color: {_on(t['danger'])};
}}
QPushButton[cancel="true"] {{ background: #111111; border-color: #111111; color: #FFFFFF; }}
QPushButton[cancel="true"]:hover {{ background: #333333; border-color: #333333; }}
QPushButton[cancel="true"]:disabled {{ background: #555555; border-color: #555555; color: #AAAAAA; }}
QPushButton[danger="true"] {{ color: {t['accent']}; }}
QPushButton[danger="true"]:hover {{
    background: {t['accent_soft']}; border-color: {t['accent']};
}}
QPushButton[danger="true"]:disabled {{ color: {t['disabled']}; background: {t['bg']}; }}

/* inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateEdit, QTimeEdit, QComboBox {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px;
    padding: 6px 10px; min-height: 18px;
    selection-background-color: {t['primary']}; selection-color: {t['on_primary']};
}}
QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDateEdit:hover, QTimeEdit:hover,
QComboBox:hover {{ border-color: {t['disabled']}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDateEdit:focus,
QTimeEdit:focus, QComboBox:focus {{ border: 1px solid {t['primary']}; }}
QLineEdit:read-only, QPlainTextEdit[readOnly="true"] {{ background: {t['bg']}; }}
QComboBox QAbstractItemView {{
    background: {t['surface']}; border: 1px solid {t['border']}; padding: 4px;
    selection-background-color: {t['primary_soft']}; selection-color: {t['text']};
}}
QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {{
    border: none; border-top-right-radius: 8px; border-bottom-right-radius: 8px; width: 20px; }}
QComboBox::down-arrow {{
    image: url({_arr_d}); width: 10px; height: 10px; }}
QDateEdit::down-arrow, QTimeEdit::down-arrow {{
    image: url({_arr_d}); width: 8px; height: 8px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button {{ border: none; border-top-right-radius: 8px; width: 16px; }}
QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button {{ border: none; border-bottom-right-radius: 8px; width: 16px; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow {{ image: url({_arr_u}); width: 8px; height: 8px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow {{ image: url({_arr_d}); width: 8px; height: 8px; }}

/* tables and lists */
QTableView, QTreeView, QListView {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px;
    gridline-color: {t['grid']}; alternate-background-color: {t['alt_row']};
    selection-background-color: {t['primary_soft']}; selection-color: {t['text']};
    outline: 0;
}}
/* no QTableView::item rules: they would override per-cell background colors */
QListView::item:selected {{ background: {t['primary_soft']}; color: {t['text']}; }}
QListView::item {{ padding: 6px 8px; border-radius: 6px; }}
QListView::item:hover {{ background: {t['hover']}; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: {t['surface']}; color: {t['text2']}; font-weight: 600; font-size: 9pt;
    padding: 8px 4px; border: none; border-bottom: 1px solid {t['border']};
}}
QHeaderView::section:hover {{ color: {t['text']}; }}
QTableCornerButton::section {{ background: {t['surface']}; border: none; }}

/* tabs: underline style */
QTabWidget::pane {{ border: none; border-top: 1px solid {t['border']}; top: -1px;
    background: transparent; }}
QTabBar {{ qproperty-drawBase: 0; background: transparent; }}
QTabBar::tab {{
    background: transparent; border: none; border-bottom: 2px solid transparent;
    padding: 8px 14px; margin-right: 6px; color: {t['text2']}; font-weight: 600;
}}
QTabBar::tab:hover {{ color: {t['text']}; }}
QTabBar::tab:selected {{ color: {t['primary']}; border-bottom: 2px solid {t['primary']}; }}

QGroupBox {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px;
    margin-top: 16px; padding: 14px 10px 10px 10px; font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px;
    color: {t['text2']}; background-color: {t['bg']}; }}

QSplitter::handle {{ background: {t['border']}; }}
QSplitter::handle:horizontal {{ width: 1px; }}

/* settings / help sidebar nav */
QListWidget#settingsNav, QListWidget#helpNav {{
    background: transparent; border: none; outline: 0; padding: 4px 0;
}}
QListWidget#settingsNav::item, QListWidget#helpNav::item {{
    padding: 6px 12px; border-radius: 6px; color: {t['text']};
}}
QListWidget#settingsNav::item:hover, QListWidget#helpNav::item:hover {{
    background: {t['hover']};
}}
QListWidget#settingsNav::item:selected, QListWidget#helpNav::item:selected {{
    background: {t['primary']}; color: {t['on_primary']}; font-weight: 600;
}}

QStatusBar {{ background: {t['sidebar']}; border-top: 1px solid {t['border']}; }}
QStatusBar QLabel {{ color: {t['text2']}; font-size: 9pt; padding: 2px 8px; }}
QStatusBar::item {{ border: none; }}
QToolTip {{ background: {t['surface']}; color: {t['text']}; border: 1px solid {t['border']};
    padding: 4px 8px; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {t['grid']}; border-radius: 3px; }}
QScrollBar::handle:hover {{ background: {t['disabled']}; }}
QScrollBar::handle:vertical {{ min-height: 28px; }}
QScrollBar::handle:horizontal {{ min-width: 28px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{
    width: 0; height: 0; background: transparent; }}

/* ---------- components ---------- */
QLabel#pageSubtitle {{ color: {t['text2']}; }}
QPushButton#link {{
    background: transparent; border: none; color: {t['primary']}; text-align: left;
    padding: 4px 0; font-weight: 600;
}}
QPushButton#link:hover {{ text-decoration: underline; background: transparent; }}

/* checkboxes */
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 2px solid {t['border']}; border-radius: 4px;
    background: {t['surface']};
}}
QCheckBox::indicator:hover {{ border-color: {t['primary']}; }}
QCheckBox::indicator:checked {{
    background: {t['primary']}; border-color: {t['primary']}; image: url({_chk});
}}
QCheckBox::indicator:checked:hover {{ background: {t['primary_hover']}; border-color: {t['primary_hover']}; image: url({_chk}); }}

/* menus */
QMenu {{ background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 6px 20px; border-radius: 6px; color: {t['text']}; }}
QMenu::item:selected {{ background: {t['primary']}; color: {t['on_primary']}; }}
QMenu::item:disabled {{ color: {t['disabled']}; }}
QFrame#sidebarDivider {{ background: {t['border']}; min-height: 1px; max-height: 1px; border: none; margin: 4px 12px; }}
QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}

/* side drawer */
QFrame#drawer {{ background: {t['surface']}; border-left: 1px solid {t['border']}; }}
QFrame#drawer QScrollArea, QFrame#drawer QScrollArea > QWidget > QWidget {{
    background: {t['surface']}; border: none; }}
QLabel#drawerTitle {{ font-size: 14pt; font-weight: 700; }}
QWidget#drawerFooter {{ border-top: 1px solid {t['border']}; background: {t['surface']}; }}
QToolButton#iconButton {{ border: none; border-radius: 6px; padding: 4px; background: transparent; }}
QToolButton#iconButton:hover {{ background: {t['hover']}; }}

/* form fields */
QLabel#fieldLabel {{ font-weight: 600; font-size: 9pt; }}
QLabel#fieldRequired {{ color: {t['accent']}; font-weight: 700; }}
QLabel#fieldError {{ color: {t['accent']}; font-size: 9pt; }}
QLabel#fieldHint {{ color: {t['text2']}; font-size: 9pt; }}
QLineEdit[invalid="true"], QComboBox[invalid="true"], QDateEdit[invalid="true"],
QTimeEdit[invalid="true"], QSpinBox[invalid="true"], QPlainTextEdit[invalid="true"], QTableWidget[invalid="true"] {{
    border: 1px solid {t['accent']}; }}

/* toast */
QFrame#toast {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px;
    border-left: 4px solid {t['primary']};
}}
QFrame#toast[kind="success"] {{ border-left-color: {t['success']}; }}
QFrame#toast[kind="warning"] {{ border-left-color: {t['warning']}; }}
QFrame#toast[kind="error"] {{ border-left-color: {t['accent']}; }}
QFrame#toast QLabel {{ background: transparent; }}
QPushButton#toastAction {{
    background: transparent; border: none; color: {t['primary']}; padding: 2px 4px;
    text-decoration: underline;
}}

/* status chips */
QLabel#statusChip {{
    border-radius: 11px; padding: 3px 12px; font-size: 9pt; font-weight: 600;
    border: 1px solid {t['border']}; color: {t['text2']}; background: transparent;
}}
QLabel#statusChip[kind="primary"] {{
    background: {t['primary_soft']}; color: {t['primary']}; border-color: {t['primary']};
}}
QLabel#statusChip[kind="success"] {{
    background: {t['success_soft']}; color: {t['success']}; border-color: {t['success']};
}}
QLabel#statusChip[kind="muted"] {{
    background: {t['pressed']}; color: {t['text']}; border-color: {t['pressed']};
}}
QLabel#statusChip[kind="warning"] {{
    background: {t['warning_soft']}; color: {t['warning']}; border-color: {t['warning']};
}}
QLabel#statusChip[kind="danger"] {{
    background: {t['accent_soft']}; color: {t['accent']}; border-color: {t['accent']};
}}

/* calendar view */
QFrame#dayCell {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 6px;
}}
QLabel#dayNumber {{ font-weight: 600; }}
QLabel#dayNumber[today="true"] {{
    background: {t['primary']}; color: {t['on_primary']};
    border-radius: 10px; padding: 1px 5px;
}}
QFrame#miniMonth {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px;
}}
QPushButton#calModeBtn {{
    padding: 4px 12px; border: 1px solid {t['border']};
    border-radius: 0; background: {t['surface']}; color: {t['text']};
}}
QPushButton#calModeBtn:checked {{
    background: {t['primary']}; color: {t['on_primary']}; border-color: {t['primary']};
}}
QPushButton#calModeBtn:hover:!checked {{ background: {t['hover']}; }}
QPushButton#calModeBtn:first-child {{ border-radius: 6px 0 0 6px; }}
QPushButton#calModeBtn:last-child  {{ border-radius: 0 6px 6px 0; }}

/* tournament navigator (sidebar) */
QFrame#tournamentNav {{ background: transparent; border-bottom: 1px solid {t['border']}; }}
QLabel#navTournamentName {{ font-size: 11pt; font-weight: 700; }}
QLabel#phaseLabel {{ color: {t['text2']}; padding: 1px 5px; border-radius: 5px; border: 1px solid transparent; }}
QLabel#phaseLabel[state="current"] {{ background: {t['success_soft']}; color: {t['success']}; border-color: {t['success']}; font-weight: 700; }}
QLabel#phaseLabel[state="done"] {{ background: {t['pressed']}; color: {t['text']}; }}
QLabel#phaseDate {{ color: {t['text2']}; font-size: 8.5pt; }}
QFrame#separator {{ background: {t['border']}; max-height: 1px; min-height: 1px; }}

/* guide */
QLabel#ampel, QFrame#card QLabel#ampel {{ min-width: 10px; max-width: 10px;
    min-height: 10px; max-height: 10px; border-radius: 5px; background: {t['success']}; }}
QFrame#card QLabel#ampel[state="warning"] {{ background: {t['warning']}; }}
QFrame#card QLabel#ampel[state="blocker"] {{ background: {t['accent']}; }}
QPushButton#nextPhase {{ padding: 7px 8px; font-size: 9pt; }}
QLabel#bigCounter {{ font-size: 22pt; font-weight: 700; }}
QLabel#dangerText {{ color: {t['accent']}; font-weight: 600; }}
QLabel#successText {{ color: {t['success']}; font-weight: 600; }}

/* selectable chips (wizard bow classes) */
QPushButton#chip {{
    border-radius: 16px; padding: 6px 14px; font-weight: 600; background: {t['surface']};
}}
QPushButton#chip:checked {{
    background: {t['primary']}; color: {t['on_primary']}; border-color: {t['primary']};
}}

/* action bar */
QFrame#actionBar {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px;
}}
QFrame#actionBar QLabel {{ background: transparent; font-weight: 600; }}

/* empty state */
QLabel#emptyTitle {{ font-size: 14pt; font-weight: 700; }}
QLabel#emptyText {{ color: {t['text2']}; }}

/* wizard steps */
QLabel#stepDot {{
    min-width: 26px; max-width: 26px; min-height: 26px; max-height: 26px;
    border-radius: 13px; border: 1px solid {t['border']}; color: {t['text2']};
    font-weight: 700; background: {t['surface']};
}}
QLabel#stepDot[state="current"] {{ background: {t['primary']}; color: {t['on_primary']};
    border-color: {t['primary']}; }}
QLabel#stepDot[state="done"] {{ background: {t['primary_soft']}; color: {t['primary']};
    border-color: {t['primary']}; }}
QLabel#stepLabel {{ color: {t['text2']}; font-weight: 600; }}
QLabel#stepLabel[state="current"] {{ color: {t['text']}; }}
QFrame#stepLine {{ background: {t['border']}; max-height: 1px; min-height: 1px; }}
QLabel#wizardTitle {{ font-size: 15pt; font-weight: 700; }}
"""


def _palette(t: dict[str, str]) -> QPalette:
    """Native parts (message boxes, calendar popup, check boxes) follow the theme too."""
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: t["bg"], QPalette.ColorRole.WindowText: t["text"],
        QPalette.ColorRole.Base: t["surface"], QPalette.ColorRole.AlternateBase: t["alt_row"],
        QPalette.ColorRole.Text: t["text"], QPalette.ColorRole.Button: t["surface"],
        QPalette.ColorRole.ButtonText: t["text"], QPalette.ColorRole.Highlight: t["primary"],
        QPalette.ColorRole.HighlightedText: t["on_primary"],
        QPalette.ColorRole.ToolTipBase: t["surface"], QPalette.ColorRole.ToolTipText: t["text"],
        QPalette.ColorRole.PlaceholderText: t["text2"], QPalette.ColorRole.Link: t["primary"],
        QPalette.ColorRole.Mid: t["border"], QPalette.ColorRole.Midlight: t["border"],
        QPalette.ColorRole.Dark: t["grid"], QPalette.ColorRole.Light: t["surface"],
    }
    for role, color in roles.items():
        p.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(t["disabled"]))
    return p


def apply(app: QApplication, overrides: dict[str, str] | None = None) -> dict[str, str]:
    global _current
    family = ss.get(ss.KEY_FONT_FAMILY, "Open Sans")
    font = QFont()
    font.setFamilies([family] + FONT_FALLBACKS)
    font.setPointSize(10)
    app.setFont(font)
    if app.style().name().lower() != "fusion":
        app.setStyle("Fusion")
    _current = tokens(overrides)
    app.setPalette(_palette(_current))
    app.setStyleSheet(_qss(_current))
    notifier.changed.emit()
    return _current


# ---------------------------------------------------------------- icons
# Simple 24x24 line icons (own drawings), stroke color is filled in at render time.

ICONS = {
    "dashboard": '<rect x="3" y="3" width="7" height="9" rx="1.5"/>'
                 '<rect x="14" y="3" width="7" height="5" rx="1.5"/>'
                 '<rect x="14" y="12" width="7" height="9" rx="1.5"/>'
                 '<rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6"/>'
             '<path d="M16 4.6a3.5 3.5 0 0 1 0 6.8"/><path d="M18 14.3c2.1.7 3.5 2.8 3.5 5.7"/>',
    "rules": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v2.5H9z"/>'
             '<path d="M9 11h6M9 15h6M9 19h3"/>',
    "layers": '<path d="M12 3 2.5 7.5 12 12l9.5-4.5L12 3z"/><path d="m2.5 12 9.5 4.5 9.5-4.5"/>'
              '<path d="m2.5 16.5 9.5 4.5 9.5-4.5"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5.5"/>'
              '<circle cx="12" cy="12" r="1.6" fill="{c}"/>',
    "settings": '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/>'
                '<circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/>'
                '<circle cx="17" cy="18" r="2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M5.3 5.3l1.4 1.4M17.3 '
           '17.3l1.4 1.4M2.5 12h2M19.5 12h2M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "monitor": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    "check": '<path d="M5 12.5 10 17l9-10"/>',
    "circle": '<circle cx="12" cy="12" r="7"/>',
    "check-circle": '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 3 3 5-6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
    "alert": '<path d="M12 3.5 2.5 20h19L12 3.5z"/><path d="M12 10v4.5M12 17.5v.01"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "x-circle": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    "help": '<circle cx="12" cy="12" r="9"/>'
            '<path d="M9.5 9.5a2.5 2.5 0 0 1 4.9.7c0 1.7-2.4 2.2-2.4 3.8M12 17v.01"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "trash": '<path d="M4 7h16M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13"/>',
    "grip": ''.join(f'<circle cx="{x}" cy="{y}" r="1.2" fill="{{c}}"/>'
                    for x in (9, 15) for y in (6, 12, 18)),
    "more-horizontal": '<circle cx="5" cy="12" r="1.5" fill="{c}"/>'
                       '<circle cx="12" cy="12" r="1.5" fill="{c}"/>'
                       '<circle cx="19" cy="12" r="1.5" fill="{c}"/>',
    "inbox": '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5.5 5h13L21 13v6H3v-6L5.5 5z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15" rx="2"/>'
                '<path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 13h6M9 17h6"/>',
    "edit": '<path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z"/>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/>'
            '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/>'
            '<path d="m22 7-10 6L2 7"/>',
    "money": '<circle cx="12" cy="12" r="9"/>'
             '<path d="M12 6.5v11M15 8.5c0-1.4-1.3-2.5-3-2.5s-3 .9-3 2.2c0 3 6 1.6 6 4.6'
             ' 0 1.3-1.3 2.2-3 2.2s-3-1.1-3-2.5"/>',
    "menu": '<path d="M3 6h18M3 12h18M3 18h18"/>',
    "arrow-right": '<path d="M5 12h14M14 6l6 6-6 6"/>',
    "eye": '<path d="M2 12c2-5 5-7 10-7s8 2 10 7c-2 5-5 7-10 7s-8-2-10-7z"/>'
           '<circle cx="12" cy="12" r="3"/>',
    "eye-off": '<path d="M3 3l18 18M10.6 10.6A3 3 0 0 0 14.8 14.8'
               'M7.9 7.9A10 10 0 0 0 2 12c2 5 5 7 10 7a9.3 9.3 0 0 0 4.7-1.3'
               'M16 16A10 10 0 0 0 22 12c-2-5-5-7-10-7a9.3 9.3 0 0 0-5 1.5"/>',
    "list": '<path d="M9 6h12M9 12h12M9 18h12"/>'
            '<circle cx="4" cy="6" r="1.2" fill="{c}"/>'
            '<circle cx="4" cy="12" r="1.2" fill="{c}"/>'
            '<circle cx="4" cy="18" r="1.2" fill="{c}"/>',
}


def pixmap(name: str, color: str, size: int = 20) -> QPixmap:
    body = ICONS[name].replace("{c}", color)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
           f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
           f'stroke-linejoin="round">{body}</svg>')
    scale = 3   # render at 3x, Qt scales down crisply on any DPI
    pix = QPixmap(size * scale, size * scale)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, size * scale,
                                                                  size * scale))
    painter.end()
    pix.setDevicePixelRatio(scale)
    return pix


def icon(name: str, color: str | None = None, selected_color: str | None = None) -> QIcon:
    t = current()
    ic = QIcon()
    ic.addPixmap(pixmap(name, color or t["text2"]), QIcon.Mode.Normal)
    ic.addPixmap(pixmap(name, selected_color or t["primary"]), QIcon.Mode.Selected)
    return ic

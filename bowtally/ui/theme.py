# -*- coding: utf-8 -*-
"""Builds palette, QSS and icons from the color settings in app_settings.

Light and dark mode share the brand colors (primary / secondary / accent); neutrals
(background, surface, border, text) come from separate light and dark settings.
"""
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from bowtally.services import settings_service as ss

FONT_FALLBACKS = ["Segoe UI", "Arial", "sans-serif"]
MODE_LIGHT, MODE_DARK, MODE_SYSTEM = "light", "dark", "system"

_current: dict[str, str] = {}


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
        "sidebar": surface,
    }
    return t


def current() -> dict[str, str]:
    """Tokens of the theme applied last (for widgets that paint colors themselves)."""
    return _current or tokens()


# ---------------------------------------------------------------- stylesheet

def build_stylesheet(overrides: dict[str, str] | None = None) -> str:
    return _qss(tokens(overrides))


def _qss(t: dict[str, str]) -> str:
    return f"""
QWidget {{ color: {t['text']}; font-size: 10pt; }}
QMainWindow, QDialog, QWizard, QWizardPage, QWidget#contentArea, QScrollArea,
QScrollArea > QWidget > QWidget {{ background: {t['bg']}; }}
QTabWidget > QStackedWidget > QWidget {{ background: transparent; }}

/* sidebar */
QWidget#sidebar {{ background: {t['sidebar']}; border-right: 1px solid {t['border']}; }}
QLabel#appTitle {{ font-size: 14pt; font-weight: 700; background: transparent; }}
QListWidget#navigation {{ background: transparent; border: none; outline: 0; padding: 0 10px; }}
QListWidget#navigation::item {{
    color: {t['text2']}; padding: 9px 10px; margin: 1px 0; border-radius: 8px;
}}
QListWidget#navigation::item:hover {{ background: {t['hover']}; color: {t['text']}; }}
QListWidget#navigation::item:selected {{
    background: {t['primary_soft']}; color: {t['primary']}; font-weight: 600;
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
QPushButton[danger="true"] {{ color: {t['accent']}; }}
QPushButton[danger="true"]:hover {{
    background: {t['accent_soft']}; border-color: {t['accent']};
}}

/* inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateEdit, QComboBox {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 8px;
    padding: 6px 10px; min-height: 18px;
    selection-background-color: {t['primary']}; selection-color: {t['on_primary']};
}}
QLineEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDateEdit:hover, QComboBox:hover {{
    border-color: {t['disabled']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDateEdit:focus,
QComboBox:focus {{ border: 1px solid {t['primary']}; }}
QLineEdit:read-only, QPlainTextEdit[readOnly="true"] {{ background: {t['bg']}; }}
QComboBox QAbstractItemView {{
    background: {t['surface']}; border: 1px solid {t['border']}; padding: 4px;
    selection-background-color: {t['primary_soft']}; selection-color: {t['text']};
}}

/* tables and lists */
QTableView, QTreeView, QListView {{
    background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 10px;
    gridline-color: {t['grid']}; alternate-background-color: {t['alt_row']};
    selection-background-color: {t['primary_soft']}; selection-color: {t['text']};
    outline: 0;
}}
QTableView::item, QTreeView::item {{ padding: 0 8px; border: none; }}
QTableView::item:selected, QTreeView::item:selected, QListView::item:selected {{
    background: {t['primary_soft']}; color: {t['text']};
}}
QListView::item {{ padding: 6px 8px; border-radius: 6px; }}
QListView::item:hover {{ background: {t['hover']}; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: {t['surface']}; color: {t['text2']}; font-weight: 600; font-size: 9pt;
    padding: 8px; border: none; border-bottom: 1px solid {t['border']};
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
    color: {t['text2']}; }}

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

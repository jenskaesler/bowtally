# -*- coding: utf-8 -*-
"""Builds the application QSS from the color settings in app_settings."""
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

from bowtally.services import settings_service as ss

FONT_FALLBACKS = ["Segoe UI", "Arial", "sans-serif"]


def _shade(hex_color: str, factor: int) -> str:
    """factor > 100 = darker, < 100 = lighter (QColor semantics)."""
    c = QColor(hex_color)
    return (c.darker(factor) if factor >= 100 else c.lighter(200 - factor)).name()


def current_colors() -> dict[str, str]:
    values = ss.get_all()
    return {k: values.get(k) or v for k, v in ss.color_defaults().items()}


def build_stylesheet(colors: dict[str, str] | None = None) -> str:
    c = dict(current_colors())
    c.update(colors or {})
    p, sec, acc = c[ss.KEY_COLOR_PRIMARY], c[ss.KEY_COLOR_SECONDARY], c[ss.KEY_COLOR_ACCENT]
    txt2, bg = c[ss.KEY_COLOR_TEXT_SECONDARY], c[ss.KEY_COLOR_BACKGROUND]
    surf, border = c[ss.KEY_COLOR_SURFACE], c[ss.KEY_COLOR_BORDER]
    text = "#1F2933"
    p_dark, acc_dark = _shade(p, 120), _shade(acc, 120)
    sel = _shade(sec, 40)
    return f"""
* {{ font-size: 10pt; color: {text}; }}
QMainWindow, QDialog, QWizard, QWizardPage, QStackedWidget > QWidget {{ background: {bg}; }}
QWidget#contentArea {{ background: {bg}; }}

/* navigation */
QListWidget#navigation {{
    background: {p}; border: none; padding-top: 8px; outline: 0;
}}
QListWidget#navigation::item {{
    color: #FFFFFF; padding: 10px 14px; border-left: 4px solid transparent;
}}
QListWidget#navigation::item:hover {{ background: {sec}; }}
QListWidget#navigation::item:selected {{
    background: {p_dark}; border-left: 4px solid {acc}; color: #FFFFFF;
}}
QLabel#appTitle {{
    background: {p}; color: #FFFFFF; font-size: 16pt; font-weight: bold; padding: 16px 14px;
}}

/* headings */
QLabel#pageTitle {{ font-size: 18pt; font-weight: bold; color: {p}; padding: 4px 0 8px 0; }}
QLabel#sectionTitle {{ font-size: 12pt; font-weight: bold; color: {p}; }}
QLabel#secondary, QLabel[secondary="true"] {{ color: {txt2}; }}
QFrame#card {{ background: {surf}; border: 1px solid {border}; border-radius: 6px; }}
QLabel#cardValue {{ font-size: 24pt; font-weight: bold; color: {p}; }}

/* buttons */
QPushButton {{
    background: {surf}; border: 1px solid {border}; border-radius: 4px; padding: 6px 14px;
}}
QPushButton:hover {{ border-color: {sec}; color: {sec}; }}
QPushButton:pressed {{ background: {sel}; }}
QPushButton:disabled {{ color: {txt2}; background: {bg}; }}
QPushButton[primary="true"] {{ background: {p}; color: #FFFFFF; border-color: {p}; }}
QPushButton[primary="true"]:hover {{ background: {sec}; border-color: {sec}; color: #FFFFFF; }}
QPushButton[danger="true"] {{ color: {acc}; border-color: {acc}; }}
QPushButton[danger="true"]:hover {{ background: {acc}; color: #FFFFFF; }}
QPushButton[danger="true"]:pressed {{ background: {acc_dark}; }}

/* inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateEdit, QComboBox {{
    background: {surf}; border: 1px solid {border}; border-radius: 4px; padding: 4px 6px;
    selection-background-color: {sec}; selection-color: #FFFFFF;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDateEdit:focus,
QComboBox:focus {{ border: 1px solid {sec}; }}
QComboBox QAbstractItemView {{
    background: {surf}; border: 1px solid {border};
    selection-background-color: {sec}; selection-color: #FFFFFF;
}}
QCheckBox::indicator {{
    width: 14px; height: 14px; border: 1px solid {border}; border-radius: 3px; background: {surf};
}}
QCheckBox::indicator:checked {{ background: {p}; border-color: {p}; }}

/* tables */
QTableView, QTableWidget, QTreeWidget, QListWidget {{
    background: {surf}; border: 1px solid {border}; gridline-color: {border};
    selection-background-color: {sel}; selection-color: {text};
    alternate-background-color: {bg};
}}
QHeaderView::section {{
    background: {p}; color: #FFFFFF; padding: 6px; border: none;
    border-right: 1px solid {p_dark}; font-weight: bold;
}}
QTableCornerButton::section {{ background: {p}; border: none; }}

/* tabs */
QTabWidget::pane {{ border: 1px solid {border}; background: {surf}; top: -1px; }}
QTabBar::tab {{
    background: {bg}; border: 1px solid {border}; padding: 7px 16px; margin-right: 2px;
    border-top-left-radius: 4px; border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{ background: {surf}; color: {p}; border-bottom-color: {surf};
    font-weight: bold; }}
QTabBar::tab:hover {{ color: {sec}; }}

QGroupBox {{
    background: {surf}; border: 1px solid {border}; border-radius: 6px; margin-top: 14px;
    padding-top: 10px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {p};
    font-weight: bold; }}

QStatusBar {{ background: {surf}; border-top: 1px solid {border}; }}
QStatusBar QLabel {{ color: {txt2}; }}
QToolTip {{ background: {surf}; color: {text}; border: 1px solid {border}; }}
QScrollBar:vertical {{ background: {bg}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 24px; }}
QScrollBar:horizontal {{ background: {bg}; height: 12px; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 5px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
"""


def apply(app: QApplication, colors: dict[str, str] | None = None) -> None:
    family = ss.get(ss.KEY_FONT_FAMILY, "Open Sans")
    font = QFont()
    font.setFamilies([family] + FONT_FALLBACKS)
    font.setPointSize(10)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet(colors))

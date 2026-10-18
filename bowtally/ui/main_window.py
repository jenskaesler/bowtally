# -*- coding: utf-8 -*-
"""Main window: navigation sidebar on the left, content stack on the right."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from bowtally.services import settings_service as ss
from bowtally.ui import theme
from bowtally.ui.dialogs.settings_dialog import SettingsDialog
from bowtally.ui.views.archers_view import ArchersView
from bowtally.ui.views.bow_classes_view import BowClassesView
from bowtally.ui.views.dashboard import DashboardView
from bowtally.ui.views.rules_view import RulesView
from bowtally.ui.views.tournaments_view import TournamentsView
from bowtally.ui.widgets.status_bar import StatusBar

NAV_WIDTH = 200
SETTINGS_KEY = "settings"
ICON_ROLE = Qt.ItemDataRole.UserRole + 1
# theme toggle: mode -> (next mode, icon, label)
MODE_CYCLE = {theme.MODE_SYSTEM: (theme.MODE_LIGHT, "monitor", "Wie Windows"),
              theme.MODE_LIGHT: (theme.MODE_DARK, "sun", "Hell"),
              theme.MODE_DARK: (theme.MODE_SYSTEM, "moon", "Dunkel")}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BowTally")
        self.resize(1280, 800)

        self.dashboard = DashboardView()
        self.archers = ArchersView()
        self.rules = RulesView()
        self.bow_classes = BowClassesView()
        self.tournaments = TournamentsView()
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")

        entries = [
            ("Dashboard", "dashboard", self.dashboard),
            ("Schützen", "users", self.archers),
            ("Regelwerke", "rules", self.rules),
            ("Bogenklassen", "layers", self.bow_classes),
            ("Turniere", "target", self.tournaments),
            ("Einstellungen", "settings", SETTINGS_KEY),
        ]
        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for text, icon_name, target in entries:
            item = QListWidgetItem(text)
            item.setData(ICON_ROLE, icon_name)
            if target != SETTINGS_KEY:
                self.stack.addWidget(target)
                item.setData(Qt.ItemDataRole.UserRole, self.stack.indexOf(target))
            else:
                item.setData(Qt.ItemDataRole.UserRole, SETTINGS_KEY)
            self.nav.addItem(item)
        self.nav.currentItemChanged.connect(self._navigate)

        self.logo = QLabel()
        title = QLabel("BowTally")
        title.setObjectName("appTitle")
        head = QHBoxLayout()
        head.setContentsMargins(20, 20, 16, 16)
        head.setSpacing(10)
        head.addWidget(self.logo)
        head.addWidget(title)
        head.addStretch()

        self.theme_toggle = QPushButton()
        self.theme_toggle.setObjectName("themeToggle")
        self.theme_toggle.setToolTip("Darstellung umschalten (Wie Windows / Hell / Dunkel)")
        self.theme_toggle.clicked.connect(self._cycle_mode)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        side.setFixedWidth(NAV_WIDTH)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(0, 0, 0, 12)
        side_lay.setSpacing(4)
        side_lay.addLayout(head)
        side_lay.addWidget(self.nav, 1)
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(10, 0, 10, 0)
        toggle_row.addWidget(self.theme_toggle)
        side_lay.addLayout(toggle_row)

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(side)
        content = QWidget()
        content.setObjectName("contentArea")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(28, 22, 28, 16)
        c_lay.addWidget(self.stack)
        lay.addWidget(content, 1)
        self.setCentralWidget(central)
        self.setStatusBar(StatusBar())

        self.dashboard.open_tournament.connect(self.open_tournament)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_scheme_changed)
        self._refresh_chrome()
        self.nav.setCurrentRow(0)

    # ------------------------------------------------------------ theme
    def apply_theme(self, overrides: dict | None = None):
        theme.apply(QApplication.instance(), overrides)
        self._refresh_chrome()

    def _refresh_chrome(self):
        """Icons are pixmaps, so they are re-rendered in the current theme colors."""
        t = theme.current()
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            item.setIcon(theme.icon(item.data(ICON_ROLE)))
        self.logo.setPixmap(theme.pixmap("target", t["primary"], 26))
        mode = ss.get(ss.KEY_UI_THEME_MODE, theme.MODE_SYSTEM)
        _next, icon_name, label = MODE_CYCLE.get(mode, MODE_CYCLE[theme.MODE_SYSTEM])
        self.theme_toggle.setIcon(theme.icon(icon_name))
        self.theme_toggle.setText(f"  {label}")

    def _cycle_mode(self):
        mode = ss.get(ss.KEY_UI_THEME_MODE, theme.MODE_SYSTEM)
        ss.set_value(ss.KEY_UI_THEME_MODE, MODE_CYCLE.get(mode, MODE_CYCLE[theme.MODE_SYSTEM])[0])
        self.apply_theme()

    def _system_scheme_changed(self, _scheme):
        if ss.get(ss.KEY_UI_THEME_MODE, theme.MODE_SYSTEM) == theme.MODE_SYSTEM:
            self.apply_theme()

    # ------------------------------------------------------------ navigation
    def _navigate(self, current: QListWidgetItem, previous: QListWidgetItem | None):
        if current is None:
            return
        target = current.data(Qt.ItemDataRole.UserRole)
        if target == SETTINGS_KEY:
            self.open_settings()
            self.nav.blockSignals(True)
            self.nav.setCurrentItem(previous)
            self.nav.blockSignals(False)
            return
        self.stack.setCurrentIndex(target)   # views refresh themselves in showEvent

    def select_page(self, widget: QWidget):
        for row in range(self.nav.count()):
            if self.nav.item(row).data(Qt.ItemDataRole.UserRole) == self.stack.indexOf(widget):
                self.nav.setCurrentRow(row)
                return

    def open_tournament(self, tournament_id: int):
        self.select_page(self.tournaments)
        self.tournaments.open_tournament(tournament_id)

    def open_settings(self):
        dlg = SettingsDialog(self.apply_theme, self)
        dlg.exec()
        self.apply_theme()   # saved values, or revert an unsaved preview
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

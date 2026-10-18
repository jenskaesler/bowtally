# -*- coding: utf-8 -*-
"""Main window: navigation sidebar on the left, content stack on the right."""
from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (QApplication, QDialog, QHBoxLayout, QHeaderView, QLabel,
                               QListWidget, QListWidgetItem, QMainWindow, QPushButton,
                               QStackedWidget, QStyledItemDelegate, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import button, theme
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
BADGE_ROLE = Qt.ItemDataRole.UserRole + 2
# theme toggle: mode -> (next mode, icon, label)
MODE_CYCLE = {theme.MODE_SYSTEM: (theme.MODE_LIGHT, "monitor", "Wie Windows"),
              theme.MODE_LIGHT: (theme.MODE_DARK, "sun", "Hell"),
              theme.MODE_DARK: (theme.MODE_SYSTEM, "moon", "Dunkel")}
SHORTCUTS = [
    ("Strg+N", "Neu (Schütze, Klasse, Regelwerk, Turnier oder Teilnehmer zuweisen)"),
    ("Strg+F", "Suchfeld der aktuellen Ansicht"),
    ("Strg+S", "Speichern (Seitenpanel, Ergebniseingabe)"),
    ("Esc", "Seitenpanel schließen / Suche leeren / Eingabe verwerfen"),
    ("F5", "Ansicht neu laden"),
    ("F1", "Diese Übersicht"),
    ("Enter", "Ausgewählten Eintrag öffnen / Seitenpanel speichern"),
    ("Tab / Umschalt+Tab", "Ergebniseingabe: nächste / vorherige Scheibe"),
    ("Enter / ↓ / ↑", "Ergebniseingabe: nächster / vorheriger Teilnehmer"),
]


class _NavDelegate(QStyledItemDelegate):
    """Default item painting plus an orange dot for items with BADGE_ROLE set."""

    def paint(self, painter: QPainter, option, index):
        super().paint(painter, option, index)
        if index.data(BADGE_ROLE):
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.current()["warning"]))
            r = option.rect
            painter.drawEllipse(QRectF(r.right() - 22, r.center().y() - 4, 8, 8))
            painter.restore()


class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tastenkürzel")
        self.resize(560, 400)
        table = QTableWidget(len(SHORTCUTS), 2)
        table.setHorizontalHeaderLabels(["Taste", "Aktion"])
        table.verticalHeader().hide()
        table.setShowGrid(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for r, (key, text) in enumerate(SHORTCUTS):
            item = QTableWidgetItem(key)
            f = item.font()
            f.setBold(True)
            item.setFont(f)
            table.setItem(r, 0, item)
            table.setItem(r, 1, QTableWidgetItem(text))
        table.resizeColumnToContents(0)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Schließen", self.accept, "primary", "Übersicht schließen"))
        lay = QVBoxLayout(self)
        lay.addWidget(table)
        lay.addLayout(row)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BowTally")
        self.resize(1360, 840)

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
        self.nav.setItemDelegate(_NavDelegate(self.nav))
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
        c_lay.setContentsMargins(28, 22, 20, 16)
        c_lay.addWidget(self.stack)
        lay.addWidget(content, 1)
        self.setCentralWidget(central)
        self.status = StatusBar()
        self.status.helpRequested.connect(self.show_shortcuts)
        self.setStatusBar(self.status)

        self.dashboard.open_tournament.connect(self.open_tournament)
        self.dashboard.new_tournament.connect(self.new_tournament)
        self.tournaments.changed.connect(self.update_badges)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_scheme_changed)
        for keys, slot in ((QKeySequence.StandardKey.New, "shortcut_new"),
                           (QKeySequence.StandardKey.Find, "shortcut_find"),
                           (QKeySequence.StandardKey.Save, "shortcut_save"),
                           (QKeySequence(Qt.Key.Key_F5), "refresh")):
            QShortcut(keys, self, activated=lambda s=slot: self._dispatch(s))
        QShortcut(QKeySequence(Qt.Key.Key_F1), self, activated=self.show_shortcuts)
        self._refresh_chrome()
        self.update_badges()
        self.nav.setCurrentRow(0)

    # ------------------------------------------------------------ shortcuts
    def _dispatch(self, method: str):
        page = self.stack.currentWidget()
        if hasattr(page, method):
            getattr(page, method)()

    def show_shortcuts(self):
        ShortcutsDialog(self).exec()

    # ------------------------------------------------------------ theme
    def apply_theme(self, overrides: dict | None = None):
        theme.apply(QApplication.instance(), overrides)
        self._refresh_chrome()

    def _refresh_chrome(self):
        """Icons are pixmaps, so they are re-rendered in the current theme colors."""
        t = theme.current()
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            item.setIcon(theme.icon(item.data(ICON_ROLE), selected_color=t["on_primary"]))
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

    def update_badges(self):
        """Orange dot on 'Turniere' while a tournament is active."""
        active = bool(ts.list_tournaments("active"))
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == self.stack.indexOf(self.tournaments):
                item.setData(BADGE_ROLE, active)
                item.setToolTip("Mindestens ein Turnier ist aktiv" if active else "")

    # ------------------------------------------------------------ navigation
    def _navigate(self, current: QListWidgetItem, previous: QListWidgetItem | None):
        if current is None:
            return
        target = current.data(Qt.ItemDataRole.UserRole)
        page = self.stack.currentWidget()
        leaving_ok = target == SETTINGS_KEY or not hasattr(page, "close_drawer") \
            or page.close_drawer()
        if target == SETTINGS_KEY or not leaving_ok:
            if target == SETTINGS_KEY:
                self.open_settings()
            self.nav.blockSignals(True)
            self.nav.setCurrentItem(previous)
            self.nav.blockSignals(False)
            return
        self.stack.setCurrentIndex(target)   # views refresh themselves in showEvent
        self.update_badges()

    def select_page(self, widget: QWidget):
        for row in range(self.nav.count()):
            if self.nav.item(row).data(Qt.ItemDataRole.UserRole) == self.stack.indexOf(widget):
                self.nav.setCurrentRow(row)
                return

    def open_tournament(self, tournament_id: int, tab: str = ""):
        self.select_page(self.tournaments)
        self.tournaments.open_tournament(tournament_id, tab or None)

    def new_tournament(self):
        self.select_page(self.tournaments)
        self.tournaments.show_list()
        self.tournaments.list.new_item()

    def open_settings(self):
        dlg = SettingsDialog(self.apply_theme, self)
        dlg.exec()
        self.apply_theme()   # saved values, or revert an unsaved preview
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

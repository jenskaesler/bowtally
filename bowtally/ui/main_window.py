# -*- coding: utf-8 -*-
"""Main window: navigation sidebar on the left, content stack on the right."""
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QStackedWidget, QStyle, QVBoxLayout, QWidget)

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

        sp = QStyle.StandardPixmap
        entries = [
            ("Dashboard", sp.SP_ComputerIcon, self.dashboard),
            ("Schützen", sp.SP_DirHomeIcon, self.archers),
            ("Regelwerke", sp.SP_FileDialogDetailedView, self.rules),
            ("Bogenklassen", sp.SP_FileDialogListView, self.bow_classes),
            ("Turniere", sp.SP_DialogApplyButton, self.tournaments),
            ("Einstellungen", sp.SP_FileDialogInfoView, SETTINGS_KEY),
        ]
        self.nav = QListWidget()
        self.nav.setObjectName("navigation")
        self.nav.setIconSize(QSize(18, 18))
        for text, icon, target in entries:
            item = QListWidgetItem(self.style().standardIcon(icon), text)
            if target != SETTINGS_KEY:
                self.stack.addWidget(target)
                item.setData(Qt.ItemDataRole.UserRole, self.stack.indexOf(target))
            else:
                item.setData(Qt.ItemDataRole.UserRole, SETTINGS_KEY)
            self.nav.addItem(item)
        self.nav.currentItemChanged.connect(self._navigate)

        title = QLabel("BowTally")
        title.setObjectName("appTitle")
        side = QWidget()
        side.setFixedWidth(NAV_WIDTH)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(0, 0, 0, 0)
        side_lay.setSpacing(0)
        side_lay.addWidget(title)
        side_lay.addWidget(self.nav)

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(side)
        content = QWidget()
        content.setObjectName("contentArea")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(20, 16, 20, 12)
        c_lay.addWidget(self.stack)
        lay.addWidget(content, 1)
        self.setCentralWidget(central)
        self.setStatusBar(StatusBar())

        self.dashboard.open_tournament.connect(self.open_tournament)
        self.nav.setCurrentRow(0)

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

    @staticmethod
    def apply_theme(colors: dict | None = None):
        theme.apply(QApplication.instance(), colors)

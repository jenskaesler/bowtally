# -*- coding: utf-8 -*-
"""Main window: sidebar (tournament navigator + navigation) and content stack."""
from PySide6.QtCore import QRectF, QSettings, QSize, Qt
from PySide6.QtGui import QColor, QGuiApplication, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (QApplication, QDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPushButton, QSplitter, QStackedWidget,
                               QStyledItemDelegate, QToolButton,
                               QVBoxLayout, QWidget)

from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts
from bowtally.ui import busy, button, repolish, show_error, theme
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import Cell, DataTable
from bowtally.ui.components.status_chip import StatusChip, tournament_chip
from bowtally.ui.components.toast import Toast
from bowtally.ui.context import context
from bowtally.ui.dialogs.export_helper import FORMATS, open_path, run_export, tournament_sheets
from bowtally.ui.dialogs.settings_dialog import SettingsDialog
from bowtally.ui.views.archers_view import ArchersView
from bowtally.ui.views.bow_classes_view import BowClassesView
from bowtally.ui.views.dashboard import DashboardView
from bowtally.ui.views.guide_view import GuideView
from bowtally.ui.views.rules_view import RulesView
from bowtally.ui.views.tournaments_view import TournamentsView
from bowtally.ui.widgets.status_bar import StatusBar

NAV_WIDTH = 240
NAME_CHARS = 20
ICON_ROLE = Qt.ItemDataRole.UserRole + 1
BADGE_ROLE = Qt.ItemDataRole.UserRole + 2


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



class PhaseLogDialog(QDialog):
    def __init__(self, tournament_id: int, parent=None, back=None):
        super().__init__(parent)
        self.setWindowTitle("Phasenwechsel-Protokoll")
        self.resize(760, 380)
        table = DataTable(["Zeitpunkt", "Von", "Nach", "Erzwungen", "Warnungen"])
        entries = ts.list_phase_log(tournament_id)
        table.set_rows([[Cell(e.transitioned_at, text=f"{e.transitioned_at:%d.%m.%Y %H:%M}",
                              sort=str(e.transitioned_at)),
                         ts.PHASE_LABELS.get(e.from_phase, e.from_phase),
                         ts.PHASE_LABELS.get(e.to_phase, e.to_phase),
                         Cell(e.forced, chip=("Ja", "warning") if e.forced else ("Nein", "muted")),
                         Cell("; ".join(e.warnings_at_transition or []) or "–",
                              tooltip="\n".join(e.warnings_at_transition or []))]
                        for e in entries], [e.id for e in entries])
        row = QHBoxLayout()
        if back is not None:
            def _go_back():
                self.accept()
                back()
            row.addWidget(button("← Zur vorherigen Phase", _go_back, "danger",
                                 "Dialog schließen und Phase zurückwechseln"))
        row.addStretch()
        row.addWidget(button("Schließen", self.accept, "primary", "Protokoll schließen"))
        lay = QVBoxLayout(self)
        if not entries:
            lay.addWidget(QLabel("Noch keine Phasenwechsel.", objectName="pageSubtitle"))
        lay.addWidget(table, 1)
        lay.addLayout(row)


class TournamentPicker(QDialog):
    """Modal tournament list for 'Turnier wechseln'."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Turnier wechseln")
        self.resize(720, 460)
        self.chosen = None
        self.table = DataTable(["Datum", "Name", "Ort", "Phase", "Teilnehmer"])
        items = ts.list_tournaments()
        self.table.set_rows([[t.date, t.name, t.location,
                              Cell(t.phase, chip=tournament_chip(t.phase)), len(t.participants)]
                             for t in items], [t.id for t in items])
        self.table.activated.connect(self._choose)
        self.ok = button("Turnier öffnen", lambda: self._choose(self.table.selected_id()),
                         "primary", "Ausgewähltes Turnier öffnen (Enter)")
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(button("Abbrechen", self.reject, tooltip="Nicht wechseln"))
        row.addWidget(self.ok)
        lay = QVBoxLayout(self)
        lay.addWidget(self.table, 1)
        lay.addLayout(row)

    def _choose(self, tid):
        if tid is not None:
            self.chosen = tid
            self.accept()


class TournamentNavigator(QFrame):
    """Sidebar block of the active tournament: name, phase list, next-phase button."""

    def __init__(self, window: "MainWindow"):
        super().__init__(objectName="tournamentNav")
        self.window_ = window
        self.name = QLabel(objectName="navTournamentName")
        self.chip = StatusChip()
        self.close_btn = QToolButton(objectName="iconButton")
        self.close_btn.setToolTip("Turnier schließen (zurück zur Gesamtübersicht)")
        self.close_btn.clicked.connect(lambda: context.set(None))
        head = QHBoxLayout()
        head.addWidget(self.name, 1)
        head.addWidget(self.close_btn)
        sub = QHBoxLayout()
        sub.addWidget(self.chip)
        sub.addStretch()
        switch = QPushButton("Wechseln", objectName="link")
        switch.setToolTip("Anderes Turnier öffnen")
        switch.clicked.connect(window.switch_tournament)
        sub.addWidget(switch)
        self.phases = QGridLayout()
        self.phases.setHorizontalSpacing(8)
        self.phases.setVerticalSpacing(3)
        self._btn_tdash = QPushButton("Turnier-Dashboard", objectName="link")
        self._btn_tdash.setIconSize(QSize(16, 16))
        self._btn_tdash.clicked.connect(
            lambda: (window.stack.setCurrentWidget(window.dashboard),
                     window.dashboard.show_tournament()))
        self._btn_tours_nav = QPushButton("Turnier-Details", objectName="link")
        self._btn_tours_nav.setIconSize(QSize(16, 16))
        self._btn_tours_nav.clicked.connect(lambda: window.select_page(window.tournaments))
        self._btn_guide_nav = QPushButton("Leitfaden", objectName="link")
        self._btn_guide_nav.setIconSize(QSize(16, 16))
        self._btn_guide_nav.clicked.connect(lambda: window.select_page(window.guide))
        self.next_btn = QPushButton("", objectName="link")
        self.next_btn.setIconSize(QSize(16, 16))
        self.next_btn.clicked.connect(window.next_phase)
        self.log_btn = button("Phasenwechsel-Protokoll",
                              lambda: PhaseLogDialog(context.tournament_id, window,
                                                     back=window.prev_phase).exec(),
                              "danger",
                              "Alle Phasenwechsel anzeigen, rückwärts navigieren")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 4, 14, 12)
        lay.setSpacing(6)
        lay.addLayout(head)
        lay.addLayout(sub)
        lay.addWidget(self._btn_tdash)
        lay.addWidget(self._btn_tours_nav)
        lay.addWidget(self._btn_guide_nav)
        lay.addWidget(self.next_btn)
        lay.addSpacing(4)
        lay.addLayout(self.phases)
        lay.addSpacing(4)
        lay.addWidget(self.log_btn)

    def refresh(self):
        t = context.tournament()
        self.setVisible(t is not None)
        tcol = theme.current()
        self._btn_tdash.setIcon(theme.icon("dashboard"))
        self._btn_tours_nav.setIcon(theme.icon("target"))
        self._btn_guide_nav.setIcon(theme.icon("rules"))
        self.next_btn.setIcon(theme.icon("arrow-right"))
        if t is None:
            return
        self.close_btn.setIcon(theme.icon("x"))
        name = t.name if len(t.name) <= NAME_CHARS else t.name[:NAME_CHARS] + "…"
        self.name.setText(name)
        self.name.setToolTip(t.name)
        self.chip.set_tournament_status(t.phase)
        while self.phases.count():
            item = self.phases.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        dates = ts.phase_dates(t.id)
        current = ts.phase_index(t.phase)
        for i, key in enumerate(ts.PHASES):
            state = "done" if i < current else "current" if i == current else "todo"
            if t.phase == "closed" and key == "closed":
                state = "done"
            icon = QLabel()
            icon.setPixmap(theme.pixmap(
                {"done": "check", "current": "target", "todo": "circle"}[state],
                {"done": tcol["success"], "current": tcol["success"],
                 "todo": tcol["text2"]}[state], 14))
            label = QLabel(ts.PHASE_LABELS[key], objectName="phaseLabel")
            label.setProperty("state", "current" if i == current else state)
            repolish(label)
            when = dates.get(key) if i <= current else None
            date_label = QLabel(f"{when:%d.%m.}" if when else ("aktuell" if i == current
                                                               else ""), objectName="phaseDate")
            self.phases.addWidget(icon, i, 0)
            self.phases.addWidget(label, i, 1)
            self.phases.addWidget(date_label, i, 2, Qt.AlignmentFlag.AlignRight)
        self.phases.setColumnStretch(1, 1)
        nxt = ts.next_phase(t.phase)
        self.next_btn.setVisible(nxt is not None)
        if nxt:
            self.next_btn.setText(f"Nächste Phase: {ts.PHASE_LABELS[nxt]}")
            self.next_btn.setToolTip("Voraussetzungen prüfen und in die nächste Phase wechseln")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BowTally")
        self.resize(1400, 880)
        context.restore()

        self.dashboard = DashboardView()
        self.guide = GuideView()
        self.archers = ArchersView()
        self.rules = RulesView()
        self.bow_classes = BowClassesView()
        self.tournaments = TournamentsView()
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")

        entries = [
            ("Dashboard", "dashboard", self.dashboard),
            ("Leitfaden", "rules", self.guide),
            ("Turniere", "target", self.tournaments),
            ("Schützen", "users", self.archers),
            ("Regelwerke", "file", self.rules),
            ("Bogenklassen", "layers", self.bow_classes),
        ]
        self.nav = self._nav_list()
        for text, icon_name, target in entries:
            item = QListWidgetItem(text)
            item.setData(ICON_ROLE, icon_name)
            self.stack.addWidget(target)
            item.setData(Qt.ItemDataRole.UserRole, self.stack.indexOf(target))
            self.nav.addItem(item)
        self.nav.currentItemChanged.connect(self._navigate)
        self._nav_item(self.guide).setHidden(True)  # always in tournament section, never in main nav
        self.settings_nav = self._nav_list()
        settings_item = QListWidgetItem("Einstellungen")
        settings_item.setData(ICON_ROLE, "settings")
        self.settings_nav.addItem(settings_item)
        help_nav_item = QListWidgetItem("Hilfe")
        help_nav_item.setData(ICON_ROLE, "help")
        self.settings_nav.addItem(help_nav_item)
        about_item = QListWidgetItem("Über BowTally")
        about_item.setData(ICON_ROLE, "info")
        self.settings_nav.addItem(about_item)
        self.settings_nav.setFixedHeight(132)
        self.settings_nav.itemClicked.connect(self._settings_clicked)

        self.logo = QLabel()
        self.logo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logo.setToolTip("Zur Hauptübersicht")
        self.logo.mousePressEvent = lambda _e: self.select_page(self.dashboard)
        self.app_title_label = QLabel("BowTally")
        self.app_title_label.setObjectName("appTitle")
        self._head_widget = QWidget()
        head = QHBoxLayout(self._head_widget)
        head.setContentsMargins(20, 20, 16, 12)
        head.setSpacing(10)
        head.addWidget(self.logo)
        head.addWidget(self.app_title_label)
        head.addStretch()

        self.navigator = TournamentNavigator(self)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(0, 0, 0, 12)
        side_lay.setSpacing(4)
        side_lay.addWidget(self._head_widget)
        side_lay.addWidget(self.navigator)
        side_lay.addWidget(self.nav, 1)
        side_lay.addWidget(self.settings_nav)

        content = QWidget()
        content.setObjectName("contentArea")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(28, 22, 20, 16)
        c_lay.addWidget(self.stack)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("mainSplitter")
        self.splitter.setHandleWidth(2)
        self.splitter.addWidget(side)
        self.splitter.addWidget(content)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([NAV_WIDTH, 1160])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self._side_widget = side

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.splitter)
        self.setCentralWidget(central)
        self.status = StatusBar()
        self.status.helpRequested.connect(self.show_help)
        self.setStatusBar(self.status)

        self.dashboard.open_tournament.connect(self.open_tournament)
        self.dashboard.new_tournament.connect(self.new_tournament)
        self.dashboard.action.connect(self.run_action)
        self.dashboard.navigate.connect(self._navigate_to)
        self.guide.action.connect(self.run_action)
        self.tournaments.openRequested.connect(lambda tid: self.open_tournament(tid))
        self.tournaments.changed.connect(self._data_changed)
        context.changed.connect(self._context_changed)
        context.dataChanged.connect(self._data_changed)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_scheme_changed)
        for keys, slot in ((QKeySequence.StandardKey.New, "shortcut_new"),
                           (QKeySequence.StandardKey.Find, "shortcut_find"),
                           (QKeySequence.StandardKey.Save, "shortcut_save"),
                           (QKeySequence(Qt.Key.Key_F5), "refresh")):
            QShortcut(keys, self, activated=lambda s=slot: self._dispatch(s))
        QShortcut(QKeySequence(Qt.Key.Key_F1), self, activated=self.show_help)
        self._refresh_chrome()
        self._context_changed(context.tournament_id, initial=True)
        self._refresh_title()

    @staticmethod
    def _nav_list() -> QListWidget:
        nav = QListWidget()
        nav.setObjectName("navigation")
        nav.setIconSize(QSize(18, 18))
        nav.setItemDelegate(_NavDelegate(nav))
        nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav.setMinimumWidth(0)
        return nav

    # ------------------------------------------------------------ shortcuts
    def _dispatch(self, method: str):
        page = self.stack.currentWidget()
        if hasattr(page, method):
            getattr(page, method)()

    def show_help(self, section: str = ""):
        from bowtally.ui.dialogs.help_dialog import HelpDialog
        dlg = HelpDialog(self)
        if section:
            dlg.show_section(section)
        dlg.exec()

    # ------------------------------------------------------------ theme
    def apply_theme(self, overrides: dict | None = None):
        theme.apply(QApplication.instance(), overrides)
        self._refresh_chrome()

    def _refresh_chrome(self):
        """Icons are pixmaps, so they are re-rendered in the current theme colors."""
        t = theme.current()
        for nav in (self.nav, self.settings_nav):
            for row in range(nav.count()):
                item = nav.item(row)
                item.setIcon(theme.icon(item.data(ICON_ROLE), selected_color=t["on_primary"]))
        self.logo.setPixmap(theme.pixmap("target", t["primary"], 26))
        self.navigator.refresh()

    def _refresh_title(self):
        club_name = (ss.get_club_profile().get("club_name") or "").strip()
        self.setWindowTitle(f"BowTally – {club_name}" if club_name else "BowTally")

    def _system_scheme_changed(self, _scheme):
        if ss.get(ss.KEY_UI_THEME_MODE, theme.MODE_SYSTEM) == theme.MODE_SYSTEM:
            self.apply_theme()

    # ------------------------------------------------------------ tournament context
    def _nav_item(self, widget: QWidget) -> QListWidgetItem | None:
        for row in range(self.nav.count()):
            if self.nav.item(row).data(Qt.ItemDataRole.UserRole) == self.stack.indexOf(widget):
                return self.nav.item(row)
        return None

    def _context_changed(self, tournament_id, initial: bool = False):
        self._nav_item(self.tournaments).setHidden(tournament_id is not None)
        self.navigator.refresh()
        self.update_badges()
        if tournament_id is None:
            self.tournaments.show_list()
            if initial or self.stack.currentWidget() is self.guide:
                self.select_page(self.dashboard)
        elif initial:
            self.tournaments.open_tournament(tournament_id)
            self.select_page(self.guide)
        current = self.stack.currentWidget()
        if hasattr(current, "refresh") and not initial:
            current.refresh()

    def _data_changed(self):
        self.navigator.refresh()
        self.update_badges()

    def update_badges(self):
        """Orange dot on 'Turniere': active tournament fully booked or scoring in progress."""
        reasons = []
        t = context.tournament()
        if t is not None:
            cap = ts._capacity(t)
            if cap.is_full:
                reasons.append(f"Maximale Teilnehmerzahl erreicht ({cap.active_count}/"
                               f"{cap.max})")
        if any(x.phase == "shooting" for x in ts.list_tournaments("shooting")):
            reasons.append("Ein Turnier ist in der Phase „Schießen“")
        item = self._nav_item(self.tournaments)
        item.setData(BADGE_ROLE, bool(reasons))
        item.setToolTip("\n".join(reasons))

    def open_tournament(self, tournament_id: int, tab: str = ""):
        """Make the tournament active. Without tab the guide is shown first."""
        if context.tournament_id != tournament_id:
            context.set(tournament_id)
        self.tournaments.open_tournament(tournament_id, tab or None)
        self.select_page(self.tournaments if tab else self.guide)

    def switch_tournament(self):
        picker = TournamentPicker(self)
        if picker.exec() and picker.chosen is not None:
            self.open_tournament(picker.chosen)

    def new_tournament(self):
        self.select_page(self.tournaments)
        self.tournaments.show_list()
        self.tournaments.list.new_item()

    def prev_phase(self):
        t = context.tournament()
        if t is None:
            return
        target = ts.prev_phase(t.phase)
        if target is None:
            return
        label = ts.PHASE_LABELS[target]
        if not ConfirmDialog.ask(
                self, f"Phasenwechsel rückgängig: {label}",
                f"Die Phase wird auf '{label}' zurückgesetzt.\n\n"
                "Dieser Schritt wird im Protokoll als erzwungener Wechsel festgehalten.",
                "Zurücksetzen", destructive=True):
            return
        try:
            ts.transition_phase_backward(t.id)
        except Exception as exc:
            show_error(self, exc, "Phasenwechsel fehlgeschlagen")
            return
        Toast.show(self, f"Phase zurückgesetzt: {label}", Toast.WARNING)
        context.notify()
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()

    def next_phase(self):
        t = context.tournament()
        target = ts.next_phase(t.phase) if t else None
        if target is None:
            return
        label = ts.PHASE_LABELS[target]
        # check first, change only after the user agreed
        conds = ts.get_phase_conditions(t.id, target)
        errors = [c.message for c in conds if not c.ok and c.severity == "blocker"]
        warnings = [c.message for c in conds if not c.ok and c.severity == "warning"]
        if errors:
            QMessageBox.critical(self, "Phasenwechsel nicht möglich",
                                 f"Der Wechsel zu „{label}“ ist noch nicht möglich:\n\n"
                                 + "\n".join(f"• {e}" for e in errors))
            return
        closing = "\n\nDanach sind keine Eingaben und Änderungen mehr möglich." \
            if target == "closed" else ""
        if warnings:
            if not ConfirmDialog.ask(
                    self, f"Wechsel zu „{label}“?",
                    "Folgende Punkte sind noch offen:\n\n"
                    + "\n".join(f"• {w}" for w in warnings)
                    + "\n\nTrotzdem fortfahren? Der Wechsel wird mit diesen Hinweisen "
                      "protokolliert." + closing, "Trotzdem wechseln",
                    destructive=target == "closed"):
                return
        elif target == "closed" and not ConfirmDialog.ask(
                self, "Turnier abschließen?", closing.strip(), "Abschließen"):
            return
        res = ts.transition_phase(t.id, target, force=True)
        if res.errors:
            show_error(self, ValueError("\n".join(res.errors)), "Phasenwechsel fehlgeschlagen")
            return
        Toast.show(self, f"Phase geändert: {label}", Toast.SUCCESS)
        context.notify()
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()

    def _navigate_to(self, key: str):
        targets = {"rules": self.rules, "bow_classes": self.bow_classes,
                   "archers": self.archers, "tournaments": self.tournaments}
        if key in targets:
            self.select_page(targets[key])

    # ------------------------------------------------------------ direct links
    def run_action(self, key: str):
        t = context.tournament()
        if t is None:
            return
        tabs = {"participants": "participants", "fees": "fees", "checkin": "checkin",
                "scoring": "scoring", "results": "results"}
        if key in tabs:
            self.open_tournament(t.id, tabs[key])
        elif key == "guide":
            self.select_page(self.guide)
        elif key == "revenue":
            self.select_page(self.dashboard)
        elif key in ("edit", "edit_contact", "edit_bank", "edit_classes", "edit_fees"):
            _pages = {"edit": 0, "edit_contact": 6, "edit_bank": 6,
                      "edit_classes": 2, "edit_fees": 5}
            self.tournaments.open_tournament(t.id)
            self.tournaments.detail.edit_at_page(_pages[key])
            context.notify()
        elif key == "announcement":
            self._generate_announcement(t.id)
        elif key == "print_checkin":
            self._print_checkin_list(t.id)
        elif key == "scoring_incomplete":
            self.open_tournament(t.id, "scoring")
            self.tournaments.detail.scoring.show_incomplete()
        elif key == "results_pdf":
            self.open_tournament(t.id, "results")
            self.tournaments.detail.results._create_pdf()
        elif key == "export_all":
            run_export(self, f"Turnier_{t.name}{FORMATS[0][2]}", FORMATS[0][1],
                       tournament_sheets(t.id))

    def _generate_announcement(self, tournament_id: int):
        from bowtally.reports.announcement import generate_announcement_pdf
        try:
            with busy():
                path = generate_announcement_pdf(tournament_id)
        except Exception as exc:
            show_error(self, exc, "Ausschreibung konnte nicht erstellt werden")
            return
        Toast.show(self, "Ausschreibung erstellt", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, path)))
        context.notify()

    def _print_checkin_list(self, tournament_id: int):
        from bowtally.reports.participant_list import build_checkin_list
        try:
            with busy():
                path = build_checkin_list(tournament_id)
        except Exception as exc:
            show_error(self, exc, "Einschreibeliste konnte nicht erstellt werden")
            return
        Toast.show(self, "Einschreibeliste erstellt", Toast.SUCCESS,
                   ("Öffnen", lambda: open_path(self, path)))

    # ------------------------------------------------------------ navigation
    def _navigate(self, current: QListWidgetItem, previous: QListWidgetItem | None):
        if current is None:
            return
        page = self.stack.currentWidget()
        if hasattr(page, "close_drawer") and not page.close_drawer():
            self.nav.blockSignals(True)
            self.nav.setCurrentItem(previous)
            self.nav.blockSignals(False)
            return
        self.stack.setCurrentIndex(current.data(Qt.ItemDataRole.UserRole))
        if self.stack.currentWidget() is self.dashboard:
            self.dashboard.show_global()
        elif self.stack.currentWidget() is self.tournaments and context.tournament_id:
            self.tournaments.open_tournament(context.tournament_id)
        self.update_badges()

    def _settings_clicked(self, item):
        self.settings_nav.clearSelection()
        if item.data(ICON_ROLE) == "info":
            from bowtally.ui.dialogs.about_dialog import AboutDialog
            AboutDialog(self).exec()
        elif item.data(ICON_ROLE) == "help":
            self.show_help()
        else:
            self.open_settings()

    def select_page(self, widget: QWidget):
        item = self._nav_item(widget)
        if item is None:
            return
        if self.nav.currentItem() is item:
            self.stack.setCurrentWidget(widget)
        else:
            self.nav.setCurrentItem(item)

    def open_settings(self):
        dlg = SettingsDialog(self.apply_theme, self)
        dlg.exec()
        self.apply_theme()   # saved values, or revert an unsaved preview
        self._refresh_title()
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_settings_restored'):
            self._settings_restored = True
            self._restore_settings()

    def _restore_settings(self):
        s = QSettings("BowTally", "BowTally")
        if geom := s.value("window/geometry"):
            self.restoreGeometry(geom)
        if state := s.value("window/splitter"):
            self.splitter.restoreState(state)

    def _save_settings(self):
        s = QSettings("BowTally", "BowTally")
        s.setValue("window/geometry", self.saveGeometry())
        s.setValue("window/splitter", self.splitter.saveState())

    def closeEvent(self, event):
        page = self.stack.currentWidget()
        if hasattr(page, "close_drawer") and not page.close_drawer():
            event.ignore()
            return
        self._save_settings()
        if ss.get_bool("backup_on_close"):
            try:
                from bowtally.services import backup_service as bs
                bs.backup_local()
            except Exception:
                pass
        super().closeEvent(event)


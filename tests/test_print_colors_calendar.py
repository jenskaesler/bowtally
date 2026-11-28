# -*- coding: utf-8 -*-
from datetime import date

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine, seed
from bowtally.database.models import AppSetting
from bowtally.services import settings_service as ss


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])


def test_new_print_color_takes_the_custom_ui_color(db):
    ss.set_value(ss.KEY_COLOR_PRIMARY, "#123456")
    with engine.session_scope() as s:
        s.delete(s.get(AppSetting, ss.KEY_PRINT_COLOR_PRIMARY))
    with engine.session_scope() as s:
        seed.run(s)
    assert ss.get(ss.KEY_PRINT_COLOR_PRIMARY) == "#123456"


def test_print_colors_sit_in_general_tab(db):
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    dlg = SettingsDialog(lambda *_: None)
    field = dlg.color_fields[ss.KEY_PRINT_COLOR_BORDER]
    page = dlg._stack.widget(dlg._page_index["behavior"])
    assert page.isAncestorOf(field)          # Turnierverwaltung -> Allgemein, not Design
    field.set_value("#111111")
    dlg.color_fields[ss.KEY_COLOR_BORDER].set_value("#222222")
    dlg._reset_colors("print_color_")
    assert field.value() == ss.DEFAULTS[ss.KEY_PRINT_COLOR_BORDER]
    assert dlg.color_fields[ss.KEY_COLOR_BORDER].value() == "#222222"


def test_calendar_double_click_presets_wizard_date(db):
    from bowtally.ui.dialogs.tournament_wizard import TournamentWizard
    from bowtally.ui.views.calendar_view import _DayCell
    got = []
    cell = _DayCell(date(2027, 5, 8), [])
    cell.newRequested.connect(got.append)
    cell.mouseDoubleClickEvent(None)
    assert got == [date(2027, 5, 8)]
    assert TournamentWizard(day=got[0]).date.date().toPython() == date(2027, 5, 8)


def test_dashboard_counts_builtin_and_custom(db):
    from bowtally.ui.views.dashboard import GlobalDashboard
    dash = GlobalDashboard()
    dash.refresh()
    assert "Standard" in dash.rules_split.text() and "eigene" in dash.bow_split.text()
    assert not dash._cards["rules"].icon_lbl.pixmap().isNull()


def test_backup_prune_keeps_newest_by_count(tmp_path):
    import os
    from bowtally.services.backup_service import _prune_by_count
    for i in range(5):
        f = tmp_path / f"bowtally_backup_2026-01-0{i + 1}-000000.zip"
        f.write_text("x")
        os.utime(f, (1_000_000 + i, 1_000_000 + i))
    (tmp_path / "other.zip").write_text("keep")
    _prune_by_count(tmp_path, 2)
    assert sorted(f.name for f in tmp_path.iterdir()) == [
        "bowtally_backup_2026-01-04-000000.zip", "bowtally_backup_2026-01-05-000000.zip",
        "other.zip"]


def test_dashboard_empty_texts_and_counts(db):
    from bowtally.ui.views.dashboard import GlobalDashboard
    dash = GlobalDashboard()
    dash.refresh()
    assert dash.club_count.text() == "noch keine Schützen"
    assert dash.helpers_lbl.text() == "noch keine Mitglieder"
    assert dash.active_lbl.text() == "laufend von 0 Turnieren insgesamt"


def test_logo_alone_enables_save(db, tmp_path, monkeypatch):
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QFileDialog
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    logo = tmp_path / "logo.png"
    img = QImage(20, 20, QImage.Format.Format_RGB32)
    img.fill(QColor("red"))
    img.save(str(logo))
    dlg = SettingsDialog(lambda *_: None)
    assert not dlg._save_btn.isEnabled()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(logo), ""))
    dlg._browse_logo()
    assert dlg._save_btn.isEnabled()
    dlg._save_settings()
    assert ss.get_club_profile()["logo_path"].endswith("logo.png")


@pytest.mark.parametrize("year_view", [False, True])
def test_calendar_right_click_offers_new_tournament(db, monkeypatch, year_view):
    import types
    from PySide6.QtWidgets import QLabel
    import bowtally.ui.views as views
    from bowtally.ui.views import calendar_view as cv
    # QMenu.exec cannot be patched on the PySide class -> replace the menu helper
    monkeypatch.setattr(views, "menu", lambda parent, entries: types.SimpleNamespace(
        exec=lambda *_: entries[0][1]()))
    got = []
    if year_view:
        view = cv._MiniMonth(2027, 5, {})
        view.newRequested.connect(got.append)
        day = next(w for w in view.findChildren(QLabel) if w.text() == "8")
        day.contextMenuEvent(None)
    else:
        cell = cv._DayCell(date(2027, 5, 8), [])
        cell.newRequested.connect(got.append)
        cell.contextMenuEvent(None)
    assert got == [date(2027, 5, 8)]


def test_year_view_double_click_creates_a_tournament_and_cancels_the_day_click(db):
    import types
    from PySide6.QtWidgets import QLabel
    from bowtally.ui.views import calendar_view as cv
    d = date(2027, 5, 8)
    view = cv._MiniMonth(2027, 5, {d: [types.SimpleNamespace(phase="draft")]})
    new, clicked = [], []
    view.newRequested.connect(new.append)
    view.dayClicked.connect(clicked.append)
    day = next(w for w in view.findChildren(QLabel) if w.text() == "8")
    day.mousePressEvent(None)
    day.mouseDoubleClickEvent(None)
    assert new == [d] and not view._click.isActive() and not clicked


def test_tables_align_only_currency_right(db):
    from PySide6.QtCore import Qt
    from bowtally.ui.components.data_table import Cell, DataTable
    table = DataTable(["Name", "Anzahl", "Preis"])
    table.set_rows([["Scheibe", 3, Cell(12.5, text="12,50 €")]], [1])
    right = [bool(table.table.item(0, c).textAlignment() & Qt.AlignmentFlag.AlignRight)
             for c in range(3)]
    assert right == [False, False, True]

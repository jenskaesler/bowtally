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


def test_design_tab_shows_print_colors(db):
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    dlg = SettingsDialog(lambda *_: None)
    assert ss.KEY_PRINT_COLOR_BORDER in dlg.color_fields


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

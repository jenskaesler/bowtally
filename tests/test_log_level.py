# -*- coding: utf-8 -*-
import json
import logging
import sqlite3

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import settings_service as ss
from bowtally.ui.components.confirm_dialog import ConfirmDialog


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    root = logging.getLogger()
    level = root.level
    yield
    root.setLevel(level)


@pytest.fixture
def dialog():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    return SettingsDialog(lambda *_: None)


def test_default_is_info_and_levels_are_mapped():
    assert ss.get(ss.KEY_LOG_LEVEL) == "info"
    assert [ss.LOG_LEVELS[v] for v in ss.OPTIONS[ss.KEY_LOG_LEVEL]] == \
        [logging.INFO, logging.WARNING, logging.DEBUG]


def test_apply_log_level_sets_the_root_logger():
    ss.apply_log_level("warning")
    assert logging.getLogger().level == logging.WARNING
    ss.set_value(ss.KEY_LOG_LEVEL, "debug")
    ss.apply_log_level()
    assert logging.getLogger().level == logging.DEBUG
    ss.apply_log_level("unbekannt")
    assert logging.getLogger().level == logging.INFO


def test_debug_leaves_a_warning_in_the_log(caplog):
    with caplog.at_level(logging.WARNING):
        ss.apply_log_level("debug")
    assert "Debug-Logging ist aktiv" in caplog.text


def _logbuch_backup():
    from bowtally.database.models import ActivityLog
    from bowtally.services import backup_service
    ss.set_value(ss.KEY_LOG_LEVEL, "warning")
    with engine.session_scope() as s:
        s.add(ActivityLog(log_type="score", description="Treffer", tournament_id=1,
                          participant_id=2, detail_json={"ring": 10}))
    with engine.session_scope() as s:
        return json.loads(json.dumps(backup_service.create_backup(s, "test")))


def _restored_values(tmp_path, monkeypatch, backup, via_zip):
    from bowtally.services import backup_service
    db_path = tmp_path / "restored.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    if via_zip:
        pytest.importorskip("pyzipper")
        zip_path = tmp_path / "b.zip"
        backup_service.save_backup_to_zip(backup, zip_path, None, "Geheim-1234")
        backup_service.restore(str(zip_path), "Geheim-1234")
    else:
        backup_service._restore_impl(backup)
    with sqlite3.connect(db_path) as con:
        level = con.execute("SELECT value FROM app_settings WHERE key='log_level'").fetchone()
        logs = con.execute("SELECT log_type, description, tournament_id, participant_id, "
                           "detail_json, created_at FROM activity_log").fetchall()
    return level, logs


@pytest.mark.parametrize("via_zip", [False, True])
def test_log_level_and_logbuch_survive_backup_and_restore(tmp_path, monkeypatch, via_zip):
    level, logs = _restored_values(tmp_path, monkeypatch, _logbuch_backup(), via_zip)
    assert level == ("warning",)
    (log_type, description, tournament_id, participant_id, detail, created_at), = logs
    assert (log_type, description, tournament_id, participant_id) == ("score", "Treffer", 1, 2)
    assert json.loads(detail) == {"ring": 10} and created_at


def test_old_backup_without_log_level_keeps_the_default(tmp_path, monkeypatch):
    backup = _logbuch_backup()
    backup["data"]["app_settings"] = [r for r in backup["data"]["app_settings"]
                                      if r["key"] != ss.KEY_LOG_LEVEL]
    level, logs = _restored_values(tmp_path, monkeypatch, backup, via_zip=False)
    assert level == ("info",) and len(logs) == 1


def _select_debug(dialog):
    combo = dialog.value_widgets[ss.KEY_LOG_LEVEL]
    assert [combo.itemText(i) for i in range(combo.count())] == ["Info", "Warnung", "Debug"]
    assert combo.currentData() == "info"
    combo.setCurrentIndex(combo.findData("debug"))
    return combo


def test_debug_needs_confirmation_and_refusal_saves_nothing(dialog, monkeypatch):
    monkeypatch.setattr(ConfirmDialog, "ask", lambda *a, **k: False)
    combo = _select_debug(dialog)
    logging.getLogger().setLevel(logging.INFO)
    dialog._save_settings()
    assert combo.currentData() == "info"
    assert ss.get(ss.KEY_LOG_LEVEL) == "info"
    assert logging.getLogger().level == logging.INFO


def test_confirmed_debug_is_saved_and_applied(dialog, monkeypatch):
    monkeypatch.setattr(ConfirmDialog, "ask", lambda *a, **k: True)
    _select_debug(dialog)
    dialog._save_settings()
    assert ss.get(ss.KEY_LOG_LEVEL) == "debug"
    assert logging.getLogger().level == logging.DEBUG


def test_warning_is_saved_without_a_question(dialog, monkeypatch):
    monkeypatch.setattr(ConfirmDialog, "ask", lambda *a, **k: pytest.fail("no question expected"))
    combo = dialog.value_widgets[ss.KEY_LOG_LEVEL]
    combo.setCurrentIndex(combo.findData("warning"))
    dialog._save_settings()
    assert ss.get(ss.KEY_LOG_LEVEL) == "warning"
    assert logging.getLogger().level == logging.WARNING

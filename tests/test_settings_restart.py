# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import backup_service as bs
from bowtally.ui.components.confirm_dialog import ConfirmDialog


@pytest.fixture
def dialog(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    from PySide6.QtWidgets import QApplication, QFileDialog
    QApplication.instance() or QApplication([])
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: ("backup.zip", ""))
    monkeypatch.setattr(bs, "restore", lambda *a, **k: None)
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    return SettingsDialog(lambda *_: None)


def _restore(dialog, monkeypatch, answers):
    asked = iter(answers)
    monkeypatch.setattr(ConfirmDialog, "ask", lambda *a, **k: next(asked))
    restarts = []
    monkeypatch.setattr(dialog, "_restart_app", lambda: restarts.append(True))
    dialog._do_restore(bs)
    return restarts


def test_restart_button_restarts_the_app_after_restore(dialog, monkeypatch):
    assert _restore(dialog, monkeypatch, [True, True]) == [True]


def test_declining_the_restart_keeps_the_app_running(dialog, monkeypatch):
    assert _restore(dialog, monkeypatch, [True, False]) == []

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


def test_logfile_button_opens_the_log(dialog, monkeypatch):
    from PySide6.QtWidgets import QPushButton
    from bowtally.ui.dialogs import settings_dialog
    opened = []
    monkeypatch.setattr(settings_dialog, "open_path", lambda _parent, path: opened.append(path))
    button = next(b for b in dialog.findChildren(QPushButton) if b.text() == "Logfile öffnen")
    button.click()
    assert opened == [config.LOG_PATH]


def test_boxes_on_the_general_page_are_equally_wide(dialog):
    from PySide6.QtWidgets import QApplication, QGroupBox
    dialog.resize(1200, 900)
    dialog.show()
    dialog._stack.setCurrentIndex(dialog._page_index["general"])
    QApplication.processEvents()
    general = dialog._stack.widget(dialog._page_index["general"])
    boxes = {box.title(): box.width() for box in general.findChildren(QGroupBox)}
    assert {"Oberfläche", "Navigation", "Update-Prüfung", "Speicherorte"} <= set(boxes)
    assert len(set(boxes.values())) == 1


def test_interface_settings_live_on_the_general_system_page(dialog):
    pages = [key for _title, items in dialog._NAV_GROUPS for key, _label in items]
    assert "ui" not in pages
    from PySide6.QtWidgets import QGroupBox
    general = dialog._stack.widget(dialog._page_index["general"])
    assert "Oberfläche" in [box.title() for box in general.findChildren(QGroupBox)]

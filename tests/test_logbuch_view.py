# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from datetime import datetime

from bowtally import config
from bowtally.database import engine
from bowtally.database.models import BackupLog
from bowtally.services import logbuch_service as ls
from bowtally.database.engine import session_scope


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")


def _add_backups(count: int, success: bool = True):
    with session_scope() as s:
        for i in range(count):
            s.add(BackupLog(created_at=datetime(2026, 1, 1, 12, i % 60), file_name=f"b{i}.zip",
                            target="local", success=success, error_message=None if success else "kaputt"))


def _view():
    from PySide6.QtWidgets import QApplication
    from bowtally.ui.views.logbuch_view import LogbuchView
    QApplication.instance() or QApplication([])
    view = LogbuchView()
    view.refresh()
    return view


def test_entry_is_one_row_with_four_columns():
    _add_backups(2)
    table = _view()._table
    assert [table.horizontalHeaderItem(c).text() for c in range(4)] == \
        ["Zeit", "Typ", "Meldung", "Kontext"]
    assert table.rowCount() == 2
    assert table.item(0, 1).text() == "Backup" and table.item(0, 2).text() == "Backup erstellt"
    assert "b1.zip" in table.item(0, 3).text() or "b0.zip" in table.item(0, 3).text()


def test_search_filters_rows():
    _add_backups(1)
    _add_backups(1, success=False)
    view = _view()
    view._search.setText("fehlgeschlagen")
    view._reload()
    assert view._table.rowCount() == 1 and view._table.item(0, 2).text() == "Backup fehlgeschlagen"


def test_load_more_appends_rows():
    _add_backups(ls.PAGE_SIZE + 5)
    view = _view()
    assert view._table.rowCount() == ls.PAGE_SIZE and not view._load_more_btn.isHidden()
    view._load_more()
    assert view._table.rowCount() == ls.PAGE_SIZE + 5

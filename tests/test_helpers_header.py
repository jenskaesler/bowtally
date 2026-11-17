# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])


def test_header_actions_run_from_search_to_new_helper():
    from PySide6.QtWidgets import QPushButton
    from bowtally.ui.components.search_bar import SearchBar
    from bowtally.ui.views.helpers_view import HelpersView
    actions = HelpersView().header.actions
    widgets = [actions.itemAt(i).widget() for i in range(actions.count())]
    assert isinstance(widgets[0], SearchBar)
    texts = [w.text() for w in widgets if isinstance(w, QPushButton)]
    assert len(texts) == 4 and texts[1:] == ["Helferliste drucken", "Aus Mitgliederkartei",
                                             "Neuer Helfer"]
    assert "xport" in texts[0]

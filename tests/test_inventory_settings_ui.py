# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import inventory_service as inv


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")


@pytest.fixture
def dialog():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    return SettingsDialog(lambda *_: None)


def _names(dialog):
    return [dialog._category_list.item(i).text() for i in range(dialog._category_list.count())]


def test_categories_can_be_added_renamed_and_deleted(dialog, monkeypatch):
    answers = iter(["Ziele", "Tische", "Möbel"])
    monkeypatch.setattr(dialog, "_ask_text", lambda *a, **k: next(answers))
    dialog._add_category()
    dialog._add_category()
    dialog._category_list.setCurrentRow(1)
    dialog._rename_category()
    assert _names(dialog) == ["Möbel", "Tische"]

    from bowtally.ui.components.confirm_dialog import ConfirmDialog
    monkeypatch.setattr(ConfirmDialog, "ask", lambda *a, **k: True)
    dialog._category_list.setCurrentRow(0)
    dialog._delete_category()
    assert _names(dialog) == ["Tische"]


def test_deleting_a_used_category_moves_its_items(dialog, monkeypatch):
    old, new = inv.save_category("Alt"), inv.save_category("Neu")
    inv.save_item({"name": "Scheibe", "category_id": old.id, "unit_price": 5, "quantity": 2})
    dialog._reload_categories()
    dialog._category_list.setCurrentRow(_names(dialog).index("Alt"))
    monkeypatch.setattr(dialog, "_ask_text", lambda *a, **k: "Neu")
    dialog._delete_category()
    assert _names(dialog) == ["Neu"]
    assert inv.count_items_in_category(new.id) == 1


def test_deleting_the_only_used_category_is_refused(dialog, monkeypatch):
    only = inv.save_category("Allein")
    inv.save_item({"name": "Tisch", "category_id": only.id, "unit_price": 1, "quantity": 1})
    dialog._reload_categories()
    dialog._category_list.setCurrentRow(0)
    shown = []
    monkeypatch.setattr("bowtally.ui.dialogs.settings_dialog.show_error",
                        lambda parent, exc, *a: shown.append(exc))
    dialog._delete_category()
    assert shown and _names(dialog) == ["Allein"]

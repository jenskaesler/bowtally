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
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _dialog(record=None):
    from bowtally.ui.views.inventory_view import InventoryItemDialog
    return InventoryItemDialog(record)


def test_tabs_and_total_is_calculated_live_and_read_only(app):
    from PySide6.QtWidgets import QTabWidget
    dialog = _dialog()
    tabs = dialog.findChild(QTabWidget)
    assert [tabs.tabText(i) for i in range(tabs.count())] == \
        ["Stammdaten", "Notizen", "Dokumente", "Reparaturkosten"]
    total = dialog.form.fields["total"]
    assert total.widget.isReadOnly() and total.value() == "0,00 €"
    dialog.form.fields["unit_price"].set_value(12.5)
    dialog.form.fields["quantity"].set_value(2)
    assert total.value() == "25,00 €"


def test_new_item_is_saved_with_category_and_notes(app):
    category = inv.save_category("Tische")
    dialog = _dialog()
    dialog.form.fields["name"].set_value("Klapptisch")
    dialog.form.fields["category_id"].set_value(category.id)
    dialog.form.fields["unit_price"].set_value(30)
    dialog.form.fields["quantity"].set_value(4)
    dialog.notes_form.fields["notes"].set_value("Garage")
    assert dialog._is_dirty() and dialog._do_save()
    item = inv.list_items()[0]
    assert (item.category_id, inv.item_total(item), item.notes) == (category.id, 120, "Garage")


def test_item_without_categories_is_saved_without_category(app):
    dialog = _dialog()
    dialog.form.fields["name"].set_value("Stuhl")
    assert dialog._do_save() and inv.list_items()[0].category_id is None


def test_category_filter_of_the_list(app):
    from bowtally.ui.views.inventory_view import InventoryView
    tables = inv.save_category("Tische")
    inv.save_category("Ziele")
    inv.save_item({"name": "Klapptisch", "category_id": tables.id, "unit_price": 30})
    inv.save_item({"name": "Bär", "unit_price": 80})
    view = InventoryView()
    view.refresh()
    combo = view._category_filter
    assert [combo.itemText(i) for i in range(combo.count())] == ["Alle", "Tische", "Ziele"]
    assert sorted(i.name for i in view._items.values()) == ["Bär", "Klapptisch"]
    combo.setCurrentIndex(combo.findData(tables.id))
    assert [i.name for i in view._items.values()] == ["Klapptisch"]


def test_repairs_can_be_added_and_need_date_and_cost(app):
    from datetime import date
    from bowtally.ui.views.inventory_view import _RepairDialog
    item = inv.save_item({"name": "3D-Bär", "unit_price": 80})
    dialog = _dialog(item)
    assert dialog._repairs.rowCount() == 0
    assert not hasattr(_dialog(), "_repairs")        # new item: hint instead of table
    repair = _RepairDialog(item.id)
    repair.form.fields["date"].set_value(None)
    assert not repair.form.validate()
    repair.form.fields["date"].set_value(date(2026, 11, 1))
    repair.form.fields["description"].set_value("Riss geklebt")
    repair.form.fields["cost"].set_value(12.5)
    assert repair._do_save()
    dialog._reload_repairs()
    assert dialog._repairs.rowCount() == 1 and dialog._repairs.item(0, 2).text() == "12,50 €"
    assert [(r.description, r.cost) for r in inv.list_repairs(item.id)] == [("Riss geklebt", 12.5)]

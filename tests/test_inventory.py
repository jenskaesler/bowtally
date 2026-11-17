# -*- coding: utf-8 -*-
import sqlite3
from datetime import date

import pytest

pytest.importorskip("pyzipper")

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from bowtally import config
from bowtally.database import engine
from bowtally.database.engine import session_scope
from bowtally.services import ValidationError
from bowtally.services import backup_service as bs
from bowtally.services import course_service as cs
from bowtally.services import inventory_service as inv
from bowtally.services import master_data_service as md
from bowtally.services import scoring_service
from bowtally.services import tournament_service as ts

PASSWORD = "Geheim-1234"


@pytest.fixture(autouse=True)
def appdata(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'i.db').as_posix()}")
    return tmp_path / "appdata"


def _item(name="Scheibe 80", price=2.5, quantity=10, **extra):
    return inv.save_item({"name": name, "unit_price": price, "quantity": quantity, **extra})


def _tournament():
    rule = scoring_service.list_rules()[0]
    return ts.save_tournament({"name": "T", "date": date(2030, 1, 1), "num_targets": 3,
                               "shots_per_target": 1, "scoring_rule_id": rule.id,
                               "start_groups": "A"}, [md.list_bow_classes()[0].id])


def test_category_with_items_is_protected_unless_items_are_moved():
    ziele, tische = inv.save_category("Ziele"), inv.save_category("Tische")
    item = _item(category_id=ziele.id)
    with pytest.raises(ValidationError):
        inv.delete_category(ziele.id)
    with pytest.raises(ValidationError):
        inv.save_category("ziele")                      # duplicate name, case-insensitive
    assert inv.save_category("Zielscheiben", ziele.id).name == "Zielscheiben"
    inv.delete_category(ziele.id, move_to=tische.id)
    assert [c.name for c in inv.list_categories()] == ["Tische"]
    assert inv.list_items(category_id=tische.id)[0].id == item.id


def test_total_price_and_inventory_value():
    a, b = _item(price=2.5, quantity=10), _item("Tisch", price=30, quantity=2, use_in_course=True)
    assert inv.item_total(a) == 25 and inv.inventory_total_value() == 85
    assert [i.id for i in inv.list_items(course_only=True)] == [b.id]
    with pytest.raises(ValidationError):
        inv.save_item({"name": "Ohne Preis"})
    with pytest.raises(ValidationError):
        inv.save_item({"name": " ", "unit_price": 1})


def test_repairs_need_date_and_cost_and_do_not_change_the_value():
    item = _item()
    for bad in ({"cost": 5}, {"date": date(2026, 1, 1)}):
        with pytest.raises(ValidationError):
            inv.save_repair(bad, item_id=item.id)
    repair = inv.save_repair({"date": date(2026, 1, 1), "cost": 12.5, "performed_by": "Jens"},
                             item_id=item.id)
    assert [r.id for r in inv.list_repairs(item.id)] == [repair.id]
    assert inv.inventory_total_value() == 25
    inv.delete_repair(repair.id)
    assert inv.list_repairs(item.id) == []


def test_files_live_in_the_app_folder_and_vanish_with_the_item(tmp_path, appdata):
    item = _item()
    source = tmp_path / "Rechnung.pdf"
    source.write_bytes(b"pdf")
    stored = inv.add_inventory_file(item.id, source)
    path = inv.inventory_file_path(stored)
    assert path.read_bytes() == b"pdf" and path.is_relative_to(appdata / "inventory_files")
    inv.remove_inventory_file(stored.id)
    assert not path.exists()
    inv.add_inventory_file(item.id, source)
    inv.delete_item(item.id)
    assert not (appdata / "inventory_files" / str(item.id)).exists()


def test_course_items_report_shortfall_and_split_the_costs():
    t = _tournament()
    scheibe = _item(price=2.5, quantity=10)
    cs.save_course_item({"inventory_item_id": scheibe.id, "quantity": 12}, tournament_id=t.id)
    cs.save_course_item({"name": "Zelt mieten", "unit_price": 40, "quantity": 2}, tournament_id=t.id)
    items = cs.list_course_items(t.id)
    assert [cs.stock_shortfall(i) for i in items] == [2, 0]
    assert cs.one_off_cost(t.id) == 80 and cs.stock_goods_value(t.id) == 30
    inv.save_item({"name": "Scheibe 80", "unit_price": 3, "quantity": 20}, scheibe.id)
    assert cs.stock_goods_value(t.id) == 36                 # current price, not the whole stock
    with pytest.raises(ValidationError):
        cs.save_course_item({"inventory_item_id": scheibe.id, "quantity": 0}, tournament_id=t.id)
    copy = _tournament()
    cs.copy_targets(t.id, copy.id)
    assert len(cs.list_course_items(copy.id)) == 2
    inv.delete_item(scheibe.id)                             # SET NULL keeps the posting
    assert cs.stock_goods_value(t.id) == 30 and cs.stock_shortfall(cs.list_course_items(t.id)[0]) == 0


def test_import_creates_categories_and_respects_the_strategy():
    rec = {"name": "Stuhl", "category": "Möbel", "unit_price": 8.0, "quantity": 4,
           "use_in_course": False}
    assert inv.import_items([rec], "skip")["created"] == 1
    assert inv.import_items([{**rec, "quantity": 9}], "skip")["skipped"] == 1
    assert inv.import_items([{"name": "Stuhl", "quantity": 9}], "update")["updated"] == 1
    (stuhl,) = inv.list_items()
    assert (stuhl.quantity, stuhl.unit_price, stuhl.category.name) == (9, 8.0, "Möbel")
    assert inv.EXPORT_HEADERS[:2] == ["Bezeichnung", "Kategorie"]
    assert inv.export_rows([stuhl])[0][:2] == ["Stuhl", "Möbel"]


def _restore(backup, tmp_path, monkeypatch, before_restore=lambda: None):
    zip_path = tmp_path / "b.zip"
    bs.save_backup_to_zip(backup, zip_path, None, PASSWORD)
    before_restore()
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "restored.db")
    bs.restore(str(zip_path), PASSWORD)
    return sqlite3.connect(tmp_path / "restored.db")


def test_backup_roundtrip_contains_inventory_files_and_course_items(tmp_path, appdata, monkeypatch):
    category = inv.save_category("Ziele")
    item = _item(category_id=category.id, shop_url="https://shop.example/x")
    inv.save_repair({"date": date(2026, 2, 3), "cost": 4}, item_id=item.id)
    source = tmp_path / "foto.jpg"
    source.write_bytes(b"jpg")
    stored = inv.add_inventory_file(item.id, source)
    t = _tournament()
    cs.save_course_item({"inventory_item_id": item.id, "quantity": 3}, tournament_id=t.id)
    with session_scope() as session:
        backup = bs.create_backup(session, "test")
    changed = lambda: inv.inventory_file_path(stored).write_bytes(b"geaendert")

    with _restore(backup, tmp_path, monkeypatch, changed) as con:
        assert con.execute("SELECT name FROM inventory_categories").fetchall() == [("Ziele",)]
        assert con.execute("SELECT name, shop_url, unit_price FROM inventory_items").fetchall() == \
            [("Scheibe 80", "https://shop.example/x", 2.5)]
        assert con.execute("SELECT cost FROM inventory_repairs").fetchall() == [(4.0,)]
        assert con.execute("SELECT quantity FROM course_items").fetchall() == [(3,)]
    assert inv.inventory_file_path(stored).read_bytes() == b"jpg"


def test_backup_with_the_old_inventory_columns_can_still_be_restored(tmp_path, monkeypatch):
    with session_scope() as session:
        backup = bs.create_backup(session, "test")
    backup["data"]["inventory_items"] = [{
        "id": 1, "item_type": "target_face", "name": "Alt", "manufacturer": "X", "quantity": 2,
        "condition": "gut", "notes": None, "active": True}]
    with _restore(backup, tmp_path, monkeypatch) as con:
        assert con.execute("SELECT name, quantity, unit_price FROM inventory_items").fetchall() \
            == [("Alt", 2, 0.0)]


def test_migration_replaces_the_old_inventory_with_an_empty_new_one(tmp_path):
    path = tmp_path / "old.db"
    old_engine = create_engine(f"sqlite:///{path.as_posix()}")
    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    with old_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0036_archer_files")
    old_engine.dispose()
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO inventory_items (item_type, name) VALUES ('target_face', 'Alt')")

    engine.init_database(f"sqlite:///{path.as_posix()}")

    assert inv.list_items() == [] and inv.list_categories() == []
    assert _item().unit_price == 2.5

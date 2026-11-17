# -*- coding: utf-8 -*-
from datetime import date

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import course_service as cs
from bowtally.services import inventory_service as inv
from bowtally.services import scoring_service
from bowtally.services import tournament_service as ts


@pytest.fixture(autouse=True)
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'c.db').as_posix()}")
    from bowtally.services import master_data_service as md
    from bowtally.ui.context import context
    rule = scoring_service.list_rules()[0]
    t = ts.save_tournament({"name": "T", "date": date(2030, 1, 1), "num_targets": 3,
                            "scoring_rule_id": rule.id},
                           [bc.id for bc in md.list_bow_classes()])
    context.set(t.id)
    yield t
    context.set(None)


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _rows(view):
    table = view.table.table
    return {table.item(r, 0).text(): [table.item(r, c).text() for c in range(table.columnCount())]
            for r in range(table.rowCount())}


def test_material_view_shows_coverage_and_separate_costs(app, db):
    from bowtally.ui.views.course_view import CourseMaterialView
    target = inv.save_item({"name": "Scheibe", "unit_price": 2.5, "quantity": 10, "use_in_course": True})
    stool = inv.save_item({"name": "Hocker", "unit_price": 5, "quantity": 4, "use_in_course": True})
    cs.save_course_item({"inventory_item_id": target.id, "quantity": 12}, tournament_id=db.id)
    cs.save_course_item({"inventory_item_id": stool.id, "quantity": 4}, tournament_id=db.id)
    cs.save_course_item({"name": "Zelt mieten", "unit_price": 40, "quantity": 2}, tournament_id=db.id)
    view = CourseMaterialView()
    view.refresh()
    rows = _rows(view)
    assert rows["Scheibe"][2:] == ["10", "Es fehlen 2", "2,50 €", "30,00 €", "Inventar"]
    assert rows["Hocker"][3] == "gedeckt"
    assert rows["Zelt mieten"][2:4] == ["–", "–"] and rows["Zelt mieten"][6] == "Einmalposten"
    assert view.totals.text() == ("Kosten Einmalartikel: 80,00 €   |   "
                                  "Warenwert Bestandsinventar: 50,00 €")


def test_dialogs_add_edit_and_remove_material(app, db, monkeypatch):
    from bowtally.ui.components.confirm_dialog import ConfirmDialog
    from bowtally.ui.views.course_view import CourseItemDialog, CourseMaterialView
    inv.save_item({"name": "Scheibe", "unit_price": 2.5, "quantity": 10, "use_in_course": True})
    inv.save_item({"name": "Stuhl", "unit_price": 8, "quantity": 4})          # not flagged

    dialog = CourseItemDialog()
    combo = dialog.form.fields["inventory_item_id"].widget
    assert [combo.itemText(i) for i in range(combo.count())] == ["Scheibe (Bestand 10)"]
    dialog.form.fields["quantity"].set_value(3)
    assert dialog._do_save()

    one_off = CourseItemDialog(one_off=True)
    one_off.form.fields["name"].set_value("Zelt")
    one_off.form.fields["unit_price"].set_value(40)
    assert one_off._do_save()
    assert {i.name: i.quantity for i in cs.list_course_items(db.id)} == {"Scheibe": 3, "Zelt": 1}

    edit = CourseItemDialog(cs.list_course_items(db.id)[0])
    assert not edit.form.fields["inventory_item_id"].widget.isEnabled()
    edit.form.fields["quantity"].set_value(5)
    assert edit._is_dirty() and edit._do_save()
    assert cs.list_course_items(db.id)[0].quantity == 5

    view = CourseMaterialView()
    view.refresh()
    view.table.select_ids([cs.list_course_items(db.id)[1].id])
    monkeypatch.setattr(ConfirmDialog, "ask", staticmethod(lambda *a, **k: True))
    view.delete_item()
    assert [i.name for i in cs.list_course_items(db.id)] == ["Scheibe"]


def test_course_tab_holds_targets_and_material(app):
    from bowtally.ui.views.course_view import CoursePage
    page = CoursePage()
    assert [page.tabText(i) for i in range(page.count())] == ["Scheiben", "Material"]

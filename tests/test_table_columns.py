# -*- coding: utf-8 -*-
import json

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from bowtally.ui.components import data_table as dt
from bowtally.ui.components.data_table import Column, DataTable, optional


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Isolated QSettings: tests never touch the real user settings."""
    from bowtally import config
    from bowtally.database import engine
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")   # theme colors
    QApplication.instance() or QApplication([])
    path = str(tmp_path / "s.ini")
    monkeypatch.setattr(dt, "QSettings",
                        lambda *_a: QSettings(path, QSettings.Format.IniFormat))
    return lambda: QSettings(path, QSettings.Format.IniFormat)


COLUMNS = [Column("a", "A"), Column("b", "B"), optional("x", "X"), optional("y", "Y")]


def _visible(table: DataTable) -> list[str]:
    h = table.table.horizontalHeader()
    cols = sorted(range(table.table.columnCount()), key=h.visualIndex)
    return [table.headers[c] for c in cols if not table.table.isColumnHidden(c)]


def test_defaults_menu_locks_default_columns(settings):
    t = DataTable(COLUMNS, table_key="t")
    t.set_rows([["1", "2", "3", "4"]], [1])
    assert _visible(t) == ["A", "B"]
    actions = {a.text(): a for a in t.column_menu().actions()}
    assert actions["A"].isChecked() and not actions["A"].isEnabled()
    assert not actions["X"].isChecked() and actions["X"].isEnabled()
    actions["Y"].setChecked(True)                      # takes effect at once
    assert _visible(t) == ["A", "B", "Y"]


def test_order_and_visibility_are_saved_and_restored(settings):
    t = DataTable(COLUMNS, table_key="t")
    t.column_menu().actions()[2].setChecked(True)      # X on
    h = t.table.horizontalHeader()
    h.moveSection(h.visualIndex(2), 0)                 # X to the front, a default column moves too
    s = settings()
    assert json.loads(s.value("TableColumns/t/visible_optional")) == ["x"]
    assert json.loads(s.value("TableColumns/t/order")) == ["x", "a", "b", "y"]
    again = DataTable(COLUMNS, table_key="t")
    assert _visible(again) == ["X", "A", "B"]
    assert DataTable(COLUMNS, table_key="other").headers == ["A", "B", "X", "Y"]
    assert _visible(DataTable(COLUMNS, table_key="other")) == ["A", "B"]


def test_hidden_columns_do_not_match_the_search(settings):
    t = DataTable(COLUMNS, table_key="t")
    t.set_rows([["eins", "zwei", "geheim", ""]], [1])
    t.apply_filter("geheim")
    assert t.visible_ids() == []
    t.column_menu().actions()[2].setChecked(True)
    t.apply_filter("geheim")
    assert t.visible_ids() == [1]


def test_grip_column_stays_first_and_new_columns_follow_saved_order(settings):
    t = DataTable(COLUMNS, table_key="r", reorderable=True)
    h = t.table.horizontalHeader()
    h.moveSection(h.visualIndex(0), 3)                 # try to move the drag grip
    assert h.visualIndex(0) == 0
    t.set_headers(COLUMNS + [optional("z", "Z")])     # e.g. a changed rule: state applied again
    assert t.headers[-1] == "Z" and t.table.isColumnHidden(5)


def test_damaged_settings_fall_back_to_defaults(settings):
    s = settings()
    s.setValue("TableColumns/t/visible_optional", "{kaputt")
    s.sync()
    assert _visible(DataTable(COLUMNS, table_key="t")) == ["A", "B"]


def test_views_offer_optional_fields(settings):
    from bowtally.ui.views.archers_view import HEADERS, ArchersView
    view = ArchersView()
    view.refresh()
    assert view.table.table_key == "schuetzen"
    assert view.table.headers[:len(HEADERS)] == HEADERS
    assert "E-Mail" in view.table.headers and _visible(view.table) == HEADERS


def test_every_view_delivers_a_value_per_column(settings):
    import datetime
    from bowtally.services import inventory_service as inv, master_data_service as md
    from bowtally.services import member_service as ms, participant_service as ps
    from bowtally.services import settings_service as ss, tournament_service as ts
    from bowtally.ui.context import context
    classes = md.list_bow_classes()
    t = ts.save_tournament({"name": "T", "date": datetime.date.today(), "num_targets": 1,
                            "scoring_rule_id": int(ss.get("default_scoring_rule_id"))},
                           [bc.id for bc in classes])
    ps.register_walk_in(t.id, {"first_name": "Max", "last_name": "Muster", "club": "BSV"},
                        classes[0].id, None, True)
    ms.create_member({"member_number": "1", "first_name": "Eva", "last_name": "Beispiel"})
    inv.save_item({"name": "Scheibe", "unit_price": 10, "quantity": 2})
    context.set(t.id)
    try:
        from bowtally.ui.views.archers_view import ArchersView
        from bowtally.ui.views.bow_classes_view import BowClassesView
        from bowtally.ui.views.checkin_view import CheckinView
        from bowtally.ui.views.inventory_view import InventoryView
        from bowtally.ui.views.members_view import MembersView
        from bowtally.ui.views.participants_view import ParticipantsView
        from bowtally.ui.views.rules_view import RulesView
        from bowtally.ui.views.tournaments_view import TournamentList
        views = [cls() for cls in (ArchersView, BowClassesView, InventoryView, MembersView,
                                   TournamentList, RulesView, ParticipantsView, CheckinView)]
        for view in views:
            if hasattr(view, "set_tournament"):
                view.set_tournament(ts.get_tournament(t.id))
            elif hasattr(view, "refresh"):
                view.refresh()
            else:                                      # RulesView: tabs load when shown
                view._tab_rules.refresh()
        tables = [tbl for view in views for tbl in view.findChildren(DataTable)]
        filled = {tbl.table_key for tbl in tables if tbl.table.rowCount()}
        assert {"schuetzen", "mitglieder", "inventar", "turniere", "teilnehmer"} <= filled
        for tbl in tables:
            assert tbl.table_key, tbl.headers
            for r in range(tbl.table.rowCount()):      # a value for every column
                assert tbl.table.item(r, tbl.table.columnCount() - 1) is not None, tbl.table_key
    finally:
        context.set(None)

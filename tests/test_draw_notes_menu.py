# -*- coding: utf-8 -*-
import datetime

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def make_tournament(tmp_path, monkeypatch, app):
    from bowtally import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    from bowtally.database.engine import init_database
    init_database()
    from bowtally.services import master_data_service as md, settings_service as ss
    from bowtally.services import tournament_service as ts

    def make(**extra):
        return ts.save_tournament({"name": "T", "date": datetime.date.today(), "num_targets": 1,
                                   "scoring_rule_id": int(ss.get("default_scoring_rule_id")),
                                   **extra}, [bc.id for bc in md.list_bow_classes()])
    return make


@pytest.mark.parametrize("use_draw", [True, False])
def test_draw_task_and_menu_only_with_use_draw(make_tournament, use_draw):
    from bowtally.services import tournament_service as ts
    from bowtally.ui.views.guide_view import phase_tasks
    from bowtally.ui.views.participants_view import ParticipantsView
    t = make_tournament(use_draw=use_draw)
    assert ts.get_tournament(t.id).use_draw is use_draw
    t = ts.get_tournament(t.id)
    t.phase = "checkin"
    assert any(x.link == "draw" for x in phase_tasks(t)) is use_draw
    view = ParticipantsView()
    view.set_tournament(ts.get_tournament(t.id))
    assert view._act_draw.isVisible() is use_draw


def test_notes_from_wizard_go_to_internal_notes(make_tournament):
    from bowtally.services import tournament_service as ts
    t = make_tournament(internal_notes="Nur intern")
    assert ts.get_tournament(t.id).internal_notes == "Nur intern"


def test_menu_has_separator_before_remove(app):
    from bowtally.ui.views import menu
    m = menu(None, [("Bestätigen", lambda: None, True), None, ("Entfernen", lambda: None, True),
                    None, ("E-Mail", lambda: None, True)])
    labels = ["-" if a.isSeparator() else a.text() for a in m.actions()]
    assert labels == ["Bestätigen", "-", "E-Mail", "-", "Entfernen"]


def test_tab_order(app):
    from bowtally.ui.views.tournaments_view import TABS
    assert TABS[:3] == ["participants", "prizes", "helpers"]


def test_certificates_one_page_per_place(make_tournament, monkeypatch, tmp_path):
    import types
    from bowtally.reports import certificates as cert
    from bowtally.services import master_data_service as md
    t = make_tournament(name="Ein sehr langer Turniername " * 4)
    bc = md.list_bow_classes()[0]
    entry = lambda r: types.SimpleNamespace(rank=r, name="Max Mustermann", total=100 - r)
    monkeypatch.setattr(cert.rs, "compute_ranking",
                        lambda tid, **k: {bc.id: [entry(1), entry(2), entry(3), entry(4)]})
    pdf = cert.build_certificates(t.id, tmp_path / "u.pdf")
    assert pdf.read_bytes().count(b"/Type /Page\n") + pdf.read_bytes().count(b"/Type /Page ") == 3

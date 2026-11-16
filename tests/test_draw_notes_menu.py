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


def test_sidebar_helpers_stay_global_with_open_tournament(make_tournament):
    from bowtally.ui.context import context
    from bowtally.ui.views.helpers_view import GLOBAL_HEADERS, HelpersView
    t = make_tournament()
    context.set(t.id)
    try:
        sidebar, tab = HelpersView(), HelpersView(tournament_mode=True)
        sidebar.refresh()
        tab.refresh()
        assert sidebar._tid is None and sidebar._btn_from_master.isHidden()
        assert sidebar.table.headers == GLOBAL_HEADERS
        assert tab._tid == t.id and not tab._btn_from_master.isHidden()
        assert tab.table.headers != GLOBAL_HEADERS
    finally:
        context.set(None)


def test_settings_close_asks_only_when_dirty(make_tournament, monkeypatch):
    from bowtally.ui.components import confirm_dialog
    from bowtally.ui.dialogs.settings_dialog import SettingsDialog
    asked = []
    answer = {"discard": False}
    monkeypatch.setattr(confirm_dialog.ConfirmDialog, "ask",
                        staticmethod(lambda *a, **k: asked.append(1) or answer["discard"]))
    dlg = SettingsDialog(apply_theme=lambda: None)
    dlg.show()
    dlg._close_dialog()                                   # nothing changed: closes, no question
    assert not dlg.isVisible() and not asked

    dlg = SettingsDialog(apply_theme=lambda: None)
    dlg.show()
    edit = next(iter(dlg.club_edits.values()))
    edit.setText("geändert")
    assert dlg._save_btn.isEnabled()
    dlg._close_dialog()                                   # declined: stays open
    dlg.close()                                           # X button: stays open, asks once
    assert dlg.isVisible() and len(asked) == 2
    answer["discard"] = True
    dlg.close()                                           # discard: closes
    assert not dlg.isVisible() and len(asked) == 3


def test_wizard_has_no_second_custom_footer_button(make_tournament):
    from PySide6.QtWidgets import QWizard
    from bowtally.ui.dialogs.tournament_wizard import TournamentWizard
    wiz = TournamentWizard()
    assert not wiz.testOption(QWizard.WizardOption.HaveCustomButton2)


def test_internal_notes_shown_in_guide_when_closed_and_on_dashboard(make_tournament):
    from PySide6.QtWidgets import QLabel, QPlainTextEdit
    from bowtally.database.engine import session_scope
    from bowtally.database.models import Tournament
    from bowtally.services import tournament_service as ts
    from bowtally.ui.views.dashboard import TournamentDashboard
    from bowtally.ui.views.guide_view import GuideView
    t = make_tournament(internal_notes="Intern: Schlüssel beim Platzwart")
    dash = TournamentDashboard()
    card = dash._phase_card(ts.get_tournament(t.id))
    assert any(lbl.text() == "Intern: Schlüssel beim Platzwart" for lbl in card.findChildren(QLabel))
    with session_scope() as s:
        s.get(Tournament, t.id).phase = "closed"
        s.get(Tournament, t.id).status = "closed"
    from bowtally.ui.context import context
    context.set(t.id)
    try:
        guide = GuideView()
        guide.refresh()
        notes = [e for e in guide.findChildren(QPlainTextEdit) if e.isReadOnly()]
        assert [e.toPlainText() for e in notes] == ["Intern: Schlüssel beim Platzwart"]
    finally:
        context.set(None)


def test_burger_button_with_menu_has_no_qt_menu_indicator(app):
    from PySide6.QtWidgets import QMenu
    from bowtally.ui import burger_button
    b = burger_button("x", menu=QMenu())
    assert b.menu() is None and b.size().width() == b.size().height() == 34

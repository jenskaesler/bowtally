# -*- coding: utf-8 -*-
import datetime

import pytest

pytest.importorskip("PySide6")

from bowtally import config
from bowtally.database import engine
from bowtally.services import ValidationError
from bowtally.services import announcement_link_service as als


@pytest.fixture
def tid(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'd.db').as_posix()}")
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from bowtally.services import master_data_service as md, settings_service as ss
    from bowtally.services import tournament_service as ts
    return ts.save_tournament({"name": "T", "date": datetime.date.today(), "num_targets": 1,
                               "scoring_rule_id": int(ss.get("default_scoring_rule_id"))},
                              [bc.id for bc in md.list_bow_classes()]).id


def test_crud_order_and_several_per_platform(tid):
    a = als.save_link({"platform": "facebook", "url": " https://fb.example/1 "}, None, tid)
    b = als.save_link({"platform": "facebook", "url": "https://fb.example/2"}, None, tid)
    c = als.save_link({"platform": "custom", "platform_label": "Newsletter",
                       "url": "https://n.example"}, None, tid)
    assert [lk.id for lk in als.list_links(tid)] == [a.id, b.id, c.id]
    assert als.list_links(tid)[0].url == "https://fb.example/1"
    assert als.platform_name(c) == "Newsletter" and als.platform_name(a) == "Facebook"
    als.save_link({"platform": "website", "platform_label": "ignored", "url": "https://w"},
                  a.id, tid)
    edited = als.list_links(tid)[0]
    assert edited.platform == "website" and edited.platform_label is None
    als.delete_link(b.id)
    assert [lk.id for lk in als.list_links(tid)] == [a.id, c.id]


@pytest.mark.parametrize("data", [{"platform": "custom", "url": "https://x"},
                                  {"platform": "website", "url": "  "},
                                  {"platform": "", "url": "https://x"}])
def test_validation(tid, data):
    with pytest.raises(ValidationError):
        als.save_link(data, None, tid)


def test_links_go_with_tournament_and_into_backup(tid):
    from bowtally import __version__
    from bowtally.services import backup_service as bs
    from bowtally.services import tournament_service as ts
    als.save_link({"platform": "instagram", "url": "https://ig.example"}, None, tid)
    with engine.session_scope() as s:
        data = bs.create_backup(s, __version__)["data"]
    assert data["announcement_links"][0]["url"] == "https://ig.example"
    ts.delete_tournament(tid)
    assert als.list_links(tid) == []


def test_dialog_live_preview_and_save(tid):
    from bowtally.ui.dialogs.announcement_link_dialog import AnnouncementLinkDialog
    dlg = AnnouncementLinkDialog(tid)
    assert dlg._preview.pixmap().isNull()
    dlg._platform.setCurrentIndex(dlg._platform.findData("custom"))
    assert not dlg._label_field.isHidden()
    dlg._label.setText("Flyer")
    dlg._url.setText("https://example.org/turnier")
    assert not dlg._preview.pixmap().isNull()
    assert dlg._do_save()
    assert als.platform_name(als.list_links(tid)[0]) == "Flyer"


def test_dashboard_card_in_every_phase(tid):
    from PySide6.QtWidgets import QLabel
    from bowtally.services import tournament_service as ts
    from bowtally.ui.context import context
    from bowtally.ui.views.dashboard import TournamentDashboard
    als.save_link({"platform": "mein_bogenturnier", "url": "https://mbt.example"}, None, tid)
    context.set(tid)
    try:
        for phase in ts.PHASES:
            with engine.session_scope() as s:
                from bowtally.database.models import Tournament
                s.get(Tournament, tid).phase = phase
            dash = TournamentDashboard()
            dash.refresh()
            texts = [w.text() for w in dash.findChildren(QLabel)]
            assert "Ausschreibungslinks" in texts, phase
            assert any("mbt.example" in t for t in texts), phase
    finally:
        context.set(None)

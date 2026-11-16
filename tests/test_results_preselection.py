# -*- coding: utf-8 -*-
import datetime

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_notify_results_archer_is_preselected(tmp_path, monkeypatch, app):
    from bowtally import config
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    from bowtally.database.engine import init_database
    init_database()
    from bowtally.services import master_data_service as md, settings_service as ss
    from bowtally.services import tournament_service as ts

    yes = md.save_archer({"first_name": "Nina", "last_name": "N", "email": "n@x.de",
                          "notify_results": True})
    no = md.save_archer({"first_name": "Tom", "last_name": "T", "email": "t@x.de"})
    t = ts.save_tournament({"name": "T", "date": datetime.date.today(), "num_targets": 1,
                            "scoring_rule_id": int(ss.get("default_scoring_rule_id"))},
                           [bc.id for bc in md.list_bow_classes()])
    ts.add_participants(t.id, [yes.id, no.id])

    from bowtally.ui.views.results_view import _SendResultsDialog
    dlg = _SendResultsDialog(t.id, {}, None)
    state = {}
    for i in range(dlg.lst.count()):
        item = dlg.lst.item(i)
        state[item.data(0x0100).archer.last_name] = item.checkState().name
    assert state == {"N": "Checked", "T": "Unchecked"}

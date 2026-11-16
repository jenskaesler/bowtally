# -*- coding: utf-8 -*-
import os
from datetime import date

import pytest
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bowtally.database import engine
from bowtally.reports.announcement import generate_announcement_pdf
from bowtally.reports.rules_pdf import build_rules_pdf
from bowtally.services import master_data_service as md
from bowtally.services import scoring_service as sc
from bowtally.services import settings_service as ss
from bowtally.services import tournament_service as ts


@pytest.fixture(scope="module", autouse=True)
def db(tmp_path_factory):
    engine.init_database(f"sqlite:///{(tmp_path_factory.mktemp('db') / 'r.db').as_posix()}")


def _page_count(path) -> int:
    return len(re.findall(rb"/Type /Page\b", path.read_bytes()))


def _rule(**texts):
    return sc.save_rule({"name": f"R{id(texts)}", "ring_values": [{"zone": "Z", "points": 5}],
                         "max_shots_per_target": 1, **texts})


def test_default_rule_is_3d_standard_and_unique():
    rule = sc.get_rule(int(ss.get("default_scoring_rule_id")))
    assert rule.name == "3D Standard 3-Pfeil"


def test_rules_pdf_created_with_special_characters():
    path = build_rules_pdf(_rule(tournament_rules="Regel <1> & mehr\n\nZweiter Absatz").id)
    assert path.read_bytes().startswith(b"%PDF") and _page_count(path) == 1


def test_announcement_conditions_page_only_when_filled():
    def pages(**texts):
        rule = _rule(**texts)
        t = ts.save_tournament({"name": "T", "date": date(2030, 1, 1), "num_targets": 2,
                                "scoring_rule_id": rule.id}, [md.list_bow_classes()[0].id])
        return _page_count(generate_announcement_pdf(t.id))
    assert pages(participation_conditions="Nur mit Helm") == pages() + 1


def test_announcement_notes_block_only_once(tmp_path, monkeypatch):
    from reportlab.platypus import SimpleDocTemplate
    stories = []
    monkeypatch.setattr(SimpleDocTemplate, "build", lambda self, story, *a, **k: stories.append(story))
    t = ts.save_tournament({"name": "N", "date": date(2030, 1, 1), "num_targets": 2,
                            "legal_notes": "Hinweis A\nHinweis B",
                            "scoring_rule_id": _rule().id},[md.list_bow_classes()[0].id])
    generate_announcement_pdf(t.id, tmp_path / "a.pdf")
    headings = [f._content[0].getPlainText() for f in stories[0] if hasattr(f, "_content")]
    assert headings.count("Wichtige Hinweise") == 1


def test_builtin_rule_saves_only_texts():
    rule = sc.get_rule(int(ss.get("default_scoring_rule_id")))
    saved = sc.save_rule_texts(rule.id, "Regeln", "Bedingungen")
    assert (saved.tournament_rules, saved.participation_conditions) == ("Regeln", "Bedingungen")
    assert saved.is_builtin and saved.name == "3D Standard 3-Pfeil"

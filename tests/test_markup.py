# -*- coding: utf-8 -*-
"""Textauszeichnung der mehrzeiligen Felder: Konverter, Editor und die Ausgabekanäle."""
import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bowtally.services import markup


@pytest.mark.parametrize("src, html", [
    ("**fett** und *kursiv* und ~~weg~~", "<b>fett</b> und <i>kursiv</i> und <s>weg</s>"),
    ("2 * 3 = 6 und a * b", "2 * 3 = 6 und a * b"),            # lone stars stay text
    ("***beides*** **offen", "<b><i>beides</i></b> **offen"),
    ("**~~a~~** & <x>", "<b><s>a</s></b> &amp; &lt;x&gt;"),
    ("- eins\n- zwei\n1. a\n2. b\n\nText", "&bull; eins<br>&bull; zwei<br>1. a<br>2. b<br><br>Text"),
])
def test_to_html(src, html):
    assert markup.to_html(src) == html


def test_other_channels():
    src = "**fett** *k* ~~s~~\n- x\n5. y"
    assert markup.to_whatsapp(src) == "*fett* _k_ ~s~\n• x\n1. y"
    assert markup.to_reportlab(src) == "<b>fett</b> <i>k</i> <strike>s</strike><br/>• x<br/>1. y"
    assert markup.to_plain(src) == "fett k s\n• x\n1. y"
    assert markup.unlist("- a") == "a" and markup.unlist("1.5 kg") == "1.5 kg"


@pytest.mark.parametrize("text", [
    "Zeile 1\nZeile 2\n\nAbsatz 2", "1. Platz: 20 €\n2. Platz: 10 €", "a_b * c # d",
    "- eins\n- **zwei**\n1. x\n2. y\nText", "**fett** *kursiv* ~~weg~~ ***bk***", "", "  eingerückt",
])
def test_editor_round_trip_keeps_the_text(text):
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from bowtally.ui.components.markdown_edit import MarkdownEdit
    edit = MarkdownEdit(text)
    assert edit.toPlainText() == text


def test_editor_toolbar_writes_markup():
    from PySide6.QtWidgets import QApplication
    QApplication.instance() or QApplication([])
    from bowtally.ui.components.markdown_edit import MarkdownEdit
    edit = MarkdownEdit()
    edit._toggle("b")
    edit.insertPlainText("fett")
    edit._toggle("b")
    edit.insertPlainText(" normal")
    edit._list("ul")
    assert edit.toPlainText() == "- **fett** normal" and edit._buttons["ul"].isChecked()
    edit._list("ul")
    assert edit.toPlainText() == "**fett** normal"
    edit.setReadOnly(True)
    assert not edit._bar.isVisibleTo(edit)


def test_announcement_and_rules_pdf_render_bold_text(tmp_path):
    from bowtally.database import engine
    from bowtally.reports.announcement import generate_announcement_pdf
    from bowtally.reports.rules_pdf import build_rules_pdf
    from bowtally.services import master_data_service as md, scoring_service as sc
    from bowtally.services import settings_service as ss, tournament_service as ts
    engine.init_database(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    ss.set_value(ss.KEY_TOURNAMENT_RULES_TEXT, "Regel **eins**\n\n- *zwei*")
    ss.set_value(ss.KEY_PARTICIPATION_TERMS_TEXT, "- Nur mit **Helm**")
    rule = sc.save_rule({"name": "R", "ring_values": [{"zone": "Z", "points": 5}],
                         "max_shots_per_target": 1})
    t = ts.save_tournament({"name": "T", "date": date(2030, 1, 1), "num_targets": 2,
                            "scoring_rule_id": rule.id, "additional_info": "Hallo **Welt**\n\nBis *bald*",
                            "legal_notes": "- **Eigene** Gefahr\nKein ~~Zuschauer~~",
                            "notes": "Festes **Schuhwerk**"}, [md.list_bow_classes()[0].id])
    data = generate_announcement_pdf(t.id, tmp_path / "a.pdf").read_bytes()
    assert data.startswith(b"%PDF") and b"OpenSans-Bold" in data and b"OpenSans-Italic" in data
    assert build_rules_pdf(path=tmp_path / "r.pdf").read_bytes().startswith(b"%PDF")

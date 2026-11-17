# -*- coding: utf-8 -*-
import pytest

pytest.importorskip("PySide6")


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_every_search_bar_has_the_same_text_and_width(app):
    from bowtally.ui.components.search_bar import PLACEHOLDER, WIDTH, SearchBar
    bars = [SearchBar("Name, Verein oder Mitgliedsnummer …"), SearchBar("Teilnehmer suchen …"),
            SearchBar()]
    assert {b.placeholderText() for b in bars} == {PLACEHOLDER}
    assert {b.width() for b in bars} == {WIDTH} and "Strg+F" in PLACEHOLDER


def test_hint_goes_into_the_tooltip(app):
    from bowtally.ui.components.search_bar import SearchBar
    assert SearchBar("Name suchen …").toolTip() == "Name suchen: Strg+F, Esc leert die Suche"
    assert SearchBar().toolTip() == "Strg+F, Esc leert die Suche"

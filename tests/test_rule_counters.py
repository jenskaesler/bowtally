# -*- coding: utf-8 -*-
from datetime import date

import pytest

from bowtally.database import engine
from bowtally.services import master_data_service as md
from bowtally.services import ranking_service as rs
from bowtally.services import scoring_service as sc
from bowtally.services import tournament_service as ts

ZONES = [{"zone": "Vital", "points": 20, "type": "kill"}, {"zone": "Körper", "points": 10},
         {"zone": "Miss", "points": 0, "type": "miss"}]


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'r.db').as_posix()}")


def _rule(**extra):
    return sc.save_rule({"name": "Mein Regelwerk", "ring_values": ZONES,
                         "max_shots_per_target": 1, **extra})


def test_empty_specials_list_stays_empty_and_missing_list_is_derived():
    assert _rule(tracked_specials=[]).tracked_specials == []
    derived = sc.save_rule({"name": "Abgeleitet", "ring_values": ZONES, "max_shots_per_target": 1})
    assert {sp["key"] for sp in derived.tracked_specials} == {"kill", "miss"}


def test_discipline_comes_from_the_rule_or_from_its_name():
    by_name = {r.name: sc.rule_discipline(r) for r in sc.list_rules()}
    assert by_name["3D Hunter (IBO)"] == "3d" and by_name["WA Halle 18m"] == "target"
    assert sc.rule_discipline(_rule(name="Eigenes 3D", rules_json={})) == "3d"
    assert sc.rule_discipline(_rule(name="Eigenes 3D 2", rules_json={"discipline": "target"})) == "target"


def test_kill_counts_only_for_3d_and_x_only_for_target_rules():
    both = [{"key": "x", "label": "X", "track": True, "tiebreak": True},
            {"key": "kill", "label": "Kill", "track": True, "tiebreak": True},
            {"key": "miss", "label": "M", "track": True, "tiebreak": False}]
    target = _rule(name="Scheibe", tracked_specials=both, rules_json={"discipline": "target"})
    assert [sp["key"] for sp in sc.counter_specials(target)] == ["x"]
    assert [sp["key"] for sp in sc.active_specials(target)] == ["x", "miss"]
    parcours = _rule(name="Parcours", tracked_specials=both, rules_json={"discipline": "3d"})
    assert [sp["key"] for sp in sc.counter_specials(parcours)] == ["kill"]
    assert [sp["key"] for sp in sc.active_specials(parcours)] == ["kill", "miss"]
    switched_off = _rule(name="Aus", tracked_specials=[{**both[1], "track": False}],
                         rules_json={"discipline": "3d"})
    assert sc.counter_specials(switched_off) == []


@pytest.mark.parametrize("tiebreak, ranks", [("most_top_scores", [1, 2]),
                                             ("total_highest", [1, 1])])
def test_ranking_uses_the_tie_break_of_the_rule(tiebreak, ranks):
    rule = _rule(tracked_specials=[], rules_json={"tiebreak": tiebreak})
    t = ts.save_tournament({"name": "T", "date": date(2026, 5, 1), "num_targets": 2,
                            "shots_per_target": 1, "scoring_rule_id": rule.id},
                           [md.list_bow_classes()[0].id])
    ts.add_participants(t.id, [md.save_archer({"first_name": f"P{i}", "last_name": "X"}).id
                               for i in range(2)])
    first, second = sorted(ts.get_tournament(t.id).participants, key=lambda p: p.start_number or 0)
    for target, (a, b) in enumerate([((20, "Vital"), (10, "Körper")),
                                     ((0, "Miss"), (10, "Körper"))], start=1):
        sc.set_score(first.id, target, 1, a)
        sc.set_score(second.id, target, 1, b)          # both 20 points; the first has a top hit
    rows = next(iter(rs.compute_ranking(t.id).values()))
    assert [r.rank for r in rows] == ranks


@pytest.fixture
def app(monkeypatch):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from bowtally.ui.views import rules_view
    app = QApplication.instance() or QApplication([])
    app.errors = []     # a real error dialog is modal and would hang the test
    monkeypatch.setattr(rules_view, "show_error", lambda _parent, exc, *_: app.errors.append(exc))
    return app


def _dialog(record=None):
    from bowtally.ui.views.rules_view import ScoringRuleDialog
    return ScoringRuleDialog(record)


def test_rule_dialog_has_switches_instead_of_json(app):
    fields = _dialog().form.fields
    assert "rules_json" not in fields
    assert {"discipline", "count_kill", "tie_kill", "count_x", "tie_x", "top_hits"} <= set(fields)


def test_rule_dialog_switches_are_saved_as_specials_and_tie_break(app):
    rule = _rule(tracked_specials=[{"key": "miss", "label": "M", "track": True, "tiebreak": False}],
                 rules_json={"tiebreak": "most_top_scores", "keep": 1, "discipline": "3d"})
    dialog = _dialog(rule)
    assert dialog.form.fields["tie_kill"].widget.isEnabled() is False     # counting is off
    dialog.form.fields["count_kill"].set_value(True)
    dialog.form.fields["tie_kill"].set_value(True)
    dialog.form.fields["top_hits"].set_value(False)
    assert dialog._do_save() and app.errors == []
    saved = sc.get_rule(rule.id)
    assert [(sp["key"], sp["tiebreak"]) for sp in saved.tracked_specials] == \
        [("kill", True), ("miss", False)]
    assert saved.rules_json == {"tiebreak": "total_highest", "keep": 1, "discipline": "3d"}

    dialog = _dialog(saved)
    assert dialog.form.fields["count_kill"].widget.isChecked()
    assert dialog.form.fields["tie_kill"].widget.isEnabled()
    dialog.form.fields["count_kill"].set_value(False)
    assert dialog._do_save()
    assert sc.counter_specials(sc.get_rule(rule.id)) == []


def test_builtin_rule_shows_its_switches_but_stays_read_only(app):
    hunter = next(r for r in sc.list_rules() if r.name == "3D Hunter (IBO)")
    dialog = _dialog(hunter)
    fields = dialog.form.fields
    assert fields["count_kill"].widget.isChecked() and fields["tie_kill"].widget.isChecked()
    assert not fields["count_kill"].widget.isEnabled() and not fields["tie_kill"].widget.isEnabled()


def test_discipline_decides_which_counter_can_be_switched_on(app):
    rule = _rule(name="Mein Parcours 3D")                       # discipline inferred: 3D
    dialog = _dialog(rule)
    f = dialog.form.fields
    assert f["count_kill"].widget.isEnabled() and not f["count_x"].widget.isEnabled()
    f["count_kill"].set_value(True)
    f["discipline"].set_value("target")
    assert not f["count_kill"].widget.isEnabled() and not f["count_kill"].widget.isChecked()
    assert not f["tie_kill"].widget.isEnabled() and f["count_x"].widget.isEnabled()
    f["count_x"].set_value(True)
    assert dialog._do_save() and app.errors == []
    saved = sc.get_rule(rule.id)
    assert saved.rules_json["discipline"] == "target"
    assert [sp["key"] for sp in sc.counter_specials(saved)] == ["x"]

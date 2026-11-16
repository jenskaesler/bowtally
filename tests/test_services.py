# -*- coding: utf-8 -*-
from datetime import date

import pytest

from bowtally.database import engine
from bowtally.services import ValidationError
from bowtally.services import master_data_service as md
from bowtally.services import ranking_service, scoring_service, settings_service, \
    tournament_service as ts


@pytest.fixture(scope="module", autouse=True)
def db(tmp_path_factory):
    url = f"sqlite:///{(tmp_path_factory.mktemp('db') / 't.db').as_posix()}"
    engine.init_database(url)
    engine.init_database(url)   # second start: migrations idempotent, no re-seed


def test_seed():
    assert settings_service.get(settings_service.KEY_COLOR_PRIMARY) == "#00357D"
    assert len(md.list_bow_classes()) == 10
    assert {"IBO 3D Standard", "ASA 3D", "WA 3D"} <= {r.name for r in scoring_service.list_rules()}


def test_archer_notify_results_saved():
    archer = md.save_archer({"first_name": "Nina", "last_name": "N", "notify_results": True})
    assert md.get_archer(archer.id).notify_results is True


def test_tournament_flow():
    ibo = next(r for r in scoring_service.list_rules() if r.name.startswith("IBO"))
    classes = md.list_bow_classes()
    t = ts.save_tournament({"name": "Test", "date": date(2026, 5, 1), "num_targets": 3,
                            "shots_per_target": 1, "scoring_rule_id": ibo.id,
                            "start_groups": "A, B"}, [classes[0].id, classes[1].id])
    a1 = md.save_archer({"first_name": "Anna", "last_name": "A", "club": "X"})
    a2 = md.save_archer({"first_name": "Bert", "last_name": "B"})
    assert ts.add_participants(t.id, [a1.id, a2.id, a1.id]) == 2
    t = ts.get_tournament(t.id)
    p1, p2 = sorted(t.participants, key=lambda p: p.start_number)
    assert (p1.start_group, p2.start_group) == ("A", "B")

    for target, pts in enumerate([20, 0, 10], start=1):
        scoring_service.set_score(p1.id, target, 1, (pts, None))
    for target, pts in enumerate([10, 10, 10], start=1):
        scoring_service.set_score(p2.id, target, 1, (pts, None))
    rows = ranking_service.compute_ranking(t.id, "most_top_scores")[classes[0].id]
    assert [(r.participant_id, r.rank, r.total) for r in rows] == [(p1.id, 1, 30),
                                                                   (p2.id, 2, 30)]

    # phase lifecycle and locking: tests/test_lifecycle.py


def test_builtin_protected():
    bc = md.list_bow_classes()[0]
    with pytest.raises(ValidationError):
        md.delete_bow_class(bc.id)
    clone = md.clone_bow_class(bc.id)
    assert clone.name.endswith("(Kopie)") and not clone.is_builtin
    md.delete_bow_class(clone.id)


def test_result_list_pdf(tmp_path):
    from bowtally.reports.result_list import build_result_list
    t = ts.list_tournaments()[0]
    out = build_result_list(t.id, tmp_path / "r.pdf")
    assert out.read_bytes()[:4] == b"%PDF"


def test_theme_tokens_both_modes():
    from bowtally.ui import theme
    light = theme.tokens({settings_service.KEY_UI_THEME_MODE: "light"})
    dark = theme.tokens({settings_service.KEY_UI_THEME_MODE: "dark"})
    assert light["bg"] == "#F4F6F9" and dark["bg"] == "#0E1116"
    # primary #00357D is too dark on a dark surface -> must be lightened for contrast
    assert theme._luminance(dark["primary"]) - theme._luminance(dark["surface"]) >= 0.3
    assert "QTabBar::tab:selected" in theme.build_stylesheet()


def test_migrations_down_and_up_again(tmp_path):
    """Downgrade to the 0.1.0 schema, then upgrade: data survives, new settings appear."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from bowtally import config

    url = f"sqlite:///{(tmp_path / 'old.db').as_posix()}"
    engine.init_database(url)
    ts.save_tournament({"name": "Alt", "date": date(2030, 1, 1), "num_targets": 3,
                        "scoring_rule_id": next(r for r in scoring_service.list_rules()
                                                 if r.name == "IBO 3D Standard").id},
                       [md.list_bow_classes()[0].id])   # a rule that survives the downgrade
    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    with create_engine(url).begin() as conn:
        cfg.attributes["connection"] = conn
        command.downgrade(cfg, "0001_initial")
    engine.init_database(url)
    assert settings_service.get(settings_service.KEY_UI_THEME_MODE) == "system"
    assert settings_service.get(settings_service.KEY_COLOR_DARK_SURFACE) == "#161B22"
    assert settings_service.get("announcement_group_hint")
    t = ts.list_tournaments()[0]
    assert t.name == "Alt" and t.phase == "announcement"


def test_internal_notes_are_independent_of_course_notes(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'n.db').as_posix()}")
    rule = scoring_service.list_rules()[0].id
    t = ts.save_tournament({"name": "N", "date": date(2030, 1, 1), "num_targets": 3,
                            "scoring_rule_id": rule, "notes": "Parcours: Wald"},
                           [md.list_bow_classes()[0].id])
    ts.update_tournament_fields(t.id, {"internal_notes": "intern"})
    ts.save_tournament({"name": "N", "date": date(2030, 1, 1), "num_targets": 3,
                        "scoring_rule_id": rule, "notes": "Parcours: Wiese"},
                       [md.list_bow_classes()[0].id], t.id)
    t = ts.get_tournament(t.id)
    assert (t.notes, t.internal_notes) == ("Parcours: Wiese", "intern")

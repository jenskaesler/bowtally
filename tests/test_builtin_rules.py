# -*- coding: utf-8 -*-
import pytest

from bowtally.database import engine, seed
from bowtally.services import scoring_service as sc


@pytest.fixture(autouse=True)
def db(tmp_path):
    engine.init_database(f"sqlite:///{(tmp_path / 'b.db').as_posix()}")


def _rule(name):
    return next(r for r in sc.list_rules() if r.name == name)


def _facts(name):
    rule = _rule(name)
    counters = {sp["key"]: sp["tiebreak"] for sp in sc.counter_specials(rule)}
    options = rule.rules_json
    return (sc.rule_discipline(rule), counters, options["tiebreak"],
            bool(options.get("top_hits_first")), bool(options.get("shoot_off")))


@pytest.mark.parametrize("name, expected", [
    # WA / DBSV Halle: meiste 10er, dann 9er, dann gleicher Rang (kein X)
    ("WA Halle 18m", ("target", {}, "most_top_scores", False, False)),
    ("WA Halle 25m", ("target", {}, "most_top_scores", False, False)),
    # WA 3D: meiste 11er, dann 10er, dann gleicher Rang
    ("WA 3D", ("3d", {}, "most_top_scores", False, False)),
    # IBO: meiste 11er; Stechen für die vorderen Plätze; kein "Kill"
    ("3D Hunter (IBO)", ("3d", {}, "most_top_scores", False, True)),
    ("IBO 3D Standard", ("3d", {}, "most_top_scores", False, True)),
    ("IBO 3D mit 12-Ring", ("3d", {}, "most_top_scores", False, True)),
    # DBSV Waldrunde: meiste 15er, dann gleicher Rang; Killzonentreffer nur gezählt
    ("DBSV 3D-Waldrunde", ("3d", {"kill": False}, "most_top_scores", False, False)),
    # IFAA Feld: Stechen für jede Auszeichnung
    ("Feldbogen IFAA (bekannte Entfernung)", ("target", {"x": False}, "total_highest", False, True)),
    ("Feldbogen IFAA (unbekannte Entfernung)", ("target", {"x": False}, "total_highest", False, True)),
])
def test_builtin_rules_follow_the_rule_books(name, expected):
    assert _facts(name) == expected


def test_rules_without_a_verifiable_source_are_gone_and_the_default_is_ibo():
    names = {r.name for r in sc.list_rules()}
    assert names.isdisjoint({"ASA 3D", "NFAA 3D", "3D Standard 3-Pfeil", "DBSV 3D-Jagdrunde",
                             "Blasrohr Standard"})
    assert len(names) == 9


def test_removal_migration_keeps_rules_in_use_as_own_rules(tmp_path):
    import sqlite3
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from bowtally import config
    path = tmp_path / "old.db"
    engine_ = create_engine(f"sqlite:///{path.as_posix()}")
    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    with engine_.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0032_shoot_off_points")
    engine_.dispose()
    con = sqlite3.connect(path)
    for name in ("ASA 3D", "NFAA 3D"):                  # seeded rules of an existing installation
        con.execute("INSERT INTO scoring_rules (name, is_builtin, ring_values, max_shots_per_target, "
                    "allow_retry_shot, rules_json, tracked_specials) VALUES (?, 1, '[]', 1, 0, '{}', '[]')",
                    (name,))
    ids = dict(con.execute("SELECT name, id FROM scoring_rules WHERE is_builtin = 1"))
    con.execute("INSERT INTO tournaments (name, date, num_targets, scoring_rule_id) "
                "VALUES ('T', '2026-01-01', 1, ?)", (ids["NFAA 3D"],))
    con.execute("UPDATE app_settings SET value = ? WHERE key = 'default_scoring_rule_id'",
                (str(ids["ASA 3D"]),))
    con.commit()
    con.close()

    engine.init_database(f"sqlite:///{path.as_posix()}")

    con = sqlite3.connect(path)
    rows = dict(con.execute("SELECT name, is_builtin FROM scoring_rules"))
    assert "ASA 3D" not in rows
    assert rows["NFAA 3D"] == 0                                  # still used by a tournament
    default = con.execute("SELECT value FROM app_settings WHERE key = 'default_scoring_rule_id'").fetchone()[0]
    assert con.execute("SELECT name FROM scoring_rules WHERE id = ?", (default,)).fetchone() == ("3D Hunter (IBO)",)
    con.close()


def test_builtin_rules_are_corrected_on_every_start():
    from bowtally.database.engine import session_scope
    with session_scope() as s:
        rule = s.query(sc.ScoringRule).filter_by(name="WA 3D").one()
        rule.rules_json = {}
        rule.tracked_specials = [{"key": "x", "label": "X", "track": True, "tiebreak": True}]
    with session_scope() as s:
        seed.run(s)
    assert _facts("WA 3D") == ("3d", {}, "most_top_scores", False, False)

# -*- coding: utf-8 -*-
import sqlite3

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from bowtally import config
from bowtally.database import engine as db
from bowtally.database.member_migration import helpers_to_members


def test_helpers_to_members_numbers_members_and_merges_duplicate_assignments():
    helpers = [{"id": 5, "first_name": "B", "last_name": "B", "active": False},
               {"id": 2, "first_name": "A", "last_name": "A", "phone": "1"}]
    assignments = [{"id": 1, "tournament_id": 1, "helper_id": 2, "task": None, "confirmed": False},
                   {"id": 2, "tournament_id": 1, "helper_id": 2, "task": "Kasse", "confirmed": True},
                   {"id": 3, "tournament_id": 2, "helper_id": 2}]
    members, merged = helpers_to_members(helpers, assignments)
    assert [(m["id"], m["member_number"], m["active"]) for m in members] == \
        [(2, "1", True), (5, "2", False)]
    assert all(m["is_tournament_helper"] for m in members)
    assert [(a["id"], a["member_id"], a["task"], a["confirmed"]) for a in merged] == \
        [(1, 2, "Kasse", True), (3, 2, None, False)]


def test_migration_0029_keeps_helpers_and_assignments(tmp_path):
    path = tmp_path / "old.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0028_global_rule_texts")
    engine.dispose()
    con = sqlite3.connect(path)
    con.execute("INSERT INTO tournaments (id, name, date, num_targets) VALUES (1, 'T', '2026-01-01', 1)")
    con.executemany("INSERT INTO helpers (id, first_name, last_name, email, active) VALUES (?, ?, ?, ?, ?)",
                    [(1, "Anna", "Alt", "a@x.de", 1), (2, "Bernd", "Bau", None, 0)])
    con.executemany("INSERT INTO tournament_helpers (tournament_id, helper_id, task, confirmed) "
                    "VALUES (1, ?, ?, ?)", [(1, "Kasse", 0), (1, "Kasse", 1), (2, "Aufbau", 0)])
    con.commit()
    con.close()

    db.init_database(f"sqlite:///{path.as_posix()}")

    con = sqlite3.connect(path)
    assert con.execute("SELECT id, member_number, first_name, email, active, is_tournament_helper, iban "
                       "FROM members ORDER BY id").fetchall() == \
        [(1, "1", "Anna", "a@x.de", 1, 1, None), (2, "2", "Bernd", None, 0, 1, None)]
    assert con.execute("SELECT member_id, task, confirmed, first_name FROM tournament_helpers "
                       "ORDER BY member_id").fetchall() == \
        [(1, "Kasse", 1, None), (2, "Aufbau", 0, None)]
    assert "helpers" not in {r[0] for r in con.execute("SELECT name FROM sqlite_master")}
    assert (tmp_path / "old.db.pre-migration-0028_global_rule_texts").is_file()
    con.close()

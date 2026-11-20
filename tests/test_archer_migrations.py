# -*- coding: utf-8 -*-
"""Migrations 0040-0042 on a database that holds archers referenced by participants and files
(foreign keys on, as in the app): the archer table must not be dropped and rebuilt."""
import sqlite3

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from bowtally import config
from bowtally.database import engine as db


def test_member_number_becomes_pass_number_with_participants_and_files(tmp_path):
    path = tmp_path / "old.db"
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0039_helper_history_manual")
    engine.dispose()
    con = sqlite3.connect(path)
    con.execute("INSERT INTO tournaments (id, name, date, num_targets) VALUES (1, 'T', '2026-01-01', 1)")
    con.executemany("INSERT INTO archers (id, first_name, last_name, member_number, active) "
                    "VALUES (?, ?, ?, ?, 1)", [(1, "Anna", "Alt", "M-7"), (2, "Bert", "Bach", None)])
    con.executemany("INSERT INTO tournament_participants (tournament_id, archer_id, "
                    "registration_status, payment_status) VALUES (1, ?, 'confirmed', 'unpaid')",
                    [(1,), (2,)])
    con.execute("INSERT INTO archer_files (archer_id, filename, stored_path) "
                "VALUES (1, 'pass.pdf', 'archer_files/1/pass.pdf')")
    con.commit()
    con.close()

    db.init_database(f"sqlite:///{path.as_posix()}")     # foreign keys on, like the app

    con = sqlite3.connect(path)
    cols = [r[1] for r in con.execute("PRAGMA table_info(archers)")]
    assert "member_number" not in cols and "pass_number" in cols
    assert con.execute("SELECT id, pass_number FROM archers ORDER BY id").fetchall() == \
        [(1, "M-7"), (2, None)]
    assert con.execute("SELECT COUNT(*) FROM tournament_participants").fetchone() == (2,)
    assert con.execute("SELECT archer_id FROM archer_files").fetchall() == [(1,)]
    assert con.execute("PRAGMA foreign_key_check").fetchall() == []
    assert "uq_participants_tournament_archer" in \
        {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    con.close()

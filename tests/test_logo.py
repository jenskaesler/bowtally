# -*- coding: utf-8 -*-
import sqlite3

import pytest

pytest.importorskip("pyzipper")

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine

from bowtally import config
from bowtally.database import engine
from bowtally.database.engine import session_scope
from bowtally.services import backup_service as bs
from bowtally.services import settings_service as ss

PASSWORD = "Geheim-1234"


@pytest.fixture
def appdata(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    (tmp_path / "appdata").mkdir()
    return tmp_path / "appdata"


def test_store_logo_copies_it_into_the_logo_folder(tmp_path, appdata):
    engine.init_database(f"sqlite:///{(tmp_path / 'l.db').as_posix()}")
    source = tmp_path / "verein.png"
    source.write_bytes(b"png")
    stored = ss.store_logo(source)
    assert stored == appdata / "logo" / "verein.png" and stored.read_bytes() == b"png"
    assert ss.store_logo(stored) == stored          # already in place: nothing to copy


def test_restore_puts_the_logo_into_the_logo_folder_and_points_the_profile_to_it(tmp_path, appdata, monkeypatch):
    engine.init_database(f"sqlite:///{(tmp_path / 'l.db').as_posix()}")
    ss.save_club_profile({"club_name": "Verein", "logo_path": str(ss.store_logo(_png(tmp_path)))})
    with session_scope() as session:
        backup = bs.create_backup(session, "test")
    zip_path = tmp_path / "b.zip"
    bs.save_backup_to_zip(backup, zip_path, bs._logo_from_backup(backup), PASSWORD)

    new_appdata = tmp_path / "appdata2"                  # restore on another machine
    monkeypatch.setattr(config, "APP_DATA_DIR", new_appdata)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "restored.db")
    bs.restore(str(zip_path), PASSWORD)

    with sqlite3.connect(tmp_path / "restored.db") as con:
        (logo_path,) = con.execute("SELECT logo_path FROM club_profile").fetchone()
    assert logo_path == str(new_appdata / "logo" / "verein.png")
    assert (new_appdata / "logo" / "verein.png").read_bytes() == b"png"


def _png(tmp_path):
    source = tmp_path / "verein.png"
    source.write_bytes(b"png")
    return source


def test_migration_moves_an_existing_logo_into_the_logo_folder(tmp_path, appdata):
    path = tmp_path / "old.db"
    old_engine = create_engine(f"sqlite:///{path.as_posix()}")
    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    with old_engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0034_member_files")
    old_engine.dispose()
    old_logo = appdata / "verein.png"                    # the old location: right in the data folder
    old_logo.write_bytes(b"png")
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO club_profile (id, logo_path) VALUES (1, ?)", (str(old_logo),))

    engine.init_database(f"sqlite:///{path.as_posix()}")

    new_logo = appdata / "logo" / "verein.png"
    assert new_logo.read_bytes() == b"png" and not old_logo.exists()
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT logo_path FROM club_profile").fetchone() == (str(new_logo),)

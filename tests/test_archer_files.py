# -*- coding: utf-8 -*-
import sqlite3

import pytest

pytest.importorskip("pyzipper")

from bowtally import config
from bowtally.database import engine
from bowtally.database.engine import session_scope
from bowtally.services import ValidationError
from bowtally.services import backup_service as bs
from bowtally.services import master_data_service as md

PASSWORD = "Geheim-1234"


@pytest.fixture(autouse=True)
def appdata(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'a.db').as_posix()}")
    return tmp_path / "appdata"


def _archer_with_file(tmp_path, content=b"Ausweis"):
    archer = md.save_archer({"first_name": "Anna", "last_name": "Alt"})
    source = tmp_path / "Schützen ausweis (1).pdf"
    source.write_bytes(content)
    return archer, md.add_archer_file(archer.id, source)


def test_files_are_copied_into_appdata_and_can_be_removed(tmp_path, appdata):
    archer, stored = _archer_with_file(tmp_path)
    path = md.archer_file_path(stored)
    assert path.read_bytes() == b"Ausweis" and path.is_relative_to(appdata / "archer_files" / str(archer.id))
    assert stored.filename == "Schützen ausweis (1).pdf" and stored.size_bytes == 7
    md.remove_archer_file(stored.id)
    assert not path.exists() and md.list_archer_files(archer.id) == []


def test_deleting_an_archer_removes_the_files_and_missing_sources_are_refused(tmp_path, appdata):
    archer, _ = _archer_with_file(tmp_path)
    md.delete_archer(archer.id)
    assert not (appdata / "archer_files" / str(archer.id)).exists()
    other = md.save_archer({"first_name": "B", "last_name": "C"})
    with pytest.raises(ValidationError):
        md.add_archer_file(other.id, tmp_path / "gibt-es-nicht.pdf")


def test_backup_contains_the_files_and_restore_brings_them_back(tmp_path, appdata, monkeypatch):
    archer, stored = _archer_with_file(tmp_path, b"Original")
    with session_scope() as session:
        backup = bs.create_backup(session, "test")
    zip_path = tmp_path / "b.zip"
    bs.save_backup_to_zip(backup, zip_path, None, PASSWORD)
    import pyzipper
    with pyzipper.AESZipFile(zip_path) as zf:
        assert stored.stored_path in zf.namelist()

    md.archer_file_path(stored).write_bytes(b"geaendert")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "restored.db")
    bs.restore(str(zip_path), PASSWORD)

    assert md.archer_file_path(stored).read_bytes() == b"Original"
    assert not (appdata / "archer_files.restoring").exists()
    with sqlite3.connect(tmp_path / "restored.db") as con:
        assert con.execute("SELECT filename, stored_path FROM archer_files").fetchall() == \
            [(stored.filename, stored.stored_path)]

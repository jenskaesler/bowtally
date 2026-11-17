# -*- coding: utf-8 -*-
import json
import sqlite3

import pytest

pytest.importorskip("pyzipper")

from bowtally import config
from bowtally.database import engine
from bowtally.database.engine import session_scope
from bowtally.services import ValidationError
from bowtally.services import backup_service as bs
from bowtally.services import member_service as ms

PASSWORD = "Geheim-1234"


@pytest.fixture(autouse=True)
def appdata(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "APP_DATA_DIR", tmp_path / "appdata")
    engine.init_database(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    return tmp_path / "appdata"


def _member_with_file(tmp_path, content=b"Vertrag"):
    member = ms.create_member({"member_number": "1", "first_name": "Anna", "last_name": "Alt"})
    source = tmp_path / "Mitglieds antrag (1).pdf"
    source.write_bytes(content)
    return member, ms.add_member_file(member.id, source)


def test_files_are_copied_into_appdata_and_can_be_removed(tmp_path, appdata):
    member, stored = _member_with_file(tmp_path)
    path = ms.member_file_path(stored)
    assert path.read_bytes() == b"Vertrag" and path.is_relative_to(appdata / "member_files" / str(member.id))
    assert stored.filename == "Mitglieds antrag (1).pdf" and stored.size_bytes == 7
    assert stored.stored_path.startswith(f"member_files/{member.id}/")
    assert "Mitglieds antrag (1).pdf" in ms.data_summary(member.id)
    ms.remove_member_file(stored.id)
    assert not path.exists() and ms.list_member_files(member.id) == []


def test_deleting_a_member_removes_the_files_and_missing_sources_are_refused(tmp_path, appdata):
    member, stored = _member_with_file(tmp_path)
    ms.delete_member(member.id)
    assert not (appdata / "member_files" / str(member.id)).exists()
    other = ms.create_member({"member_number": "2", "first_name": "B", "last_name": "C"})
    with pytest.raises(ValidationError):
        ms.add_member_file(other.id, tmp_path / "gibt-es-nicht.pdf")


def _backup_zip(tmp_path):
    with session_scope() as session:
        backup = bs.create_backup(session, "test")
    zip_path = tmp_path / "b.zip"
    bs.save_backup_to_zip(backup, zip_path, None, PASSWORD)
    return zip_path


def test_backup_contains_the_files_and_restore_brings_them_back(tmp_path, appdata, monkeypatch):
    member, stored = _member_with_file(tmp_path, b"Original")
    zip_path = _backup_zip(tmp_path)
    import pyzipper
    with pyzipper.AESZipFile(zip_path) as zf:
        assert stored.stored_path in zf.namelist()

    stray = appdata / "member_files" / "999" / "stray.txt"        # not part of the backup
    stray.parent.mkdir(parents=True)
    stray.write_text("alt")
    ms.member_file_path(stored).write_bytes(b"geaendert")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "restored.db")

    bs.restore(str(zip_path), PASSWORD)

    assert ms.member_file_path(stored).read_bytes() == b"Original"
    assert not stray.exists() and not (appdata / "member_files.restoring").exists()
    with sqlite3.connect(tmp_path / "restored.db") as con:
        assert con.execute("SELECT filename, stored_path FROM member_files").fetchall() == \
            [(stored.filename, stored.stored_path)]


def test_restore_refuses_files_outside_of_the_member_folder(tmp_path, appdata, monkeypatch):
    import pyzipper
    zip_path = tmp_path / "evil.zip"
    with pyzipper.AESZipFile(zip_path, "w", encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(PASSWORD.encode())
        zf.writestr("backup.json", json.dumps({"meta": {"format_version": "4"}, "data": {}}))
        zf.writestr("bowtally.info", "type: bowtally_backup\n")
        zf.writestr("member_files/../evil.txt", "boese")
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "restored.db")
    with pytest.raises(ValueError, match="ungültig"):
        bs.restore(str(zip_path), PASSWORD)
    assert not (appdata / "evil.txt").exists() and not (tmp_path / "evil.txt").exists()
    assert not (appdata / "member_files.restoring").exists()

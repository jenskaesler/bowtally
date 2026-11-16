# -*- coding: utf-8 -*-
import json
import sqlite3
import zipfile
from pathlib import Path

from bowtally import config
from bowtally.services import backup_service


def test_restore_archer_with_builtin_bow_class(tmp_path, monkeypatch):
    db_path = tmp_path / "bowtally.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    backup = {
        "meta": {"format_version": "1"},
        "data": {
            "bow_classes": [{"id": 4, "name": "Builtin", "is_builtin": 1}],
            "archers": [{"id": 1, "first_name": "Robin", "last_name": "Hood",
                         "default_bow_class_id": 4}],
        },
    }
    backup_file = tmp_path / "backup.json"
    backup_file.write_text(json.dumps(backup), encoding="utf-8")

    backup_service.restore_json(str(backup_file))

    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT default_bow_class_id FROM archers").fetchone() == (4,)


def _make_zip_backup(tmp_path, with_logo):
    logo_src = None
    if with_logo:
        logo_src = tmp_path / "logo.png"
        logo_src.write_bytes(b"PNGDATA")
    backup = {
        "meta": {"format_version": "1", "logo_path": None},
        "data": {"club_profile": [{"id": 1, "name": "Club", "logo_path":
                                   str(logo_src) if logo_src else None}]},
    }
    zip_path = tmp_path / "backup.zip"
    backup_service.save_backup_to_zip(backup, zip_path, str(logo_src) if logo_src else None)
    return zip_path, backup


def test_restore_zip_with_logo(tmp_path, monkeypatch):
    db_path = tmp_path / "bowtally.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    zip_path, _ = _make_zip_backup(tmp_path, with_logo=True)

    backup_service.restore(str(zip_path))

    with sqlite3.connect(db_path) as con:
        row = con.execute("SELECT logo_path FROM club_profile").fetchone()
    assert row and row[0]
    logo_file = config.APP_DATA_DIR / Path(row[0]).name
    assert logo_file.read_bytes() == b"PNGDATA"


def test_save_backup_to_zip_meta_and_info(tmp_path):
    zip_path, backup = _make_zip_backup(tmp_path, with_logo=False)
    assert backup["meta"]["logo_path"] is None
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "backup.json" in names and "bowtally.info" in names
        assert not any(n.startswith("logo/") for n in names)
        info = zf.read("bowtally.info").decode("utf-8")
    assert 'type: bowtally_backup' in info
    assert "app_version:" in info and "schema_version:" in info
    assert "backup_created_at:" in info


def test_restore_rejects_old_json_backup(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    old = tmp_path / "old.json"
    old.write_text(json.dumps({"meta": {"format_version": "1"}, "data": {}}), encoding="utf-8")
    try:
        backup_service.restore(str(old))
    except ValueError as exc:
        assert "nicht mehr unterstützt" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_restore_rejects_invalid_zip(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    bogus = tmp_path / "bogus.zip"
    bogus.write_bytes(b"not a zip")
    try:
        backup_service.restore(str(bogus))
    except ValueError as exc:
        assert "JSON" in str(exc) or "ZIP" in str(exc)
    else:
        raise AssertionError("expected ValueError")

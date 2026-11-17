# -*- coding: utf-8 -*-
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from bowtally import config
from bowtally.services import backup_service

PASSWORD = "Geheim-1234"


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
    pytest.importorskip("pyzipper")
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
    backup_service.save_backup_to_zip(backup, zip_path, str(logo_src) if logo_src else None, PASSWORD)
    return zip_path, backup


def test_restore_zip_with_logo(tmp_path, monkeypatch):
    db_path = tmp_path / "bowtally.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    zip_path, _ = _make_zip_backup(tmp_path, with_logo=True)

    backup_service.restore(str(zip_path), PASSWORD)

    with sqlite3.connect(db_path) as con:
        row = con.execute("SELECT logo_path FROM club_profile").fetchone()
    assert row and row[0]
    logo_file = config.APP_DATA_DIR / Path(row[0]).name
    assert logo_file.read_bytes() == b"PNGDATA"


def test_save_backup_to_zip_meta_and_info(tmp_path):
    zip_path, backup = _make_zip_backup(tmp_path, with_logo=False)
    assert backup["meta"]["logo_path"] is None
    import pyzipper
    with pyzipper.AESZipFile(zip_path) as zf:
        zf.setpassword(PASSWORD.encode())
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


def _format1_backup():
    return {
        "meta": {"format_version": "1"},
        "data": {
            "helpers": [{"id": 7, "first_name": "Maid", "last_name": "Marian",
                         "phone": "123", "email": "m@example.org", "active": 1}],
            "tournaments": [{"id": 1, "name": "Cup", "date": "2026-05-01", "num_targets": 20}],
            "tournament_helpers": [{"id": 1, "tournament_id": 1, "helper_id": 7,
                                    "task": "Kasse", "confirmed": 1}],
        },
    }


def test_restore_format1_helpers_become_members(tmp_path, monkeypatch):
    db_path = tmp_path / "bowtally.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)

    backup_service._restore_impl(_format1_backup())

    with sqlite3.connect(db_path) as con:
        member = con.execute("SELECT id, member_number, first_name, is_tournament_helper "
                             "FROM members").fetchall()
        assignment = con.execute("SELECT member_id, task, confirmed FROM tournament_helpers").fetchall()
    assert member == [(7, "1", "Maid", 1)]
    assert assignment == [(7, "Kasse", 1)]


def test_format2_round_trip_keeps_member_with_iban(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    db_path = tmp_path / "bowtally.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    backup = {"meta": {"format_version": "2"}, "data": {"members": [
        {"id": 3, "member_number": "42", "first_name": "Robin", "last_name": "Hood",
         "iban": "DE89370400440532013000", "bic": "COBADEFFXXX", "sepa_direct_debit": 1}]}}

    backup_service._restore_impl(backup)

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    with Session(engine) as session:
        exported = backup_service.create_backup(session, "test")
    engine.dispose()
    assert exported["meta"]["format_version"] == "3"
    assert "helpers" not in exported["data"]
    (member,) = exported["data"]["members"]
    assert member["iban"] == "DE89370400440532013000" and member["member_number"] == "42"


def test_restore_rejects_unknown_format(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    with pytest.raises(ValueError, match="Unbekanntes Backup-Format"):
        backup_service._restore_impl({"meta": {"format_version": "99"}, "data": {}})


def test_backup_without_password_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_service, "_get_password", lambda key: "")
    monkeypatch.setattr(backup_service.ss, "get", lambda key, default=None: str(tmp_path))
    with pytest.raises(ValueError, match="Kein Backup-Passwort gesetzt"):
        backup_service.save_backup_to_zip({"meta": {}, "data": {}}, tmp_path / "x.zip", None, "")
    for backup in (backup_service.backup_local, backup_service.backup_network,
                   backup_service.backup_nextcloud):
        with pytest.raises(ValueError, match="Kein Backup-Passwort gesetzt"):
            backup()
    assert not list(tmp_path.glob("*.zip"))


def _legacy_zip(tmp_path):
    """Unencrypted ZIP as written by older BowTally versions."""
    zip_path = tmp_path / "legacy.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("backup.json", json.dumps(_format1_backup()))
        zf.writestr("bowtally.info", "type: bowtally_backup\n")
    return zip_path


def test_legacy_unencrypted_zip_restores_without_password(tmp_path, monkeypatch):
    db_path = tmp_path / "bowtally.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)

    backup_service.restore(str(_legacy_zip(tmp_path)))

    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT first_name FROM members").fetchone() == ("Maid",)


def test_encrypted_zip_needs_correct_password(tmp_path, monkeypatch):
    zip_path, _ = _make_zip_backup(tmp_path, with_logo=False)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")

    with pytest.raises(backup_service.BackupPasswordRequired):
        backup_service.restore(str(zip_path))
    with pytest.raises(ValueError, match="Das Passwort ist falsch."):
        backup_service.restore(str(zip_path), "falsch")
    assert not (tmp_path / "bowtally.db").exists()


def test_restore_ignores_obsolete_setting_and_keeps_rule_options(tmp_path, monkeypatch):
    db_path = tmp_path / "bowtally.db"
    monkeypatch.setattr(config, "DB_PATH", db_path)
    rule = {"id": 900, "name": "Mein 3D", "is_builtin": 0, "max_shots_per_target": 1,
            "ring_values": json.dumps([{"zone": "Kill", "points": 10, "type": "kill"}]),
            "tracked_specials": json.dumps([{"key": "kill", "label": "Kill", "track": True,
                                             "tiebreak": True}]),       # JSON columns are text in backups
            "rules_json": json.dumps({"discipline": "3d", "tiebreak": "total_highest"})}
    backup = {"meta": {"format_version": "2"}, "data": {
        "app_settings": [{"key": "result_tiebreak_mode", "value": "total_highest",
                          "category": "behavior", "value_type": "string"}],
        "scoring_rules": [rule]}}

    backup_service._restore_impl(backup)

    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT 1 FROM app_settings WHERE key = 'result_tiebreak_mode'").fetchone() is None
        row = con.execute("SELECT tracked_specials, rules_json FROM scoring_rules "
                          "WHERE name = 'Mein 3D'").fetchone()
    assert json.loads(row[0])[0]["tiebreak"] is True
    assert json.loads(row[1]) == {"discipline": "3d", "tiebreak": "total_highest"}


def test_builtin_rules_count_kill_miss_and_x_per_target(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "bowtally.db")
    from bowtally.database.engine import init_database
    from bowtally.services import scoring_service as sc
    init_database()
    types = {r.name: {z["zone"]: z.get("type", "") for z in r.ring_values} for r in sc.list_rules()}
    assert types["DBSV 3D-Waldrunde"]["Innere Killzone (1. Pfeil)"] == "kill"
    assert types["DBSV 3D-Waldrunde"]["Miss"] == "miss"
    assert types["WA Halle 18m"]["X (10 innen)"] == "x" and types["WA Halle 18m"]["10"] == ""
    assert types["3D Hunter (IBO)"]["Vital innen"] == ""        # not unambiguous: left to the user

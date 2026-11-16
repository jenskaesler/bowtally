# -*- coding: utf-8 -*-
import json
import sqlite3

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

# -*- coding: utf-8 -*-
"""Local, network and cloud backup / restore for the BowTally database."""
import base64
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from bowtally import config
from bowtally.services import settings_service as ss

EXPORT_TABLE_ORDER = [
    "app_settings", "club_profile", "scoring_rules", "bow_classes", "archers",
    "tournament_phases", "tournaments", "entry_fees", "tournament_participants",
    "tournament_rounds", "scores", "helpers", "tournament_helpers",
    "score_sheet_templates", "prizes", "course_targets", "schedule_groups",
    "phase_transition_log", "inventory_items",
]


def _json_name() -> str:
    return f"BowTally-Backup-{datetime.now():%Y-%m-%d-%H%M%S}.json"


def _prune_by_days(dest_dir: Path, days: int):
    cutoff = datetime.now() - timedelta(days=days)
    for pattern in ("BowTally-Backup-*.json", "bowtally_backup_*.zip"):
        for f in dest_dir.glob(pattern):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                    f.unlink(missing_ok=True)
            except OSError:
                pass


def _retention_days() -> int:
    return max(1, int(ss.get("backup_retention_days", "30") or 30))


def _get_password(key: str) -> str:
    try:
        import keyring
        v = keyring.get_password("BowTally", key)
        if v is not None:
            return v
    except Exception:
        pass
    encoded = ss.get(f"{key}_b64") or ""
    try:
        return base64.b64decode(encoded.encode()).decode("utf-8")
    except Exception:
        return ""


def _set_password(key: str, value: str) -> None:
    try:
        import keyring
        keyring.set_password("BowTally", key, value)
        return
    except Exception:
        pass
    ss.set_many({f"{key}_b64": base64.b64encode(value.encode("utf-8")).decode()})


# ------------------------------------------------------------------ export

def create_backup(session, app_version: str) -> dict:
    from sqlalchemy import text as _text
    meta = {
        "bowtally_version": app_version,
        "backup_created_at": datetime.now().isoformat(),
        "format_version": "1",
    }
    try:
        row = session.execute(_text("SELECT version_num FROM alembic_version")).fetchone()
        meta["schema_version"] = row[0] if row else None
    except Exception:
        meta["schema_version"] = None

    data = {}
    for table in EXPORT_TABLE_ORDER:
        try:
            rows = session.execute(_text(f"SELECT * FROM {table}")).mappings().all()
            data[table] = [
                {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}
                for row in rows
            ]
        except Exception:
            data[table] = []
    return {"meta": meta, "data": data}


def save_backup_to_file(backup_dict: dict, path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(backup_dict, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------ backup

def _log_backup(file_name: str, target: str, file_size: int, success: bool,
                error: str = None) -> None:
    try:
        from bowtally.database.engine import session_scope
        from bowtally.database.models import BackupLog
        with session_scope() as s:
            s.add(BackupLog(file_name=file_name, target=target,
                            file_size_bytes=file_size, success=success, error_message=error))
    except Exception:
        pass


def backup_local() -> str:
    from bowtally.database.engine import session_scope
    from bowtally import __version__
    path = (ss.get("backup_local_path") or "").strip()
    if not path:
        raise ValueError("Kein Backup-Pfad konfiguriert.")
    dest = Path(path)
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / _json_name()
    with session_scope() as session:
        backup = create_backup(session, __version__)
    save_backup_to_file(backup, file_path)
    _prune_by_days(dest, _retention_days())
    _log_backup(file_path.name, "local", os.path.getsize(file_path), True)
    return str(file_path)


def backup_network() -> str:
    from bowtally.database.engine import session_scope
    from bowtally import __version__
    path = (ss.get("backup_network_path") or "").strip()
    if not path:
        raise ValueError("Kein Netzwerkpfad konfiguriert.")
    if ss.get_bool("backup_network_requires_auth"):
        user = ss.get("backup_network_user") or ""
        pwd = _get_password("backup_network_password")
        import subprocess
        result = subprocess.run(
            ["net", "use", path, f"/user:{user}", pwd],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ConnectionError(result.stderr.strip() or "net use fehlgeschlagen")
    dest = Path(path)
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / _json_name()
    with session_scope() as session:
        backup = create_backup(session, __version__)
    save_backup_to_file(backup, file_path)
    _prune_by_days(dest, _retention_days())
    _log_backup(file_path.name, "network", os.path.getsize(file_path), True)
    return str(file_path)


def _nc_dav_base(url: str, user: str) -> str:
    """Return WebDAV base URL ending in /; handles both base-URL and full DAV-URL input."""
    if "/remote.php/dav/" in url:
        return url.rstrip("/") + "/"
    return f"{url}/remote.php/dav/files/{user}/"


def _nc_auth(user: str, pwd: str) -> str:
    return "Basic " + base64.b64encode(f"{user}:{pwd}".encode()).decode()


def _nc_request(url: str, method: str, auth: str, data=None):
    import urllib.request
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header("Authorization", auth)
    return req


def _nc_mkcol_recursive(base: str, path: str, auth: str) -> None:
    """MKCOL each segment of path under base; ignores 405/409/404 (already exists)."""
    import urllib.request, urllib.error
    parts = path.strip("/").split("/")
    for i in range(1, len(parts) + 1):
        seg_url = base + "/".join(parts[:i]) + "/"
        try:
            urllib.request.urlopen(_nc_request(seg_url, "MKCOL", auth))
        except urllib.error.HTTPError as e:
            if e.code not in (405, 409):
                raise


def backup_nextcloud() -> str:
    import urllib.request
    from bowtally.database.engine import session_scope
    from bowtally import __version__
    url = (ss.get("backup_nextcloud_url") or "").rstrip("/")
    user = ss.get("backup_nextcloud_user") or ""
    pwd = _get_password("backup_nextcloud_password")
    remote_path = (ss.get("backup_nextcloud_path") or "BowTally/Backups").strip("/")
    if not url or not user:
        raise ValueError("Nextcloud-URL und Benutzername erforderlich.")
    auth = _nc_auth(user, pwd)
    with session_scope() as session:
        backup = create_backup(session, __version__)
    filename = _json_name()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                     encoding="utf-8") as tmp:
        json.dump(backup, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    try:
        dav_base = _nc_dav_base(url, user)
        folder_url = f"{dav_base}{remote_path}/"
        remote = f"{folder_url}{filename}"
        _nc_mkcol_recursive(dav_base, remote_path, auth)
        tmp_size = os.path.getsize(tmp_path)
        with open(tmp_path, "rb") as f:
            urllib.request.urlopen(_nc_request(remote, "PUT", auth, f.read()))
    finally:
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
    _log_backup(filename, "nextcloud", tmp_size, True)
    return remote


# ------------------------------------------------------------------ test

def test_local(path: str) -> None:
    if not path:
        raise ValueError("Kein Verzeichnispfad angegeben.")
    dest = Path(path)
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)
    if not os.access(dest, os.W_OK):
        raise PermissionError(f"Kein Schreibzugriff auf: {path}")


def test_network(path: str, requires_auth: bool, user: str, password: str) -> None:
    if not path:
        raise ValueError("Kein Netzwerkpfad angegeben.")
    if requires_auth and user:
        import subprocess
        result = subprocess.run(
            ["net", "use", path, f"/user:{user}", password],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ConnectionError(result.stderr.strip() or "Verbindung fehlgeschlagen")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Pfad nicht erreichbar: {path}")


def test_nextcloud(url: str, user: str, password: str, remote_path: str) -> None:
    import urllib.request, urllib.error
    url = url.rstrip("/")
    remote_path = (remote_path or "BowTally/Backups").strip("/")
    if not url or not user:
        raise ValueError("URL und Benutzername erforderlich.")
    auth = _nc_auth(user, password)
    dav_base = _nc_dav_base(url, user)
    check_url = f"{dav_base}{remote_path}/"
    req = _nc_request(check_url, "PROPFIND", auth)
    req.add_header("Depth", "0")
    try:
        urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            _nc_mkcol_recursive(dav_base, remote_path, auth)
        else:
            raise ConnectionError(f"HTTP {e.code}: {e.reason}") from e


# ------------------------------------------------------------------ restore

def _import_data(conn, inspector, data: dict) -> None:
    from sqlalchemy import text as _text
    for table in EXPORT_TABLE_ORDER:
        rows = data.get(table, [])
        if not rows:
            continue
        try:
            schema_cols = {c["name"] for c in inspector.get_columns(table)}
        except Exception:
            continue
        for row in rows:
            if row.get("is_builtin"):
                continue
            filtered = {k: v for k, v in row.items() if k in schema_cols}
            if not filtered:
                continue
            cols_str = ", ".join(filtered.keys())
            ph_str = ", ".join(f":{k}" for k in filtered.keys())
            conn.execute(_text(f"INSERT OR REPLACE INTO {table} ({cols_str}) VALUES ({ph_str})"),
                         filtered)


def restore_json(backup_path: str) -> None:
    from bowtally.database.engine import _upgrade_to_head, _enable_sqlite_fk
    from sqlalchemy import create_engine, inspect as sa_inspect, event

    raw = Path(backup_path).read_text(encoding="utf-8")
    backup = json.loads(raw)
    meta = backup.get("meta", {})
    if meta.get("format_version") != "1":
        raise ValueError(f"Unbekanntes Backup-Format (format_version={meta.get('format_version')})")
    data = backup.get("data", {})

    db_path = config.DB_PATH
    if db_path.exists():
        shutil.copy2(db_path, Path(str(db_path) + ".restore_backup"))

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        tmp_url = f"sqlite:///{tmp_path.as_posix()}"
        tmp_engine = create_engine(tmp_url, future=True)
        event.listen(tmp_engine, "connect", _enable_sqlite_fk)
        _upgrade_to_head(tmp_engine)
        inspector = sa_inspect(tmp_engine)
        with tmp_engine.begin() as conn:
            _import_data(conn, inspector, data)
        tmp_engine.dispose()
        shutil.move(str(tmp_path), str(db_path))
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def restore(zip_path: str):
    """Backward compat: restore from old ZIP backup."""
    db_path = config.DB_PATH
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            raise ValueError("Leeres ZIP-Archiv.")
        shutil.copy2(db_path, str(db_path) + ".restore_backup")
        with zf.open(names[0]) as src, open(db_path, "wb") as dst:
            dst.write(src.read())

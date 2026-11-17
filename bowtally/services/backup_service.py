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
    "tournament_rounds", "scores", "members", "tournament_helpers", "member_helper_history",
    "member_files",
    "score_sheet_templates", "prizes", "course_targets", "schedule_groups",
    "phase_transition_log", "inventory_items", "activity_log", "backup_log",
    "tournament_bow_classes",
]


class BackupPasswordRequired(ValueError):
    """The backup ZIP is encrypted and no password was given."""


class BackupPasswordWrong(ValueError):
    """The given password does not open the encrypted backup ZIP."""


def _zip_name() -> str:
    return f"bowtally_backup_{datetime.now():%Y-%m-%d-%H%M%S}.zip"


def _logo_from_backup(backup: dict) -> str | None:
    rows = backup.get("data", {}).get("club_profile") or []
    return (rows[0].get("logo_path") or None) if rows else None


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


def _backup_password() -> str:
    password = _get_password("backup_zip_password")
    if not password:
        raise ValueError("Kein Backup-Passwort gesetzt. "
                         "Bitte unter Einstellungen > Backup ein Passwort festlegen.")
    return password


# ------------------------------------------------------------------ export

def create_backup(session, app_version: str) -> dict:
    from sqlalchemy import text as _text
    meta = {
        "type": "bowtally_backup",
        "bowtally_version": app_version,
        "backup_created_at": datetime.now().isoformat(),
        "format_version": "4",
        "logo_path": None,
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


def save_backup_to_zip(backup_dict: dict, path, logo_path: str | None, password: str) -> None:
    """Write backup as AES-256 encrypted ZIP: backup.json + bowtally.info (+ logo/<name>)."""
    from bowtally import __version__
    if not password:
        raise ValueError("Kein Backup-Passwort gesetzt. "
                         "Bitte unter Einstellungen > Backup ein Passwort festlegen.")
    import pyzipper  # lazy: only needed when writing/reading encrypted backups
    meta = backup_dict.setdefault("meta", {})
    if logo_path and os.path.exists(logo_path):
        logo_file = Path(logo_path)
        meta["logo_path"] = f"logo/{logo_file.name}"
        logo_bytes = logo_file.read_bytes()
    else:
        meta["logo_path"] = None
        logo_bytes = None
    info = (
        f"type: bowtally_backup\n"
        f"app_version: {__version__}\n"
        f"schema_version: {meta.get('schema_version')}\n"
        f"backup_created_at: {meta.get('backup_created_at')}\n"
    )
    with pyzipper.AESZipFile(path, "w", compression=zipfile.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as zf:
        zf.setpassword(password.encode("utf-8"))
        zf.writestr("backup.json", json.dumps(backup_dict, ensure_ascii=False, indent=2))
        zf.writestr("bowtally.info", info)
        if logo_bytes is not None:
            zf.writestr(meta["logo_path"], logo_bytes)
        for row in backup_dict.get("data", {}).get("member_files", []):   # relative path = zip name
            source = config.APP_DATA_DIR / row["stored_path"]
            if source.is_file():
                zf.write(source, row["stored_path"])


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
    password = _backup_password()
    dest = Path(path)
    dest.mkdir(parents=True, exist_ok=True)
    file_path = dest / _zip_name()
    with session_scope() as session:
        backup = create_backup(session, __version__)
    save_backup_to_zip(backup, file_path, _logo_from_backup(backup), password)
    _prune_by_days(dest, _retention_days())
    _log_backup(file_path.name, "local", os.path.getsize(file_path), True)
    return str(file_path)


def backup_network() -> str:
    from bowtally.database.engine import session_scope
    from bowtally import __version__
    path = (ss.get("backup_network_path") or "").strip()
    if not path:
        raise ValueError("Kein Netzwerkpfad konfiguriert.")
    password = _backup_password()
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
    file_path = dest / _zip_name()
    with session_scope() as session:
        backup = create_backup(session, __version__)
    save_backup_to_zip(backup, file_path, _logo_from_backup(backup), password)
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
    password = _backup_password()
    auth = _nc_auth(user, pwd)
    with session_scope() as session:
        backup = create_backup(session, __version__)
    filename = _zip_name()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
    save_backup_to_zip(backup, tmp_path, _logo_from_backup(backup), password)
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

OBSOLETE_SETTINGS = {"result_tiebreak_mode"}     # tie-break is a per-rule option now


def _import_rules(conn, inspector, rows: list[dict], used_ids: set[int]) -> dict[int, int]:
    """Restore scoring rules; returns {id in backup: id in the new database}.

    Built-in rules are matched by name (their ids differ between versions). Rules the app no longer
    ships are kept as own rules only if a tournament (used_ids) still uses them; own rules are
    inserted with a new id, so nothing is overwritten.
    """
    from sqlalchemy import text as _text
    columns = {c["name"] for c in inspector.get_columns("scoring_rules")} - {"id"}
    ids = {}
    for row in rows:
        existing = conn.execute(_text("SELECT id FROM scoring_rules WHERE name = :n"),
                                {"n": row["name"]}).scalar()
        if existing is not None and row.get("is_builtin"):
            ids[row["id"]] = existing
            continue
        if existing is None and row.get("is_builtin") and row["id"] not in used_ids:
            continue
        values = {k: v for k, v in row.items() if k in columns}
        values["is_builtin"] = 0
        if existing is not None:                    # an own rule named like a built-in rule
            values["name"] = f"{row['name']} (Backup)"
        cols = ", ".join(values)
        placeholders = ", ".join(f":{k}" for k in values)
        ids[row["id"]] = conn.execute(
            _text(f"INSERT INTO scoring_rules ({cols}) VALUES ({placeholders})"), values).lastrowid
    return ids


def _import_data(conn, inspector, data: dict) -> None:
    from sqlalchemy import text as _text
    # rules first: settings and tournaments point to them by id
    used = {row.get("scoring_rule_id") for table in ("tournaments", "tournament_rounds")
            for row in data.get(table, [])}
    used |= {int(row["value"]) for row in data.get("app_settings", [])
             if row.get("key") == "default_scoring_rule_id" and str(row.get("value") or "").isdigit()}
    rule_ids = _import_rules(conn, inspector, data["scoring_rules"], used)         if data.get("scoring_rules") else {}
    for table in EXPORT_TABLE_ORDER:
        rows = data.get(table, [])
        if not rows or table == "scoring_rules":
            continue
        try:
            schema_cols = {c["name"] for c in inspector.get_columns(table)}
        except Exception:
            continue
        for row in rows:
            if row.get("is_builtin") or (table == "app_settings"
                                         and row.get("key") in OBSOLETE_SETTINGS):
                continue
            if table in ("tournaments", "tournament_rounds") and row.get("scoring_rule_id") in rule_ids:
                row = {**row, "scoring_rule_id": rule_ids[row["scoring_rule_id"]]}
            if table == "app_settings" and row.get("key") == "default_scoring_rule_id":
                row = {**row, "value": str(rule_ids.get(int(row["value"] or 0), row["value"]))}
            filtered = {k: v for k, v in row.items() if k in schema_cols}
            if not filtered:
                continue
            cols_str = ", ".join(filtered.keys())
            ph_str = ", ".join(f":{k}" for k in filtered.keys())
            conn.execute(_text(f"INSERT OR REPLACE INTO {table} ({cols_str}) VALUES ({ph_str})"),
                         filtered)


def _restore_impl(backup: dict) -> None:
    from bowtally.database.engine import _upgrade_to_head, _enable_sqlite_fk
    from sqlalchemy import create_engine, inspect as sa_inspect, event
    from sqlalchemy.orm import Session
    from bowtally.database import seed

    meta = backup.get("meta", {})
    if meta.get("format_version") not in ("1", "2", "3", "4"):
        raise ValueError(f"Unbekanntes Backup-Format (format_version={meta.get('format_version')})")
    data = backup.get("data", {})
    if "helpers" in data:  # format 1: helpers -> members
        from bowtally.database.member_migration import helpers_to_members
        data["members"], data["tournament_helpers"] = helpers_to_members(
            data.pop("helpers"), data.get("tournament_helpers", []))

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
        with Session(tmp_engine) as session:  # built-in rows are skipped on import, so seed them first (FKs)
            seed.run(session)
            session.commit()
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


def restore_from_json(backup_path: str, password: str | None = None) -> None:
    path = Path(backup_path)
    if zipfile.is_zipfile(path):
        restore(str(path), password)
        return
    _restore_impl(json.loads(path.read_text(encoding="utf-8")))


# Backward compat: alter Name der öffentlichen API
restore_json = restore_from_json


def _open_zip(zip_path: str, password: str | None) -> zipfile.ZipFile:
    """Plain ZipFile for legacy unencrypted backups, AES ZipFile otherwise."""
    with zipfile.ZipFile(zip_path) as probe:
        encrypted = any(info.flag_bits & 0x1 for info in probe.infolist())
    if not encrypted:
        return zipfile.ZipFile(zip_path)
    if not password:
        raise BackupPasswordRequired("Das Backup ist passwortgeschützt.")
    import pyzipper
    zf = pyzipper.AESZipFile(zip_path)
    zf.setpassword(password.encode("utf-8"))
    return zf


MEMBER_FILES_DIR = "member_files"


def _extract_member_files(zf, names: list[str]) -> Path:
    """Unpack the member files into a staging folder next to the final one and return it."""
    staging = config.APP_DATA_DIR / f"{MEMBER_FILES_DIR}.restoring"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    try:
        for name in names:
            if not name.startswith(f"{MEMBER_FILES_DIR}/") or name.endswith("/"):
                continue
            relative = Path(name).relative_to(MEMBER_FILES_DIR)
            target = staging / relative
            if ".." in relative.parts or not target.resolve().is_relative_to(staging.resolve()):
                raise ValueError("Kein gültiges BowTally-Backup (ungültiger Dateipfad).")
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return staging


def restore(zip_path: str, password: str | None = None) -> None:
    """Restore from a ZIP backup: checks bowtally.info, imports backup.json, restores logo."""
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Alte JSON-Backups werden nicht mehr unterstützt. "
                         "Bitte ein ZIP-Backup (.zip) verwenden.")
    with _open_zip(zip_path, password) as zf:
        names = zf.namelist()
        if "backup.json" not in names or "bowtally.info" not in names:
            raise ValueError("Kein gültiges BowTally-Backup (ZIP-Format erwartet).")
        try:
            info_text = zf.read("bowtally.info").decode("utf-8")
            backup_text = zf.read("backup.json").decode("utf-8")
            logo_entry = next((n for n in names if n.startswith("logo/")), None)
            logo_bytes = zf.read(logo_entry) if logo_entry else None
            staging = _extract_member_files(zf, names)
        except (RuntimeError, zipfile.BadZipFile) as exc:  # pyzipper: bad password / HMAC mismatch
            if not password:
                raise
            raise BackupPasswordWrong("Das Passwort ist falsch.") from exc
    info = {}
    for line in info_text.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            info[key.strip()] = value.strip()
    if info.get("type") != "bowtally_backup":
        raise ValueError("Kein gültiges BowTally-Backup (Typ fehlt oder falsch).")
    backup = json.loads(backup_text)
    if logo_entry and logo_bytes:
        config.APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        dest = config.APP_DATA_DIR / Path(logo_entry).name
        dest.write_bytes(logo_bytes)
        backup.setdefault("meta", {})["logo_path"] = str(dest)
    try:
        _restore_impl(backup)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    shutil.rmtree(config.APP_DATA_DIR / MEMBER_FILES_DIR, ignore_errors=True)   # the backup is the full state
    staging.rename(config.APP_DATA_DIR / MEMBER_FILES_DIR)

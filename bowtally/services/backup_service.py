# -*- coding: utf-8 -*-
"""Local, network and cloud backup / restore for the BowTally database."""
import base64
import os
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from bowtally import config
from bowtally.services import settings_service as ss


def _zip_name() -> str:
    return f"bowtally_backup_{datetime.now():%Y%m%d_%H%M%S}.zip"


def _create_zip(dest_dir: Path) -> Path:
    db_path = config.DB_PATH
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / _zip_name()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(db_path, db_path.name)
    return zip_path


def _prune_by_days(dest_dir: Path, days: int):
    cutoff = datetime.now() - timedelta(days=days)
    for f in dest_dir.glob("bowtally_backup_*.zip"):
        try:
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                f.unlink(missing_ok=True)
        except OSError:
            pass


def _retention_days() -> int:
    return max(1, int(ss.get("backup_retention_days", "30") or 30))


def _get_password(key: str) -> str:
    try:
        import keyring  # optional dependency
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


# ------------------------------------------------------------------ backup

def backup_local() -> str:
    path = (ss.get("backup_local_path") or "").strip()
    if not path:
        raise ValueError("Kein Backup-Pfad konfiguriert.")
    dest = Path(path)
    zip_path = _create_zip(dest)
    _prune_by_days(dest, _retention_days())
    return str(zip_path)


def backup_network() -> str:
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
    zip_path = _create_zip(dest)
    _prune_by_days(dest, _retention_days())
    return str(zip_path)


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
            if e.code not in (405, 409):  # already exists
                raise


def backup_nextcloud() -> str:
    import urllib.request
    import tempfile
    url = (ss.get("backup_nextcloud_url") or "").rstrip("/")
    user = ss.get("backup_nextcloud_user") or ""
    pwd = _get_password("backup_nextcloud_password")
    remote_path = (ss.get("backup_nextcloud_path") or "BowTally/Backups").strip("/")
    if not url or not user:
        raise ValueError("Nextcloud-URL und Benutzername erforderlich.")
    auth = _nc_auth(user, pwd)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = _create_zip(Path(tmp))
        dav_base = f"{url}/remote.php/dav/files/{user}/"
        folder_url = f"{dav_base}{remote_path}/"
        remote = f"{folder_url}{zip_path.name}"
        _nc_mkcol_recursive(dav_base, remote_path, auth)
        with open(zip_path, "rb") as f:
            urllib.request.urlopen(_nc_request(remote, "PUT", auth, f.read()))
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
    dav_base = f"{url}/remote.php/dav/files/{user}/"
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

def restore(zip_path: str):
    db_path = config.DB_PATH
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            raise ValueError("Leeres ZIP-Archiv.")
        shutil.copy2(db_path, str(db_path) + ".restore_backup")
        with zf.open(names[0]) as src, open(db_path, "wb") as dst:
            dst.write(src.read())

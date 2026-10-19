# -*- coding: utf-8 -*-
"""Local and cloud backup / restore for the BowTally database."""
import os
import shutil
import zipfile
from datetime import datetime
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


def _prune(dest_dir: Path, keep: int):
    backups = sorted(dest_dir.glob("bowtally_backup_*.zip"))
    for old in backups[:-keep]:
        old.unlink(missing_ok=True)


def backup_local() -> str:
    path = (ss.get("backup_local_path") or "").strip()
    if not path:
        raise ValueError("Kein Backup-Pfad konfiguriert.")
    dest = Path(path)
    retention = int(ss.get("backup_retention", "10") or 10)
    zip_path = _create_zip(dest)
    _prune(dest, retention)
    return str(zip_path)


def backup_nextcloud():
    import urllib.request
    url = (ss.get("backup_nc_url") or "").rstrip("/")
    user = ss.get("backup_nc_user") or ""
    pwd = ss.get("backup_nc_pass") or ""
    if not url or not user:
        raise ValueError("Nextcloud-URL und Benutzername erforderlich.")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = _create_zip(Path(tmp))
        remote = f"{url}/remote.php/dav/files/{user}/BowTally/{zip_path.name}"
        mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        mgr.add_password(None, url, user, pwd)
        handler = urllib.request.HTTPBasicAuthHandler(mgr)
        opener = urllib.request.build_opener(handler)
        # ensure remote folder exists
        folder_url = f"{url}/remote.php/dav/files/{user}/BowTally/"
        try:
            req = urllib.request.Request(folder_url, method="MKCOL")
            opener.open(req)
        except Exception:
            pass
        with open(zip_path, "rb") as f:
            data = f.read()
        req = urllib.request.Request(remote, data=data, method="PUT")
        opener.open(req)


def restore(zip_path: str):
    db_path = config.DB_PATH
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        if not names:
            raise ValueError("Leeres ZIP-Archiv.")
        # back up current db first
        shutil.copy2(db_path, str(db_path) + ".restore_backup")
        with zf.open(names[0]) as src, open(db_path, "wb") as dst:
            dst.write(src.read())

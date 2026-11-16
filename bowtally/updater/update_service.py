# -*- coding: utf-8 -*-
"""Update check and installer download. No UI dependency."""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from packaging.version import InvalidVersion, Version

from bowtally.__version__ import __version__

log = logging.getLogger(__name__)

RELEASE_API = "https://api.github.com/repos/jenskaesler/bowtally/releases/latest"
TIMEOUT = 5
CLEANUP_FLAG = "--cleanup-after"


@dataclass
class UpdateInfo:
    available: bool
    version: str
    body: str
    asset_url: str
    asset_name: str
    checksum_available: bool
    checksum: str | None


class UpdateService:
    def __init__(self, config_dir: Path):
        self.config_dir = Path(config_dir)
        self._cleanup_pending()

    # ---------------------------------------------------------------- state
    def _state_path(self) -> Path:
        return self.config_dir / "updater_state.json"

    def get_skipped_version(self) -> str | None:
        try:
            return json.loads(self._state_path().read_text(encoding="utf-8")).get(
                "skipped_version")
        except (OSError, ValueError):
            return None

    def set_skipped_version(self, version: str) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self._state_path().write_text(
                json.dumps({"skipped_version": version}), encoding="utf-8")
        except OSError as exc:
            log.debug("skipped_version not persisted: %s", exc)

    # ---------------------------------------------------------------- startup args
    def handle_startup_args(self, argv: list[str]) -> None:
        """`--cleanup-after <pfad>`: delete the left-over installer after a silent update."""
        target = _arg_value(argv, CLEANUP_FLAG)
        if target:
            self._delete_later(Path(target))

    # ---------------------------------------------------------------- version check
    def check_for_update(self) -> UpdateInfo | None:
        try:
            res = requests.get(RELEASE_API, timeout=TIMEOUT,
                               headers={"Accept": "application/vnd.github+json"})
        except requests.RequestException as exc:
            log.debug("Update check failed: %s", exc)
            return None
        self._set_last_check()  # nur nach erfolgreicher Verbindung, nicht bei Netzwerkfehler
        if res.status_code != 200:
            log.debug("Update check returned HTTP %s", res.status_code)
            return None
        try:
            data = res.json()
        except ValueError:
            return None
        return _parse_release(data)

    # ---------------------------------------------------------------- internals
    def _cleanup_pending(self) -> None:
        pending = self.config_dir / "cleanup_pending.txt"
        try:
            target = pending.read_text(encoding="utf-8").strip()
        except OSError:
            return
        if not target:
            pending.unlink(missing_ok=True)
            return
        self._delete_later(Path(target))
        try:
            pending.unlink(missing_ok=True)
        except OSError:
            pass

    def _delete_later(self, path: Path, delay: float = 2.0) -> None:
        try:
            time.sleep(delay)
            path.unlink(missing_ok=True)
        except OSError as exc:
            log.debug("Cleanup of %s failed: %s", path, exc)
            try:
                self.config_dir.mkdir(parents=True, exist_ok=True)
                (self.config_dir / "cleanup_pending.txt").write_text(str(path),
                                                                     encoding="utf-8")
            except OSError:
                pass

    def last_check_str(self) -> str:
        import datetime
        path = self.config_dir / "last_update_check.txt"
        try:
            ts = float(path.read_text(encoding="utf-8").strip())
            return datetime.datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
        except (OSError, ValueError):
            return "nie"

    def _set_last_check(self) -> None:
        import time
        (self.config_dir / "last_update_check.txt").write_text(str(int(time.time())),
                                                                encoding="utf-8")


def _arg_value(argv: list[str], flag: str) -> str | None:
    for i, arg in enumerate(argv):
        if arg == flag and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith(flag + "="):
            return arg[len(flag) + 1:]
    return None


def _parse_release(data: dict) -> UpdateInfo | None:
    tag = (data.get("tag_name") or "").lstrip("v")
    try:
        remote = Version(tag)
    except InvalidVersion:
        return None
    try:
        current = Version(__version__)
    except InvalidVersion:
        return None
    if remote <= current:
        return None

    assets = data.get("assets") or []
    asset = next((a for a in assets if (a.get("name") or "").lower().endswith(".exe")), None)
    body = data.get("body") or ""
    if asset is None:
        return UpdateInfo(False, tag, body, "", "", False, None)

    checksum = _find_checksum(assets, asset.get("name") or "")
    return UpdateInfo(True, tag, body, asset.get("browser_download_url") or "",
                      asset.get("name") or "", checksum is not None, checksum)


def _find_checksum(assets: list[dict], installer_name: str) -> str | None:
    sums = next((a for a in assets if (a.get("name") or "").lower() == "checksums.txt"), None)
    if sums is None:
        return None
    try:
        res = requests.get(sums.get("browser_download_url") or "", timeout=TIMEOUT)
        if res.status_code != 200:
            return None
    except requests.RequestException as exc:
        log.debug("checksums.txt download failed: %s", exc)
        return None
    for line in res.text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == installer_name:
            return parts[0].lower()
    return None


def download_asset(url: str, dest: Path, cancel=None, on_progress=None) -> bool:
    """Stream `url` to `dest`. Returns False if cancelled or failed."""
    try:
        with requests.get(url, stream=True, timeout=30) as res:
            if res.status_code != 200:
                return False
            total = int(res.headers.get("Content-Length") or 0)
            done = 0
            with open(dest, "wb") as fh:
                for chunk in res.iter_content(chunk_size=64 * 1024):
                    if cancel is not None and cancel.is_set():
                        return False
                    if not chunk:
                        continue
                    fh.write(chunk)
                    done += len(chunk)
                    if on_progress is not None:
                        on_progress(done, total)
        return True
    except (requests.RequestException, OSError) as exc:
        log.debug("Download failed: %s", exc)
        return False


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
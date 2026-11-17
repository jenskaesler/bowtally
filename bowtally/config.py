# -*- coding: utf-8 -*-
"""Path constants. No other state lives here."""
import os
import sys
import tempfile
from pathlib import Path

APP_NAME = "BowTally"

# Overridable for tests / portable installs
APP_DATA_DIR = Path(os.environ.get("BOWTALLY_DATA_DIR")
                    or Path(os.environ.get("APPDATA", Path.home())) / APP_NAME)
DB_PATH = APP_DATA_DIR / "bowtally.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"
LOG_PATH = APP_DATA_DIR / "app.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
PDF_TEMP_DIR = Path(tempfile.gettempdir()) / APP_NAME


def export_dir() -> Path:
    """Configured export directory (default: ~/Downloads). Includes mkdir."""
    try:
        from bowtally.services import settings_service as ss
        p = ss.get("default_export_path")
        if p:
            d = Path(p)
            d.mkdir(parents=True, exist_ok=True)
            return d
    except Exception:
        pass
    d = Path.home() / "Downloads"
    if not d.exists():
        d = Path.home()
    d.mkdir(parents=True, exist_ok=True)
    return d

# Package dir: inside a PyInstaller bundle data files live under sys._MEIPASS
_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
PACKAGE_DIR = _BASE / "bowtally"
MIGRATIONS_DIR = PACKAGE_DIR / "database" / "migrations"
ALEMBIC_INI = PACKAGE_DIR / "database" / "alembic.ini"
ASSETS_DIR = _BASE / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"


def _read_text(relative_path: str, not_found: str) -> str:
    try:
        return (_BASE / relative_path).read_text(encoding="utf-8")
    except OSError:
        return not_found


# Installed app: the installer writes the current LICENSE / CHANGELOG next to the exe
INSTALL_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else None


def _first_text(candidates: list[Path | None], not_found: str) -> str:
    for path in candidates:
        try:
            if path is not None:
                return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return not_found


def license_text() -> str:
    installed = INSTALL_DIR and [INSTALL_DIR / "LICENSE.txt", INSTALL_DIR / "docs" / "LICENSE.txt"]
    return _first_text([*(installed or []), _BASE / "LICENSE"], "Lizenzdatei nicht gefunden.")


def changelog_text() -> str:
    # Installation: docs/CHANGELOG.md; Entwicklung: liegt im Repo-Root
    return (_read_text("docs/CHANGELOG.md", "")
            or _read_text("CHANGELOG.md", "Changelog-Datei nicht gefunden."))

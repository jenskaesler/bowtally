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

# Package dir: inside a PyInstaller bundle data files live under sys._MEIPASS
_BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
PACKAGE_DIR = _BASE / "bowtally"
MIGRATIONS_DIR = PACKAGE_DIR / "database" / "migrations"
ALEMBIC_INI = PACKAGE_DIR / "database" / "alembic.ini"
ASSETS_DIR = _BASE / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"

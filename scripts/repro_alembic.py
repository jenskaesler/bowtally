# -*- coding: utf-8 -*-
"""Dev helper: reproduce / repair the 'alembic_version empty but tables present' state.

Usage:
    python scripts/repro_alembic.py repro <db-path>
    python scripts/repro_alembic.py status <db-path>
    python scripts/repro_alembic.py stamp <db-path>
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def status(path: Path):
    c = sqlite3.connect(path)
    tables = sorted(r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
    try:
        ver = [r[0] for r in c.execute("SELECT version_num FROM alembic_version")]
    except sqlite3.OperationalError:
        ver = None
    counts = {}
    for t in tables:
        try:
            counts[t] = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except sqlite3.Error as e:
            counts[t] = f"ERR {e}"
    c.close()
    print(f"path      : {path}")
    print(f"tables    : {len(tables)}")
    print(f"alembic   : {'table missing' if ver is None else ver}")
    print(f"counts    : {counts}")


def repro(path: Path):
    """Create tables via metadata, leave alembic_version empty -> broken state."""
    from sqlalchemy import create_engine
    from bowtally.database.models import Base

    if path.exists():
        path.unlink()
    eng = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(eng)          # all tables, no alembic_version
    eng.dispose()
    print("created tables, alembic_version NOT stamped:")
    status(path)
    print("\nnow run init_database on it -> should crash with 'table app_settings already exists'")


def stamp(path: Path):
    """Repair: stamp head so alembic stops trying to run 0001 again."""
    from sqlalchemy import create_engine
    from alembic import command
    from alembic.config import Config
    from bowtally import config as cfg

    eng = create_engine(f"sqlite:///{path.as_posix()}")
    c = Config(str(cfg.ALEMBIC_INI))
    c.set_main_option("script_location", str(cfg.MIGRATIONS_DIR))
    with eng.begin() as conn:
        c.attributes["connection"] = conn
        command.stamp(c, "head")
    eng.dispose()
    print("stamped head:")
    status(path)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    p = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("repro.db")
    {"repro": repro, "status": status, "stamp": stamp}[cmd](p)
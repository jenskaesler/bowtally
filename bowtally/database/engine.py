# -*- coding: utf-8 -*-
"""SQLAlchemy engine, session factory and first-start logic."""
import logging
import shutil
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from bowtally import config

log = logging.getLogger(__name__)

# The only global state of the application.
SessionFactory: sessionmaker | None = None


def _enable_sqlite_fk(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def init_database(db_url: str | None = None) -> sessionmaker:
    """Create dirs, run Alembic to head, seed if empty. Returns the session factory."""
    global SessionFactory
    db_url = db_url or config.DB_URL
    config.APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.PDF_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    engine = create_engine(db_url, future=True)
    event.listen(engine, "connect", _enable_sqlite_fk)
    _prepare_schema(engine)

    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    from bowtally.database import seed
    with SessionFactory() as s:
        seed.run(s)
        s.commit()
    return SessionFactory


def _has_tables(engine) -> bool:
    from sqlalchemy import inspect
    return bool(inspect(engine).get_table_names())


def _stamped_revision(engine) -> str | None:
    from sqlalchemy import inspect, text
    if "alembic_version" not in inspect(engine).get_table_names():
        return None
    with engine.connect() as conn:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()


def schema_version() -> str | None:
    """Alembic revision of the open database (independent of the app version)."""
    if SessionFactory is None:
        return None
    return _stamped_revision(SessionFactory.kw["bind"])


def schema_number() -> str:
    """Short schema version for display, e.g. "0042" (full revision: schema_version())."""
    revision = schema_version()
    return revision.split("_", 1)[0] if revision else "unbekannt"


def _prepare_schema(engine) -> None:
    """Bring an existing but unversioned schema to head instead of crashing on migration 0001."""
    from alembic import command
    from alembic.config import Config

    from bowtally.database.models import Base

    if _has_tables(engine) and not _stamped_revision(engine):
        # Schema exists but alembic_version is empty (crashed or interrupted first run):
        # create any missing tables, adopt the current schema as head, then backfill seed data.
        log.warning("Existing schema without alembic_version - stamping head")
        Base.metadata.create_all(engine)
        cfg = Config(str(config.ALEMBIC_INI))
        cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
        with engine.begin() as conn:
            cfg.attributes["connection"] = conn
            command.stamp(cfg, "head")
        _backfill_missing_seed_data(engine)
        return
    _copy_db_before_migration(engine)
    _upgrade_to_head(engine)


def _copy_db_before_migration(engine) -> None:
    """Keep a copy of the database file (<db>.pre-migration-<revision>) before pending migrations run."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    db_file = engine.url.database
    current = _stamped_revision(engine)
    if not db_file or not Path(db_file).is_file() or current is None:
        return
    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    if current != ScriptDirectory.from_config(cfg).get_current_head():
        shutil.copy2(db_file, f"{db_file}.pre-migration-{current}")


def _backfill_missing_seed_data(engine) -> None:
    """Insert reference data that normally lives in migrations 0003/0006/0016."""
    from sqlalchemy import inspect, text
    from bowtally.database.seed import TOURNAMENT_PHASES

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    with engine.begin() as conn:
        if "tournament_phases" in tables and not conn.execute(
                text("SELECT 1 FROM tournament_phases LIMIT 1")).scalar():
            for key, label, order, desc in TOURNAMENT_PHASES:
                conn.execute(text(
                    "INSERT INTO tournament_phases (key, label, sort_order, description) "
                    "VALUES (:k, :l, :o, :d)"),
                    {"k": key, "l": label, "o": order, "d": desc})
        if "score_sheet_templates" in tables and not conn.execute(
                text("SELECT 1 FROM score_sheet_templates LIMIT 1")).scalar():
            import importlib
            m16 = importlib.import_module('bowtally.database.migrations.versions.0016_score_sheets_prizes')
            for tpl in m16._BUILTIN_TEMPLATES:
                conn.execute(text(
                    "INSERT INTO score_sheet_templates "
                    "(name, tournament_type, is_builtin, column_config, header_fields) "
                    "VALUES (:name, :tournament_type, 1, :column_config, :header_fields)"), tpl)


def _upgrade_to_head(engine) -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(config.ALEMBIC_INI))
    cfg.set_main_option("script_location", str(config.MIGRATIONS_DIR))
    with engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")


@contextmanager
def session_scope():
    """Transactional scope: commit on success, rollback + re-raise on error."""
    if SessionFactory is None:
        raise RuntimeError("Database not initialised")
    session: Session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        log.exception("Database operation failed, rolled back")
        raise
    finally:
        session.close()

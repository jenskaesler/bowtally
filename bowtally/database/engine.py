# -*- coding: utf-8 -*-
"""SQLAlchemy engine, session factory and first-start logic."""
import logging
from contextlib import contextmanager

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
    _upgrade_to_head(engine)

    SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)

    from bowtally.database import seed
    from bowtally.database.models import AppSetting
    with SessionFactory() as s:
        if s.scalar(select(AppSetting).limit(1)) is None:
            log.info("Empty app_settings - seeding database")
            seed.run(s)
            s.commit()
    return SessionFactory


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

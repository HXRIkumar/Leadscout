"""Database engine + session (SPEC §4.1: SQLite via SQLAlchemy 2.x).

Zero-ops, laptop-local. Postgres migration path stays open (swap DATABASE_URL).
`init_db()` is idempotent — safe to call on every command.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _resolve_sqlite_path(url: str) -> str:
    """Make a relative sqlite path absolute against the repo root and ensure its dir exists."""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        raw = url[len(prefix):]
        p = Path(raw)
        if not p.is_absolute():
            p = get_settings().repo_root / p
        p.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{p}"
    return url


def get_engine() -> Engine:
    global _engine, _SessionFactory
    if _engine is None:
        url = _resolve_sqlite_path(get_settings().database_url)
        _engine = create_engine(url, future=True)
        _SessionFactory = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
    return _engine


def _ensure_sqlite_columns(engine: Engine) -> None:
    """Dev-only lightweight migration: ADD COLUMN for mapped columns missing from an
    existing SQLite table. Handles additive schema changes without Alembic. Only
    nullable/defaulted columns can be added this way (all our added columns are).
    Not a substitute for real migrations once on Postgres.
    """
    if not engine.url.get_backend_name().startswith("sqlite"):
        return
    insp = inspect(engine)
    existing = set(insp.get_table_names())
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing:
                continue
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in have:
                    continue
                coltype = col.type.compile(engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {coltype}'))


def init_db() -> None:
    """Create all tables if absent, backfill additive columns. Idempotent (SPEC §15)."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_sqlite_columns(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session context. Commits on success, rolls back on error."""
    global _SessionFactory
    if _SessionFactory is None:
        get_engine()
    assert _SessionFactory is not None
    session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

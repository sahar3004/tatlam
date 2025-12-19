"""Database connection and session management for Tatlam.

This module provides both legacy sqlite3 connections (for backward compatibility)
and modern SQLAlchemy 2.0 engine/session management.

WAL Mode is enabled for better concurrent access performance, which is essential
for async batch processing with asyncio.gather().

Usage:
    # Legacy API (backward compatible)
    conn = get_db()

    # SQLAlchemy API
    with get_session() as session:
        scenarios = session.scalars(select(Scenario)).all()
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from tatlam.settings import get_settings

if TYPE_CHECKING:
    from sqlalchemy.pool import ConnectionPoolEntry

# Schema for the scenarios table (kept for legacy init_db compatibility)
SCENARIOS_SCHEMA = """
CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id TEXT DEFAULT '',
    external_id TEXT DEFAULT '',
    title TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    threat_level TEXT DEFAULT '',
    likelihood TEXT DEFAULT '',
    complexity TEXT DEFAULT '',
    location TEXT DEFAULT '',
    background TEXT DEFAULT '',
    steps TEXT DEFAULT '[]',
    required_response TEXT DEFAULT '[]',
    debrief_points TEXT DEFAULT '[]',
    operational_background TEXT DEFAULT '',
    media_link TEXT,
    mask_usage TEXT,
    authority_notes TEXT DEFAULT '',
    cctv_usage TEXT DEFAULT '',
    comms TEXT DEFAULT '[]',
    decision_points TEXT DEFAULT '[]',
    escalation_conditions TEXT DEFAULT '[]',
    end_state_success TEXT DEFAULT '',
    end_state_failure TEXT DEFAULT '',
    lessons_learned TEXT DEFAULT '[]',
    variations TEXT DEFAULT '[]',
    validation TEXT DEFAULT '[]',
    owner TEXT DEFAULT 'web',
    approved_by TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now'))
);
"""

# Module-level engine and session factory (lazy initialization)
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_db_url() -> str:
    """Construct the SQLAlchemy database URL.

    Handles both string and Path types for DB_PATH configuration.

    Returns:
        str: SQLite URL in format 'sqlite:///path/to/db'
    """
    settings = get_settings()
    db_path = settings.DB_PATH

    # Handle Path objects (convert to absolute path string)
    if isinstance(db_path, Path):
        db_path = str(db_path.absolute())

    return f"sqlite:///{db_path}"


def _set_wal_mode(
    dbapi_connection: sqlite3.Connection,
    connection_record: "ConnectionPoolEntry",
) -> None:
    """Enable WAL mode and optimized synchronous settings on connect.

    WAL (Write-Ahead Logging) mode is essential for concurrent access
    patterns like asyncio.gather() to prevent 'database is locked' errors.

    SYNCHRONOUS=NORMAL provides good durability with better performance
    than FULL mode, suitable for most use cases.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.close()


def get_engine() -> Engine:
    """Get or create the SQLAlchemy engine with WAL mode enabled.

    The engine is created once and cached for the lifetime of the process.
    Uses check_same_thread=False to allow multi-threaded access (required
    for async/executor patterns).

    Returns:
        Engine: Configured SQLAlchemy engine.
    """
    global _engine
    if _engine is None:
        url = get_db_url()
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,  # Verify connections before use
        )
        # Register WAL mode activation on every new connection
        event.listen(_engine, "connect", _set_wal_mode)

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Get or create the session factory.

    Returns:
        sessionmaker[Session]: Configured session factory.
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Provides automatic commit on success and rollback on exception.
    Always closes the session when done.

    Usage:
        with get_session() as session:
            session.add(scenario)
            # Auto-commits on exit, rolls back on exception

    Yields:
        Session: Active database session.
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Reset the engine and session factory.

    Useful for tests that need to switch database paths.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


# ==== Legacy API (backward compatible) ====


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection with Row factory enabled.

    This is the legacy API maintained for backward compatibility.
    New code should prefer get_session() for SQLAlchemy access.

    Centralizing this ensures consistent row handling across app and CLI.
    """
    # Resolve DB_PATH at call time to respect tests that reload config
    settings = get_settings()
    con = sqlite3.connect(settings.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Initialize the database schema.

    This is the legacy API. For SQLAlchemy, use:
        Base.metadata.create_all(get_engine())

    Parameters
    ----------
    conn : sqlite3.Connection | None
        Optional connection to use. If None, creates a new connection.
    """
    if conn is None:
        conn = get_db()
        close_conn = True
    else:
        close_conn = False

    conn.executescript(SCENARIOS_SCHEMA)
    conn.commit()

    if close_conn:
        conn.close()


def init_db_sqlalchemy() -> None:
    """Initialize the database schema using SQLAlchemy.

    Creates all tables defined in the ORM models.
    """
    from tatlam.infra.models import Base
    engine = get_engine()
    Base.metadata.create_all(engine)


__all__ = [
    # Legacy API
    "get_db",
    "init_db",
    "SCENARIOS_SCHEMA",
    # SQLAlchemy API
    "get_engine",
    "get_session",
    "get_session_factory",
    "get_db_url",
    "reset_engine",
    "init_db_sqlalchemy",
]

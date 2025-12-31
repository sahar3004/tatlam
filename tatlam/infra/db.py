"""Database connection and session management for Tatlam.

This module provides modern SQLAlchemy 2.0 engine/session management.

WAL Mode is enabled for better concurrent access performance, which is essential
for async batch processing with asyncio.gather().

Usage:
    # SQLAlchemy API
    with get_session() as session:
        scenarios = session.scalars(select(Scenario)).all()
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from tatlam.settings import get_settings

if TYPE_CHECKING:
    import sqlite3
    from sqlalchemy.pool import ConnectionPoolEntry

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


def init_db_sqlalchemy() -> None:
    """Initialize the database schema using SQLAlchemy.

    Creates all tables defined in the ORM models.
    """
    from tatlam.infra.models import Base

    engine = get_engine()
    Base.metadata.create_all(engine)


__all__ = [
    # SQLAlchemy API
    "get_engine",
    "get_session",
    "get_session_factory",
    "get_db_url",
    "reset_engine",
    "init_db_sqlalchemy",
]

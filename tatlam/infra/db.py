from __future__ import annotations

import sqlite3
from importlib import import_module


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection with Row factory enabled.

    Centralizing this ensures consistent row handling across app and CLI.
    """
    # Resolve DB_PATH at call time to respect tests that reload config
    config = import_module("config")
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


__all__ = ["get_db"]

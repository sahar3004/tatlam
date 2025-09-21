from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path


def test_ready_table_missing(tmp_path: Path, monkeypatch):
    # Create empty DB file without the scenarios table
    db_path = tmp_path / "empty.db"
    sqlite3.connect(db_path).close()
    monkeypatch.setenv("DB_PATH", str(db_path))
    # force reimport so config picks up env
    import sys

    for mod in ("app", "config"):
        if mod in sys.modules:
            del sys.modules[mod]

    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)
    c = app.test_client()
    r = c.get("/healthz/ready")
    assert r.status_code == 503
    data = r.get_json()
    assert any("table_missing" in x for x in data["checks"])  # type: ignore[index]

from __future__ import annotations

import sqlite3
from pathlib import Path
from collections.abc import Iterator

import pytest


CREATE_TABLE_SQL = """
CREATE TABLE scenarios (
    id INTEGER PRIMARY KEY,
    bundle_id TEXT,
    external_id TEXT,
    title TEXT,
    category TEXT,
    threat_level TEXT,
    likelihood TEXT,
    complexity TEXT,
    location TEXT,
    background TEXT,
    steps TEXT,
    required_response TEXT,
    debrief_points TEXT,
    operational_background TEXT,
    media_link TEXT,
    mask_usage TEXT,
    authority_notes TEXT,
    cctv_usage TEXT,
    comms TEXT,
    decision_points TEXT,
    escalation_conditions TEXT,
    end_state_success TEXT,
    end_state_failure TEXT,
    lessons_learned TEXT,
    variations TEXT,
    validation TEXT,
    owner TEXT,
    approved_by TEXT,
    status TEXT,
    created_at TEXT
);
"""


@pytest.fixture()
def sample_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "tatlam.db"
    con = sqlite3.connect(db_path)
    con.executescript(CREATE_TABLE_SQL)
    rows = [
        (
            1,
            "BUNDLE-1",
            "ext-1",
            "אירוע בדיקה A",
            "חפץ חשוד ומטען",
            "גבוהה",
            "בינונית",
            "בינונית",
            "תחנה A",
            "רקע A",
            "[]",
            "[]",
            "[]",
            "אין תיעוד רלוונטי",
            "",
            "לא",
            "",
            "",
            "[]",
            "[]",
            "[]",
            "",
            "",
            "[]",
            "[]",
            "[]",
            "system",
            "gold",
            "approved",
            "2025-09-20T10:00:00",
        ),
        (
            2,
            "BUNDLE-1",
            "ext-2",
            "אירוע בדיקה B",
            "פיגועים פשוטים",
            "בינונית",
            "נמוכה",
            "בינונית",
            "תחנה B",
            "רקע B",
            "[]",
            "[]",
            "[]",
            "אין תיעוד רלוונטי",
            "",
            "כן",
            "",
            "",
            "[]",
            "[]",
            "[]",
            "",
            "",
            "[]",
            "[]",
            "[]",
            "system",
            "operator",
            "approved",
            "2025-09-20T10:05:00",
        ),
        (
            3,
            "BUNDLE-2",
            "ext-3",
            "אירוע בהמתנה",
            "פיגועים פשוטים",
            "נמוכה",
            "נמוכה",
            "נמוכה",
            "תחנה C",
            "רקע C",
            "[]",
            "[]",
            "[]",
            "אין תיעוד רלוונטי",
            "",
            "לא",
            "",
            "",
            "[]",
            "[]",
            "[]",
            "",
            "",
            "[]",
            "[]",
            "[]",
            "system",
            "operator",
            "pending",
            "2025-09-20T10:10:00",
        ),
    ]
    con.executemany(
        """
        INSERT INTO scenarios (
            id, bundle_id, external_id, title, category, threat_level, likelihood,
            complexity, location, background, steps, required_response, debrief_points,
            operational_background, media_link, mask_usage, authority_notes, cctv_usage,
            comms, decision_points, escalation_conditions, end_state_success, end_state_failure,
            lessons_learned, variations, validation, owner, approved_by, status, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    con.commit()
    con.close()
    return db_path


@pytest.fixture(autouse=True)
def use_sample_db_env(monkeypatch: pytest.MonkeyPatch, sample_db: Path) -> Iterator[None]:
    monkeypatch.setenv("DB_PATH", str(sample_db))
    # Disable gating so tests see rows regardless of 'status'
    monkeypatch.setenv("REQUIRE_APPROVED_ONLY", "0")
    # Ensure fresh import of config/app per test so DB_PATH is respected
    import sys as _sys

    for mod in ("app", "config"):
        if mod in _sys.modules:
            del _sys.modules[mod]
    yield

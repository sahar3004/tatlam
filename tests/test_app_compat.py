from __future__ import annotations

# ruff: noqa: E501

import importlib
import sqlite3
import sys
from pathlib import Path

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
    con.execute(
        """
        INSERT INTO scenarios (id, title, category, threat_level, likelihood, complexity, background, steps, required_response, debrief_points, operational_background, media_link, mask_usage, authority_notes, cctv_usage, comms, decision_points, escalation_conditions, end_state_success, end_state_failure, lessons_learned, variations, validation, owner, approved_by, status, created_at)
        VALUES (1, 'אירוע בדיקה', 'חפץ חשוד ומטען', 'גבוהה', 'בינונית', 'בינונית', 'רקע קצר', '[]', '[]', '[]', 'אין תיעוד רלוונטי', '', 'לא', '', '', '[]', '[]', '[]', '', '', '[]', '[]', '[]', 'system', 'operator', 'pending', '2025-09-20T10:00:00')
        """
    )
    con.commit()
    con.close()
    return db_path


@pytest.fixture()
def flask_app(sample_db: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DB_PATH", str(sample_db))
    monkeypatch.setenv("REQUIRE_APPROVED_ONLY", "0")
    monkeypatch.setenv("FLASK_SECRET_KEY", "tests-secret")
    for mod in ["app", "config"]:
        if mod in sys.modules:
            del sys.modules[mod]
    config = importlib.import_module("config")
    importlib.reload(config)
    app_module = importlib.import_module("app")
    importlib.reload(app_module)
    app_module.app.config.update(TESTING=True)
    yield app_module.app


def test_home_page_lists_category(flask_app):
    client = flask_app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert "חפץ חשוד ומטען" in resp.get_data(as_text=True)


def test_category_page_matches_legacy_behavior(flask_app):
    client = flask_app.test_client()
    resp = client.get("/cat/chefetz-chashud")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "אירוע בדיקה" in body


def test_scenario_detail_available(flask_app):
    client = flask_app.test_client()
    resp = client.get("/scenario/1")
    assert resp.status_code == 200
    assert "אירוע בדיקה" in resp.get_data(as_text=True)


def test_api_scenario_returns_json(flask_app):
    client = flask_app.test_client()
    resp = client.get("/api/scenario/1")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["title"] == "אירוע בדיקה"
    assert payload["category"] == "חפץ חשוד ומטען"

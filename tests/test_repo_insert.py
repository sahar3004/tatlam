from __future__ import annotations

import importlib
import sys

import pytest


def test_insert_requires_fields(sample_db):
    from tatlam.infra import repo

    with pytest.raises(ValueError):
        repo.insert_scenario({})
    with pytest.raises(ValueError):
        repo.insert_scenario({"title": "X"})
    # Unknown category should fail
    with pytest.raises(ValueError):
        repo.insert_scenario({"title": "X", "category": "Unknown"})


def test_insert_and_fetch_api(sample_db):
    from tatlam.infra import repo

    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)
    c = app.test_client()

    new_id = repo.insert_scenario(
        {"title": "טופס בדיקה", "category": "פיגועים פשוטים", "steps": ["a", "b"]},
        owner="test",
        pending=True,
    )
    assert new_id > 0
    r = c.get(f"/api/scenario/{new_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data["title"] == "טופס בדיקה"

    # API POST creation
    r2 = c.post(
        "/api/v1/scenarios",
        json={"title": "דרך API", "category": "פיגועים פשוטים"},
    )
    assert r2.status_code == 201
    nid = r2.get_json()["id"]
    r3 = c.get(f"/api/scenario/{nid}")
    assert r3.status_code == 200


def test_pending_hidden_when_gate_on(sample_db, monkeypatch):
    # Turn on gating and ensure newly inserted pending row is hidden from lists
    monkeypatch.setenv("REQUIRE_APPROVED_ONLY", "1")
    # Re-import affected modules to pick up env change
    for mod in ("app", "config", "tatlam.infra.repo"):
        if mod in sys.modules:
            del sys.modules[mod]

    from tatlam.infra import repo as repo2

    new_id = repo2.insert_scenario(
        {"title": "Pending X", "category": "פיגועים פשוטים"},
        owner="test",
        pending=True,
    )
    assert new_id > 0

    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)
    c = app.test_client()
    r = c.get("/api/scenarios?page=1&page_size=100")
    data = r.get_json()
    titles = {it["title"] for it in data["items"]}
    assert "Pending X" not in titles

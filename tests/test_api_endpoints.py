from __future__ import annotations

import importlib


def test_api_list_and_filters(sample_db):
    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)
    client = app.test_client()

    # Basic list
    r = client.get("/api/scenarios?page=1&page_size=10")
    assert r.status_code == 200
    data = r.get_json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2

    # Query filter by title substring
    r2 = client.get("/api/scenarios?q=בדיקה%20A")
    assert r2.status_code == 200
    data2 = r2.get_json()
    assert any("בדיקה A" in it["title"] for it in data2["items"])  # type: ignore[index]


def test_api_cat_and_scenario(sample_db):
    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)
    client = app.test_client()

    r = client.get("/api/cat/chefetz-chashud.json?page=1&page_size=5")
    assert r.status_code == 200
    payload = r.get_json()
    assert payload["total"] >= 1
    assert all(it["category"] for it in payload["items"])  # type: ignore[index]

    # Page 2 (pagination path)
    r_p2 = client.get("/api/cat/chefetz-chashud.json?page=2&page_size=1")
    assert r_p2.status_code == 200

    r2 = client.get("/api/scenario/1")
    assert r2.status_code == 200
    one = r2.get_json()
    assert one["id"] == 1

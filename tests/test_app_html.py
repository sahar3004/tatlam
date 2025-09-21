from __future__ import annotations

import importlib


def _client():
    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)
    return app.test_client()


def test_home_and_list_pages(sample_db):
    c = _client()
    r = c.get("/")
    assert r.status_code == 200
    assert "קטגוריות" in r.get_data(as_text=True)

    r2 = c.get("/all")
    assert r2.status_code == 200


def test_category_and_detail_pages(sample_db):
    c = _client()
    r = c.get("/cat/chefetz-chashud")
    assert r.status_code == 200
    # Invalid slug -> 404 (API route avoids template dependency)
    assert c.get("/api/cat/nope.json").status_code == 404

    # Detail for existing row id=1
    r2 = c.get("/scenario/1")
    assert r2.status_code == 200


def test_dbg_and_health(sample_db, monkeypatch):
    c = _client()
    r = c.get("/dbg/cats_snapshot")
    assert r.status_code == 200
    payload = r.get_json()
    assert "db_categories" in payload

    assert c.get("/health").status_code == 200
    assert c.get("/healthz/ready").status_code in (200, 503)


def test_require_approved_only_gate(sample_db, monkeypatch):
    # Turn on gating and ensure pending rows are excluded from totals
    monkeypatch.setenv("REQUIRE_APPROVED_ONLY", "1")
    # Re-import app/config to pick up env change
    import sys

    for mod in ("app", "config"):
        if mod in sys.modules:
            del sys.modules[mod]

    c = _client()
    r = c.get("/api/scenarios?page=1&page_size=50")
    data = r.get_json()
    titles = {it["title"] for it in data["items"]}
    assert "אירוע בהמתנה" not in titles

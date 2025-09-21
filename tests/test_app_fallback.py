from __future__ import annotations

import importlib

from jinja2 import TemplateNotFound


def test_fallback_html_when_templates_missing(sample_db, monkeypatch):
    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)

    # Force render_template to raise to trigger fallback HTML rendering
    def _raise_template(*_a, **_k):
        raise TemplateNotFound("x")

    monkeypatch.setattr(app_mod, "render_template", _raise_template)

    c = app.test_client()
    assert c.get("/").status_code == 200
    assert c.get("/cat/chefetz-chashud").status_code == 200
    assert c.get("/scenario/1").status_code == 200


def test_dbg_echo_returns_request_info(sample_db):
    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)
    c = app.test_client()
    r = c.get("/dbg/echo", headers={"X-Unit": "1"})
    assert r.status_code == 200
    payload = r.get_json()
    assert payload["headers"]["X-Unit"] == "1"

from __future__ import annotations

import importlib


def test_render_with_fallback_default_dump():
    app_mod = importlib.import_module("app")
    app = app_mod.app
    with app.app_context():
        html = app_mod.render_with_fallback("unknown.html", ctx={"a": 1})
    assert "pre" in html and "a" in html

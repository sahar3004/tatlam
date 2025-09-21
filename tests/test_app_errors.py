from __future__ import annotations

import importlib


def test_not_found_and_internal_handlers(sample_db):
    app_mod = importlib.import_module("app")
    app = app_mod.app
    app.config.update(TESTING=True)

    # 404 via API path to avoid template dependency
    c = app.test_client()
    r = c.get("/api/no-such")
    assert r.status_code == 404

    # Directly call error handlers with API path
    with app.test_request_context("/api/whatever"):
        resp, code = app_mod.not_found(Exception())
        assert code == 404
        resp2, code2 = app_mod.internal(Exception())
        assert code2 == 500

from __future__ import annotations

import importlib


def test_helpers_fetchers(sample_db):
    app_mod = importlib.import_module("app")
    cnt = app_mod.fetch_count_by_slug("chefetz-chashud")
    assert isinstance(cnt, int) and cnt >= 1
    rows = app_mod.fetch_all_basic_categories()
    assert any(r["category"] for r in rows)

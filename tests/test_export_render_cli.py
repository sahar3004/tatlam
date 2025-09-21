from __future__ import annotations

from pathlib import Path

from export_json import fetch_rows
from render_cards import fetch, load_template, safe_filename, unique_path


def test_export_json_filters(sample_db, tmp_path: Path):
    rows_all = fetch_rows()
    assert len(rows_all) >= 2
    rows_cat = fetch_rows(category="חפץ חשוד ומטען")
    assert all(r["category"] == "חפץ חשוד ומטען" for r in rows_cat)


def test_render_cards_to_directory(sample_db, tmp_path: Path):
    # Sanity on helpers
    assert safe_filename("כותרת/בדיקה") != ""
    # unique_path adds suffix if exists
    p1 = unique_path(tmp_path, "file.md")
    p1.write_text("x", encoding="utf-8")
    p2 = unique_path(tmp_path, "file.md")
    assert p2.name != "file.md"

    rows = fetch(category="חפץ חשוד ומטען", bundle_id=None)
    assert rows, "expected at least one row to render"
    # Render via template engine directly
    tpl = load_template(None)
    content = tpl.render(r=rows[0])
    assert "כותרת" in content or rows[0]["title"] in content


def test_fetch_bundle_filter(sample_db):
    rows = fetch(category=None, bundle_id="BUNDLE-1")
    assert all(r["bundle_id"] == "BUNDLE-1" for r in rows)

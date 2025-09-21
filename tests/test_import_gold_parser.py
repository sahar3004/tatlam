from __future__ import annotations

from import_gold_md import parse_md_to_scenario


def test_parse_md_to_scenario_basic():
    md = (
        "# כותרת ראשית\n"
        "📂 קטגוריה: חפץ חשוד ומטען\n\n"
        "## סיפור מקרה\n- תיאור קצר\n\n"
        "## שלבי תגובה\n- צעד א\n- צעד ב\n\n"
        "## תחקיר\n- נקודה\n"
    )
    sc = parse_md_to_scenario(md)
    assert sc["title"]
    assert sc["category"]
    assert isinstance(sc.get("steps"), list)

from __future__ import annotations

from export_json import normalize


def test_export_normalize_lists_parsed():
    row = {
        "steps": '["a", "b"]',
        "required_response": None,
        "debrief_points": "[]",
        "comms": "\n",
        "decision_points": '{"x":1}',
        "escalation_conditions": "not-json",
        "lessons_learned": ["L1"],
        "variations": 5,
        "validation": "[1,2]",
    }
    out = normalize(row)
    assert out["steps"] == ["a", "b"]
    assert out["required_response"] == []
    # For a single JSON object, current normalize keeps it as object
    assert out["decision_points"] == {"x": 1}

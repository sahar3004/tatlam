from __future__ import annotations

import json
from typing import Any


def coerce_bundle_shape(bundle: dict[str, Any]) -> dict[str, Any]:
    """Normalize scenario fields to expected schema and types.

    - Ensures all known keys exist
    - Coerces list-like fields to lists (parsing JSON strings when possible)
    """
    expected_list_fields = [
        "steps",
        "required_response",
        "debrief_points",
        "comms",
        "decision_points",
        "escalation_conditions",
        "lessons_learned",
        "variations",
        "validation",
    ]
    defaults = {
        "external_id": "",
        "title": "",
        "category": "",
        "threat_level": "",
        "likelihood": "",
        "complexity": "",
        "location": "",
        "background": "",
        "operational_background": "",
        "media_link": "",
        "mask_usage": "",
        "authority_notes": "",
        "cctv_usage": "",
        "end_state_success": "",
        "end_state_failure": "",
    }
    scs = bundle.get("scenarios", [])
    fixed: list[dict[str, Any]] = []
    for sc in scs:
        sc = dict(sc or {})
        # Fill defaults
        for k, v in defaults.items():
            sc.setdefault(k, v)
        # Coerce list-like
        for k in expected_list_fields:
            val = sc.get(k, [])
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        val = parsed
                    else:
                        val = [parsed]
                except Exception:
                    val = [val] if val else []
            elif not isinstance(val, list):
                val = [val] if val else []
            sc[k] = val
        fixed.append(sc)
    bundle["scenarios"] = fixed
    return bundle


__all__ = ["coerce_bundle_shape"]

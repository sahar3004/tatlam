from __future__ import annotations

import json
from typing import Any

import jsonschema
from jsonschema import ValidationError


def build_validator_prompt(bundle: dict[str, Any]) -> str:
    return (
        "אתה ולידטור JSON קפדני. בדוק ותקן את המבנה במידת הצורך. "
        "החזר אך ורק JSON תקין – ללא הסברים/גדרות קוד. "
        "שמור על העברית בדיוק כפי שהיא.\n\n" + json.dumps(bundle, ensure_ascii=False)
    )


def validate_json_schema(data: dict[str, Any], schema: dict[str, Any]) -> bool:
    """
    Validate data against a JSON schema.

    Args:
        data: Dictionary to validate
        schema: JSON Schema to validate against

    Returns:
        True if validation passes

    Raises:
        jsonschema.ValidationError: If validation fails
    """
    jsonschema.validate(instance=data, schema=schema)
    return True


__all__ = ["build_validator_prompt", "validate_json_schema"]

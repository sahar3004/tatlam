"""Scenario bundle validation and normalization.

Phase 2 Update: Added strict Pydantic validation to enforce schema compliance.
LLM outputs must match the expected structure or fail fast.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

logger = logging.getLogger(__name__)


class ScenarioModel(BaseModel):
    """Strict validation model for a single scenario.

    All fields that should be lists are validated as lists.
    Strings will be coerced to single-item lists where appropriate.
    """

    # Required fields
    title: str = Field(..., min_length=1, description="Scenario title")
    category: str = Field(..., min_length=1, description="Scenario category")

    # Optional metadata
    external_id: str = ""
    threat_level: str = ""
    likelihood: str = ""
    complexity: str = ""
    location: str = ""
    background: str = ""
    operational_background: str = ""
    media_link: str = ""
    mask_usage: str = ""
    authority_notes: str = ""
    cctv_usage: str = ""
    end_state_success: str = ""
    end_state_failure: str = ""

    # List fields (validated as lists)
    steps: list[Any] = Field(default_factory=list)
    required_response: list[Any] = Field(default_factory=list)
    debrief_points: list[Any] = Field(default_factory=list)
    comms: list[Any] = Field(default_factory=list)
    decision_points: list[Any] = Field(default_factory=list)
    escalation_conditions: list[Any] = Field(default_factory=list)
    lessons_learned: list[Any] = Field(default_factory=list)
    variations: list[Any] = Field(default_factory=list)
    validation: list[Any] = Field(default_factory=list)

    class Config:
        # Allow extra fields from LLM (flexible)
        extra = "allow"
        # Strict mode: raise errors on type mismatches
        strict = False  # Allow coercion

    @field_validator(
        "steps",
        "required_response",
        "debrief_points",
        "comms",
        "decision_points",
        "escalation_conditions",
        "lessons_learned",
        "variations",
        "validation",
        mode="before",
    )
    @classmethod
    def coerce_list_field(cls, v: Any) -> list[Any]:
        """Coerce JSON strings and single values to lists."""
        if isinstance(v, str):
            if not v.strip():
                return []
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [parsed]
            except (json.JSONDecodeError, ValueError):
                return [v]
        elif isinstance(v, list):
            return v
        elif v is None:
            return []
        else:
            return [v]


class ScenarioBundleModel(BaseModel):
    """Strict validation model for a scenario bundle."""

    bundle_id: str = Field(..., min_length=1, description="Unique bundle identifier")
    scenarios: list[ScenarioModel] = Field(..., min_items=0)

    class Config:
        extra = "forbid"  # Strict: no extra fields allowed in bundle


def validate_bundle_strict(bundle: dict[str, Any]) -> dict[str, Any]:
    """Validate bundle with strict Pydantic schema.

    Raises:
        ValidationError: If bundle doesn't match schema

    Returns:
        Validated bundle as dict
    """
    try:
        validated = ScenarioBundleModel(**bundle)
        return validated.model_dump()
    except ValidationError as e:
        logger.error("Bundle validation failed: %s", e)
        raise


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


__all__ = [
    "coerce_bundle_shape",
    "validate_bundle_strict",
    "ScenarioModel",
    "ScenarioBundleModel",
]

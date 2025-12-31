from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

# jsonschema is optional - only needed for validate_json_schema()
if TYPE_CHECKING:
    import jsonschema

logger = logging.getLogger(__name__)


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
        ImportError: If jsonschema is not installed
    """
    import jsonschema  # Import at runtime
    jsonschema.validate(instance=data, schema=schema)
    return True


# ==== Doctrine Validation ====


@dataclass
class DoctrineValidationResult:
    """
    תוצאת וולידציה של תרחיש מול הדוקטרינה.
    
    Attributes:
        is_valid: True אם התרחיש עובר את כל הבדיקות הקריטיות
        errors: רשימת שגיאות קריטיות (מכשילות)
        warnings: רשימת אזהרות (לא מכשילות)
        doctrine_score: ציון 0-100 לפי הדוקטרינה
    """
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    doctrine_score: int = 100


# Valid threat levels from doctrine
VALID_THREAT_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL", "נמוכה", "בינונית", "גבוהה", "קריטית"}

# Required fields for a complete scenario
REQUIRED_SCENARIO_FIELDS = [
    "title",
    "category", 
    "steps",
]

# Safety violation patterns (doctrine: touching suspicious object = score 0)
SAFETY_VIOLATION_PATTERNS = [
    ("נגע", "חפץ"),
    ("לגעת", "חפץ"),
    ("הרים", "חפץ"),
    ("זז", "חפץ"),
    ("הזזת", "חפץ"),
]


def validate_scenario_doctrine(scenario: dict[str, Any]) -> DoctrineValidationResult:
    """
    מאמת שתרחיש עומד בדרישות הדוקטרינה.
    
    בודק:
    1. שדות חובה (title, category, steps)
    2. קטגוריה תקינה
    3. רמת איום תקינה
    4. הפרות בטיחות (נגיעה בחפץ חשוד וכו')
    5. מספר שלבים מספיק
    
    Args:
        scenario: מילון עם נתוני התרחיש
        
    Returns:
        DoctrineValidationResult עם is_valid, errors, warnings, doctrine_score
    """
    from tatlam.core.categories import category_to_slug
    
    errors: list[str] = []
    warnings: list[str] = []
    score = 100
    
    # 1. Check required fields
    for field_name in REQUIRED_SCENARIO_FIELDS:
        if not scenario.get(field_name):
            errors.append(f"שדה חובה חסר: {field_name}")
            score -= 15
    
    # 2. Validate category
    cat = scenario.get("category", "")
    if cat:
        slug = category_to_slug(cat)
        if slug is None:
            warnings.append(f"קטגוריה לא מוכרת: {cat} (ממופה ל-uncategorized)")
            score -= 5
    else:
        errors.append("קטגוריה חסרה")
        score -= 10
    
    # 3. Validate threat level
    threat = str(scenario.get("threat_level", "")).upper().strip()
    if threat:
        # Normalize Hebrew to English
        threat_normalized = threat.replace("נמוכה", "LOW").replace("בינונית", "MEDIUM").replace("גבוהה", "HIGH").replace("קריטית", "CRITICAL")
        if threat_normalized not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            warnings.append(f"רמת איום לא תקינה: {threat}")
            score -= 5
    else:
        warnings.append("רמת איום לא צוינה")
        score -= 3
    
    # 4. Check for safety violations
    scenario_text = str(scenario).lower()
    for pattern_words in SAFETY_VIOLATION_PATTERNS:
        if all(word in scenario_text for word in pattern_words):
            errors.append("🚨 הפרת דוקטרינה קריטית: נגיעה בחפץ חשוד!")
            score = 0
            break
    
    # 5. Check steps count
    steps = scenario.get("steps", [])
    if isinstance(steps, list):
        if len(steps) < 3:
            warnings.append(f"מעט שלבים: {len(steps)} (מומלץ 4-8)")
            score -= 10
        elif len(steps) < 4:
            warnings.append(f"מספר שלבים נמוך: {len(steps)} (מומלץ 4-8)")
            score -= 5
    
    # 6. Check for decision points (recommended)
    decision_points = scenario.get("decision_points", [])
    if not decision_points:
        warnings.append("חסרות נקודות הכרעה")
        score -= 5
    
    # 7. Check for end states
    if not scenario.get("end_state_success") and not scenario.get("end_state_failure"):
        warnings.append("חסרים מצבי סיום (הצלחה/כשל)")
        score -= 5
    
    # Ensure score is in valid range
    score = max(0, min(100, score))
    
    result = DoctrineValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        doctrine_score=score
    )
    
    logger.debug(
        "Doctrine validation: valid=%s, score=%d, errors=%d, warnings=%d",
        result.is_valid, result.doctrine_score, len(errors), len(warnings)
    )
    
    return result


__all__ = [
    "build_validator_prompt",
    "validate_json_schema",
    "DoctrineValidationResult",
    "validate_scenario_doctrine",
]


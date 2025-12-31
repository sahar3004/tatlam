"""
tatlam/core/prompts.py - Centralized Prompt Management

This module provides secure, cached prompt loading and formatting for the Trinity system.
It prevents prompt injection by clearly demarcating user input from system instructions.

Security Principles:
1. System prompts are loaded ONCE at startup and cached
2. User input is ALWAYS wrapped in XML tags to prevent instruction confusion
3. No raw string concatenation with untrusted input
4. All prompts are validated before use

Usage:
    from tatlam.core.prompts import PromptManager, get_prompt_manager

    # Get the singleton instance
    prompts = get_prompt_manager()

    # Format a scenario generation prompt
    formatted = prompts.format_scenario_prompt(
        user_input="צור תרחיש של חפץ חשוד",
        category="חפץ חשוד"
    )

Legacy Usage (backward compatible):
    from tatlam.core.prompts import load_system_prompt, memory_addendum
"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PromptValidationError(Exception):
    """Raised when prompt validation fails."""
    pass


class PromptInjectionDetectedError(Exception):
    """Raised when potential prompt injection is detected in user input."""
    pass


# ==== Prompt File Paths ====
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_SYSTEM_PROMPT_PATH = _BASE_DIR / "system_prompt_he.txt"


@lru_cache(maxsize=1)
def _load_system_prompt_file() -> str:
    """
    Load the system prompt from file ONCE and cache it.

    This function is cached to ensure the file is only read once at startup.
    Call _load_system_prompt_file.cache_clear() to reload (useful in tests).

    Returns:
        The raw system prompt text

    Raises:
        FileNotFoundError: If the prompt file doesn't exist
        UnicodeDecodeError: If the file contains invalid UTF-8
    """
    if not _SYSTEM_PROMPT_PATH.exists():
        logger.warning("System prompt file not found: %s, using fallback", _SYSTEM_PROMPT_PATH)
        return _FALLBACK_PROMPT

    try:
        content = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        logger.debug("Loaded system prompt from %s (%d chars)", _SYSTEM_PROMPT_PATH, len(content))
        return content
    except UnicodeDecodeError as e:
        logger.error("Failed to decode system prompt file: %s, using fallback", e)
        return _FALLBACK_PROMPT


# Fallback prompt if file is missing
_FALLBACK_PROMPT = (
    'אתה מסייע ליצירת תטל"מים מובְנים ואחראיים. שמור על פורמט, עברית תקנית, '
    "וריאליזם מבצעי. אל תמציא קישורים."
)


# ==== Prompt Injection Detection ====

# Patterns that might indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+(instructions|prompts)",
    r"disregard\s+(previous|all|above)",
    r"new\s+instructions?:",
    r"system\s*:\s*",
    r"assistant\s*:\s*",
    r"</?(system|user|assistant)>",
    r"התעלם\s+מ(ההוראות|ההנחיות)",
    r"הוראות\s+חדשות",
]
_COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def _check_for_injection(text: str) -> None:
    """
    Check if text contains potential prompt injection patterns.

    Args:
        text: User input to validate

    Raises:
        PromptInjectionDetectedError: If injection patterns are found
    """
    for pattern in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("Potential prompt injection detected: %s", pattern.pattern)
            raise PromptInjectionDetectedError(
                "Input contains potentially malicious patterns. Please rephrase your request."
            )


def _sanitize_user_input(text: str) -> str:
    """
    Sanitize user input by escaping special characters.

    This prevents the model from interpreting user input as instructions.

    Args:
        text: Raw user input

    Returns:
        Sanitized text safe for inclusion in prompts
    """
    # Replace angle brackets that could be confused with XML tags
    text = text.replace("<", "⟨").replace(">", "⟩")
    return text.strip()


# ==== PromptManager Class ====


class PromptManager:
    """
    Centralized prompt management for the Trinity system.

    This class provides secure prompt formatting with:
    - Cached prompt loading (single file read at startup)
    - User input sanitization and validation
    - Prompt injection detection
    - Clear separation between system instructions and user input

    Thread Safety:
        This class is thread-safe. The system prompt is loaded once and cached.
        Formatting methods are pure functions with no shared mutable state.
    """

    def __init__(self) -> None:
        """Initialize the PromptManager and verify prompts are loadable."""
        # Verify we can load the system prompt (will be cached)
        self._batch_prompt = _load_system_prompt_file()
        logger.debug("PromptManager initialized")

    @property
    def batch_system_prompt(self) -> str:
        """Get the batch processing system prompt (from file)."""
        return self._batch_prompt

    def get_trinity_prompt(self, role: str) -> str:
        """
        Get the Trinity system prompt for a specific role.

        Args:
            role: One of "writer", "judge", or "simulator"

        Returns:
            The system prompt for the specified role

        Raises:
            ValueError: If role is not recognized
        """
        # Import here to avoid circular imports
        from tatlam.core.doctrine import get_system_prompt

        if role not in ("writer", "judge", "simulator"):
            raise ValueError(f"Invalid role: {role}. Must be one of: writer, judge, simulator")
        return get_system_prompt(role)

    def format_scenario_prompt(
        self,
        user_input: str,
        category: str | None = None,
        count: int = 5,
        *,
        validate_injection: bool = True,
    ) -> str:
        """
        Format a scenario generation prompt with user input safely wrapped.

        This method ensures user input cannot be confused with system instructions
        by wrapping it in XML-style tags and sanitizing special characters.

        Args:
            user_input: The user's scenario request (e.g., "תרחיש של חפץ חשוד")
            category: Optional category to restrict scenarios to
            count: Number of scenarios to generate (default: 5)
            validate_injection: Whether to check for injection attempts (default: True)

        Returns:
            Formatted prompt ready for the Writer (Claude)

        Raises:
            PromptValidationError: If user_input is empty or invalid
            PromptInjectionDetectedError: If injection patterns are detected

        Example:
            >>> prompts = PromptManager()
            >>> prompt = prompts.format_scenario_prompt(
            ...     user_input="צור תרחישים של אדם חשוד",
            ...     category="אדם חשוד",
            ...     count=3
            ... )
        """
        # Validate input
        if not user_input or not user_input.strip():
            raise PromptValidationError("User input cannot be empty")

        if validate_injection:
            _check_for_injection(user_input)

        # Sanitize user input
        safe_input = _sanitize_user_input(user_input)
        safe_category = _sanitize_user_input(category) if category else None

        # Get valid categories from the doctrine
        from tatlam.core.categories import CATS
        valid_categories = ", ".join([meta.get("title", "") for meta in CATS.values() if meta.get("title") != "לא מסווג"][:8])

        # Build the prompt with clear demarcation
        category_clause = ""
        if safe_category:
            category_clause = f"\n- הקטגוריה המבוקשת: {safe_category}"

        prompt = f"""
<doctrine_compliance>
כל תרחיש חייב לעמוד בתורת ההפעלה (Trinity Doctrine).
</doctrine_compliance>

<user_request>
{safe_input}
</user_request>

<required_format>
📋 שדות חובה בכל תרחיש:
1. title - כותרת ייחודית ותיאורית (3-8 מילים)
2. category - אחת מ: {valid_categories}
3. threat_level - LOW / MEDIUM / HIGH / CRITICAL
4. location - מפלס (-3 עד 0) + אזור ספציפי בתחנת אלנבי
5. background - סיפור מקרה (50-200 מילים)
6. steps - 4-8 שלבי תגובה מפורטים לפי הנהלים
7. decision_points - 2-4 נקודות הכרעה עם הפניות חוקיות
8. escalation_conditions - תנאי הסלמה
9. end_state_success - מצב סיום מוצלח
10. end_state_failure - מצב כשל
11. lessons_learned - 2-4 לקחים
</required_format>

<safety_rules>
🚨 כללי ברזל (הפרה = תרחיש פסול):
- אין לגעת בחפץ חשוד! טווח מינימלי 50 מ'
- טווחי רכב חשוד: אופנוע 100 מ', רכב 200 מ', משאית 400 מ'
- פתיחה באש: רק לפי Ultima Ratio (אמצעי + כוונה + סכנת חיים מיידית)
- חיפוש: רק בחשד סביר לפי חוק הסמכויות 2005
- איסור אפליה: ללא פרופיילינג גזעי/דתי
</safety_rules>

<constraints>
- מספר תרחישים: {count}{category_clause}
- שונות: שחקנים, זמן, סביבה, טריגר שונים בכל תרחיש
- אותנטיות: השתמש בנתונים מדויקים מהדוקטרינה (משקלי מטענים, שמות קומות)
- פורמט: Markdown מובנה עם כל השדות הנדרשים
</constraints>
"""
        return prompt.strip()

    def format_audit_prompt(
        self,
        scenario_text: str,
        scenario_metadata: dict[str, Any] | None = None,
        *,
        validate_injection: bool = True,
    ) -> str:
        """
        Format an audit prompt for the Judge (Gemini).

        Args:
            scenario_text: The scenario text to audit (in markdown format)
            scenario_metadata: Optional metadata dict with title, category, etc.
            validate_injection: Whether to check for injection attempts

        Returns:
            Formatted prompt ready for the Judge

        Raises:
            PromptValidationError: If scenario_text is empty
        """
        if not scenario_text or not scenario_text.strip():
            raise PromptValidationError("Scenario text cannot be empty")

        if validate_injection:
            _check_for_injection(scenario_text)

        safe_scenario = _sanitize_user_input(scenario_text)

        metadata_section = ""
        if scenario_metadata:
            metadata_section = "\n<scenario_metadata>\n"
            for key, value in scenario_metadata.items():
                if value is not None:
                    safe_value = _sanitize_user_input(str(value))
                    metadata_section += f"  {key}: {safe_value}\n"
            metadata_section += "</scenario_metadata>\n"

        prompt = f"""
<audit_task>
בצע ביקורת מקצועית על התרחיש הבא לפי התורה המבצעית.
</audit_task>
{metadata_section}
<scenario_content>
{safe_scenario}
</scenario_content>

<instructions>
- העריך את התרחיש לפי מסגרת הבטיחות, החוקיות והטקטיקה
- תן ציון 0-100 עם הסבר מפורט
- החמר במיוחד על:
  * נגיעה בחפץ חשוד (ציון 0 מיידי)
  * שימוש בכוח לא מידתי
  * הפרת סמכויות
- ציין נקודות חוזק וחולשה
</instructions>
"""
        return prompt.strip()

    def format_simulation_system_prompt(
        self,
        scenario_context: str | None = None,
        character_type: str = "civilian",
    ) -> str:
        """
        Format the system prompt for the Simulator.

        Args:
            scenario_context: Optional context about the current scenario
            character_type: Type of character to simulate ("civilian", "suspect", "terrorist")

        Returns:
            System prompt for the Simulator

        Raises:
            ValueError: If character_type is invalid
        """
        valid_types = ("civilian", "suspect", "terrorist")
        if character_type not in valid_types:
            raise ValueError(f"Invalid character_type: {character_type}. Must be one of: {valid_types}")

        base_prompt = self.get_trinity_prompt("simulator")

        context_section = ""
        if scenario_context:
            safe_context = _sanitize_user_input(scenario_context)
            context_section = f"""

<current_scenario>
{safe_context}
</current_scenario>
"""

        character_instructions = {
            "civilian": "אתה אזרח רגיל. דרוש את זכויותיך אם נדרש.",
            "suspect": "אתה אדם חשוד. פעל באופן שמעורר חשד אך אל תודה בכוונות.",
            "terrorist": "אתה מחבל. פעל לפי אינדיקטורים התנהגותיים מהתורה.",
        }

        prompt = f"""{base_prompt}
{context_section}
<character_role>
{character_instructions[character_type]}
</character_role>

<response_rules>
- Hebrew ONLY (עברית בלבד).
- ABSOLUTELY NO ARABIC (אסור להשתמש בערבית).
- Do not use Arabic slang/words even if the character is suspicious.
- Speak naturally but strictly in Hebrew.
- שמור על הדמות לאורך כל הסימולציה
- הגב באופן ריאלי לפעולות המאבטח
</response_rules>
"""
        return prompt.strip()

    def validate_scenario_dict(self, scenario: dict[str, Any]) -> list[str]:
        """
        Validate that a scenario dictionary has required fields for auditing.

        Args:
            scenario: Scenario dictionary to validate

        Returns:
            List of missing or invalid fields (empty if valid)
        """
        required_fields = ["title", "category", "steps"]
        missing = []

        for field in required_fields:
            if field not in scenario:
                missing.append(f"Missing required field: {field}")
            elif field == "steps" and not isinstance(scenario.get("steps"), list):
                missing.append("Field 'steps' must be a list")

        return missing


# ==== Module-Level Singleton Access ====

_prompt_manager: PromptManager | None = None


def get_prompt_manager() -> PromptManager:
    """
    Get the singleton PromptManager instance.

    Returns:
        The global PromptManager instance
    """
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


# ==== Legacy Compatibility Functions ====


def load_system_prompt(path: str = "system_prompt_he.txt") -> str:
    """
    Load the batch system prompt (legacy compatibility function).

    Args:
        path: Path to the system prompt file (ignored, uses cached version)

    Returns:
        The batch system prompt text
    """
    return _load_system_prompt_file()


def memory_addendum() -> dict[str, str]:
    """
    Get the memory addendum for duplicate checking (legacy compatibility).

    Returns:
        Dict with role and content for memory context
    """
    return {
        "role": "system",
        "content": (
            "בדוק בזיכרון הארגוני דמיון לתטל״מים קיימים; אם דומה – שנה כותרת/זווית/"
            "actors/זמן/סביבה כך שתיווצר שונות. אין להשתמש בכותרת קיימת."
        ),
    }


__all__ = [
    # Classes
    "PromptManager",
    # Exceptions
    "PromptValidationError",
    "PromptInjectionDetectedError",
    # Functions
    "get_prompt_manager",
    "load_system_prompt",
    "memory_addendum",
]

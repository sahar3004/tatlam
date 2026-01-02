import json
import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


def strip_markdown_and_parse_json(text: str) -> dict[str, Any] | list[Any] | None:
    """
    Secure JSON parser that strips markdown code blocks before parsing.

    Security: Uses only json.loads() without regex extraction to prevent
    injection vulnerabilities. Handles LLM responses that may contain:
    - Markdown code blocks: ```json ... ``` or ``` ... ```
    - Plain JSON objects or arrays

    Returns:
        Parsed JSON object (dict or list) or None if parsing fails
    """
    if not text:
        return None

    # Step 1: Strip markdown code blocks
    cleaned = text.strip()

    # Remove opening markdown fence with optional language specifier
    if cleaned.startswith("```"):
        # Find the end of the first line (language specifier)
        first_line_end = cleaned.find("\n")
        if first_line_end != -1:
            cleaned = cleaned[first_line_end + 1 :]

    # Remove closing markdown fence
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # Step 2: Try direct JSON parsing (secure - no regex)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        LOGGER.debug("JSON parsing failed: %s", e)
        return None

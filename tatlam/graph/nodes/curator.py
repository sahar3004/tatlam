"""
tatlam/graph/nodes/curator.py - The Curator Node

The Curator uses a Cloud LLM (Gemini) to filter the raw seeds from the Scout.
It selects only the most promising, doctrine-aligned, and interesting ideas
before passing them to the Writer.

Key Features:
- Uses Cloud LLM for high-quality filtering
- Applies doctrine knowledge for safety/legality checks
- Selects top N seeds based on operational value
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from tatlam.graph.state import SwarmState, WorkflowPhase
from tatlam.settings import get_settings

if TYPE_CHECKING:
    from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_cloud_client() -> "OpenAI | None":
    """Get the cloud LLM client."""
    from tatlam.core.llm_factory import client_cloud, ConfigurationError

    try:
        return client_cloud()
    except (ConfigurationError, Exception) as e:
        logger.warning("Cloud LLM not available for Curator: %s", e)
        return None


def _get_doctrine_context() -> str:
    """Get key doctrine elements for filtering."""
    from tatlam.core.doctrine import TRINITY_DOCTRINE
    
    doctrine = TRINITY_DOCTRINE
    safety = doctrine.get("procedures", {}).get("suspicious_object", {}).get("safety_distances", {})
    
    return f"""
קריטריוני סינון מהדוקטרינה:
- טווח בטיחות מחפץ חשוד: {safety.get('object_urban', '50 מטר')}
- טווח מרכב: {safety.get('car', '100 מטר')}
- פתיחה באש: רק לפי "אמצעי + כוונה + סכנת חיים מיידית"
- איסור מוחלט על פרופיילינג גזעי
"""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_curator_llm(client: "OpenAI", model: str, prompt: str, system_prompt: str) -> str:
    """Call cloud LLM for curation."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return (response.choices[0].message.content or "").strip()


def _build_curator_prompt(seeds: list[str], select_count: int, category: str) -> str:
    """Build the prompt for seed curation."""
    seeds_text = "\n".join([f"{i+1}. {seed}" for i, seed in enumerate(seeds)])
    
    return f"""
🎯 משימה: בחר את {select_count} הרעיונות הטובים ביותר מתוך הרשימה

📂 קטגוריה נדרשת: {category}

📋 רשימת הרעיונות:
{seeds_text}

🔍 קריטריוני בחירה (לפי סדר חשיבות):
1. **רלוונטיות** - הרעיון מתאים לקטגוריה הנדרשת
2. **ריאליזם** - הרעיון אפשרי ולא פנטזיה
3. **עניין אימוני** - הרעיון מציב דילמה או אתגר למאבטח
4. **תאימות לדוקטרינה** - לא מעודד הפרות בטיחות או חוק
5. **מגוון** - בחר רעיונות שונים זה מזה

⚠️ דחה רעיונות:
- שמעודדים נגיעה בחפץ חשוד
- שכוללים פרופיילינג גזעי
- שלא מתאימים לקטגוריה
- שחוזרים על עצמם

📤 פלט נדרש (JSON בלבד):
{{
  "selected_seeds": ["רעיון 1", "רעיון 2", ...],
  "reasoning": "הסבר קצר לבחירה"
}}
"""


def _parse_curated_seeds(response_text: str, original_seeds: list[str]) -> list[str]:
    """Parse the curator response and extract selected seeds."""
    try:
        data = json.loads(response_text)
        selected = data.get("selected_seeds", [])
        
        if isinstance(selected, list) and len(selected) > 0:
            # Return the selected seeds
            return [str(s) for s in selected if isinstance(s, str) and len(s) > 5]
        
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("Failed to parse curator response: %s", e)
    
    # Fallback: return first N original seeds
    return original_seeds[:8]


def curator_node(state: SwarmState) -> SwarmState:
    """
    Curator Node: Filter scout seeds using Cloud LLM.
    
    This node:
    1. Takes raw seeds from scout_seeds
    2. Asks Cloud LLM to select the best ones
    3. Updates scout_seeds with only the winners
    
    Args:
        state: Current SwarmState
        
    Returns:
        Updated SwarmState with filtered scout_seeds
    """
    state.log_phase_change(WorkflowPhase.CURATING)
    
    # Check if we have seeds to curate
    if not state.scout_seeds:
        logger.info("Curator skipped: no seeds from Scout")
        return state
    
    logger.info(
        "Curator starting: filtering %d seeds down to %d",
        len(state.scout_seeds), state.batch_size
    )
    
    # Get cloud client
    cloud_client = _get_cloud_client()
    
    if not cloud_client:
        logger.warning("Curator skipped: Cloud LLM not available, using all seeds")
        state.scout_seeds = state.scout_seeds[:state.batch_size]
        return state
    
    settings = get_settings()
    
    # Build prompts
    doctrine_context = _get_doctrine_context()
    system_prompt = f"""אתה אוצר (Curator) במערכת Trinity לאבטחת תחבורה ציבורית.
תפקידך לסנן רעיונות ולבחור רק את הטובים ביותר.

{doctrine_context}

החזר JSON בלבד."""

    user_prompt = _build_curator_prompt(
        state.scout_seeds, 
        state.batch_size, 
        state.category
    )
    
    try:
        response_text = _call_curator_llm(
            cloud_client,
            settings.VALIDATOR_MODEL,  # Use the validator model (fast, cheap)
            user_prompt,
            system_prompt
        )
        
        # Parse response
        curated_seeds = _parse_curated_seeds(response_text, state.scout_seeds)
        
        logger.info(
            "Curator completed: selected %d seeds from %d",
            len(curated_seeds), len(state.scout_seeds)
        )
        
        state.scout_seeds = curated_seeds
        
    except Exception as e:
        logger.warning("Curator failed: %s, using first %d seeds", e, state.batch_size)
        state.metrics.llm_errors += 1
        state.scout_seeds = state.scout_seeds[:state.batch_size]
    
    return state


__all__ = ["curator_node"]

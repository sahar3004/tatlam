"""
tatlam/graph/nodes/scout.py - The Scout Node

The Scout uses the local LLM to generate a high volume of raw scenario IDEAS (seeds).
These seeds are short, one-line concepts that will be filtered by the Curator
and then expanded by the Writer.

Key Features:
- Uses local LLM for cost-free ideation
- Generates many ideas quickly (quantity over quality)
- Outputs a list of raw text seeds
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

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


def _get_local_client() -> "OpenAI | None":
    """Get the local LLM client."""
    from tatlam.core.llm_factory import client_local, ConfigurationError

    try:
        return client_local()
    except (ConfigurationError, Exception) as e:
        logger.warning("Local LLM not available for Scout: %s", e)
        return None


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_local_llm(client: "OpenAI", model: str, prompt: str) -> str:
    """Call local LLM for idea generation."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "אתה גנרטור רעיונות יצירתי. תפקידך להציע רעיונות מגוונים ומאתגרים לתרחישי אבטחה."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,  # High creativity
    )
    return (response.choices[0].message.content or "").strip()


def _build_scout_prompt(category: str, count: int = 20) -> str:
    """Build the prompt for seed generation."""
    return f"""
🎯 משימה: ייצור {count} רעיונות גולמיים לתרחישי אבטחה בקטגוריה: "{category}"

📋 כללים:
1. כל רעיון בשורה נפרדת
2. כל רעיון: משפט אחד קצר (10-30 מילים)
3. מגוון מקסימלי - כל רעיון שונה מהקודמים
4. התייחס לתחנת רכבת קלה "אלנבי" בתל אביב
5. כלול רעיונות מאתגרים ולא שגרתיים

📍 מיקומים אפשריים: רציף, כרטוס, מבואה, מדרגות, שירותים, חדר טכני

דוגמאות לפורמט:
- אדם עם מעיל כבד בקיץ מתנהג בעצבנות ליד הכרטוס
- תיק עזוב מתחת לספסל ברציף עם חוטים בולטים
- רחפן נמוך מעל הכניסה הראשית בשעת לחץ

עכשיו, צור {count} רעיונות חדשים ומגוונים:
"""


def _parse_seeds(raw_text: str) -> list[str]:
    """Parse the raw LLM output into a list of seeds."""
    lines = raw_text.strip().split("\n")
    seeds = []
    
    for line in lines:
        # Clean the line
        line = line.strip()
        # Remove common prefixes like "1.", "-", "*", "•"
        line = re.sub(r'^[\d]+[.)]\s*', '', line)
        line = re.sub(r'^[-*•]\s*', '', line)
        line = line.strip()
        
        # Filter valid seeds
        if len(line) > 10 and len(line) < 200:  # Reasonable length
            seeds.append(line)
    
    return seeds


def scout_node(state: SwarmState) -> SwarmState:
    """
    Scout Node: Generate raw scenario idea seeds using local LLM.
    
    This node:
    1. Calls the local LLM to brainstorm many ideas quickly
    2. Parses the output into individual seeds
    3. Stores them in state.scout_seeds for the Curator
    
    Args:
        state: Current SwarmState
        
    Returns:
        Updated SwarmState with scout_seeds populated
    """
    state.log_phase_change(WorkflowPhase.SCOUTING)
    
    # Calculate how many seeds we need
    # We want more seeds than target to give Curator good options
    seed_count = max(20, state.batch_size * 3)
    
    logger.info(
        "Scout starting: generating %d idea seeds for category '%s'",
        seed_count, state.category
    )
    
    # Get local client
    local_client = _get_local_client()
    
    if not local_client:
        logger.warning("Scout skipped: Local LLM not available, passing to Writer directly")
        return state
    
    settings = get_settings()
    
    # Build and call prompt
    prompt = _build_scout_prompt(state.category, seed_count)
    
    try:
        raw_text = _call_local_llm(
            local_client,
            settings.LOCAL_MODEL_NAME,
            prompt
        )
        
        # Parse seeds
        seeds = _parse_seeds(raw_text)
        state.scout_seeds = seeds
        
        logger.info(
            "Scout completed: generated %d seeds from %d chars of raw text",
            len(seeds), len(raw_text)
        )
        
    except Exception as e:
        logger.warning("Scout failed: %s, continuing without seeds", e)
        state.metrics.llm_errors += 1
        # Don't fail the workflow, just continue without seeds
    
    return state


__all__ = ["scout_node"]

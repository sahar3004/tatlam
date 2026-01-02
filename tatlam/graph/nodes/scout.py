"""
tatlam/graph/nodes/scout.py - The Scout Node (2-Stage Pipeline)

The Scout uses a 2-stage approach for generating scenario ideas:
1. Stage 1 (Local Qwen): Generate raw, diverse ideas quickly and cheaply
2. Stage 2 (Claude Sonnet): Refine and stabilize ideas, or serve as fallback

Key Features:
- 2-stage pipeline for quality + cost optimization
- Local LLM for creative brainstorming (high temperature)
- Cloud Claude for refinement and structure
- Graceful fallback if local LLM unavailable
"""
from __future__ import annotations

import logging
import re
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
from tatlam.core.doctrine import get_system_prompt

if TYPE_CHECKING:
    from openai import OpenAI
    import anthropic

logger = logging.getLogger(__name__)


def _get_local_client() -> "OpenAI | None":
    """Get the local LLM client."""
    from tatlam.core.llm_factory import client_local, ConfigurationError

    try:
        return client_local()
    except (ConfigurationError, Exception) as e:
        logger.debug("Local LLM not available for Scout: %s", e)
        return None


def _get_anthropic_client() -> "anthropic.Anthropic | None":
    """Get the Anthropic Claude client for Stage 2."""
    from tatlam.core.llm_factory import create_writer_client, ConfigurationError

    try:
        return create_writer_client()
    except (ConfigurationError, Exception) as e:
        logger.debug("Anthropic client not available for Scout Stage 2: %s", e)
        return None


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_local_llm(client: "OpenAI", model: str, system: str, prompt: str) -> str:
    """Call local LLM for Stage 1 idea generation."""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.95,  # Very high creativity for diverse ideas
    )
    return (response.choices[0].message.content or "").strip()


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_claude_refinement(client: Any, model: str, raw_ideas: str, category: str) -> str:
    """Call Claude Sonnet for Stage 2 refinement."""
    system_prompt = """אתה מומחה לאבטחת תחבורה ציבורית במערכת Trinity.
תפקידך לקחת רעיונות גולמיים לתרחישי אבטחה ולשפר אותם:

1. הסר רעיונות לא ריאליסטיים או לא רלוונטיים לקטגוריה
2. שפר ניסוח - הפוך כל רעיון לברור ותמציתי
3. הוסף פרטים מקצועיים (מיקום ספציפי, אינדיקטורים)
4. וודא מגוון - אם יש חזרות, מחק או החלף
5. שמור על 15-20 הרעיונות הטובים ביותר

פלט: רשימת רעיונות משופרים, כל אחד בשורה נפרדת."""

    user_prompt = f"""קטגוריה: {category}

רעיונות גולמיים לשיפור:
{raw_ideas}

החזר רשימת רעיונות משופרים (15-20), כל אחד בשורה נפרדת:"""

    response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return (response.content[0].text if response.content else "").strip()


def _build_scout_prompt(category: str, count: int = 25) -> str:
    """Build the prompt for Stage 1 seed generation."""
    return f"""🎯 משימה: ייצור {count} רעיונות גולמיים ומגוונים לתרחישי אבטחה

📂 קטגוריה: "{category}"

📍 זירת הפעולה: תחנת רכבת קלה "אלנבי" בתל אביב
   - מפלס 0: רחוב, כניסה ראשית
   - מפלס -1: כרטוס, בידוק, מבואה
   - מפלס -2: קומה טכנית (סטרילי)
   - מפלס -3: רציפים

📋 כללים:
1. כל רעיון בשורה נפרדת
2. כל רעיון: משפט אחד (15-40 מילים)
3. מגוון מקסימלי - כל רעיון שונה לחלוטין
4. התמקד באיומים ריאליסטיים ורלוונטיים לקטגוריה
5. כלול אינדיקטורים התנהגותיים ספציפיים

🧠 טיפים ליצירתיות:
- חשוב על שעות שונות ביום
- חשוב על מזג אוויר ועונות
- חשוב על סוגי אנשים שונים
- חשוב על תרחישי קצה נדירים

דוגמאות לפורמט:
• אדם עם מעיל גשם ארוך ביום שמשי עומד ליד עמוד במבואה ומביט סביבו בעצבנות
• ילד כבן 10 מסתובב לבדו ברציף ללא ליווי מבוגר ונראה מבולבל
• רחפן לבן קטן מרחף מעל הכניסה בגובה 15 מטר ואינו זז

צור {count} רעיונות חדשים ומגוונים:"""


def _build_fallback_prompt(category: str, count: int = 20) -> str:
    """Build prompt for Claude-only fallback when local LLM unavailable."""
    return f"""אתה מומחה ליצירת תרחישי אימון לאבטחת תחבורה ציבורית.

צור {count} רעיונות מגוונים לתרחישי אבטחה בקטגוריה: "{category}"

הזירה: תחנת רכבת קלה "אלנבי" בתל אביב (4 מפלסים)

כללים:
- כל רעיון בשורה נפרדת
- כל רעיון: משפט אחד עם אינדיקטורים ספציפיים
- מגוון מקסימלי

החזר רשימת {count} רעיונות:"""


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
        
        # Filter valid seeds (reasonable length)
        if 15 < len(line) < 250:
            seeds.append(line)
    
    return seeds


def scout_node(state: SwarmState) -> SwarmState:
    """
    Scout Node: 2-Stage idea generation pipeline.
    
    Stage 1 (Local Qwen): Generate raw, creative ideas quickly
    Stage 2 (Claude Sonnet): Refine items and ensure quality
    
    If Local LLM unavailable, Claude serves as complete fallback.
    
    Args:
        state: Current SwarmState
        
    Returns:
        Updated SwarmState with scout_seeds populated
    """
    state.log_phase_change(WorkflowPhase.SCOUTING)
    
    settings = get_settings()
    seed_count = max(25, state.batch_size * 3)
    
    logger.info(
        "Scout starting 2-stage pipeline for category '%s' (target: %d seeds)",
        state.category, seed_count
    )
    
    # Get clients
    local_client = _get_local_client()
    anthropic_client = _get_anthropic_client()
    
    raw_ideas = ""
    refined_ideas = ""
    
    # === STAGE 1: Local Qwen - Raw Idea Generation ===
    if local_client:
        try:
            logger.info("Scout Stage 1: Generating raw ideas with Local Qwen")
            
            system_prompt = "אתה יוצר רעיונות יצירתי ומגוון. תפקידך להציע רעיונות מאתגרים ולא שגרתיים לתרחישי אבטחה."
            user_prompt = _build_scout_prompt(state.category, seed_count)
            
            raw_ideas = _call_local_llm(
                local_client,
                settings.LOCAL_MODEL_NAME,
                system_prompt,
                user_prompt
            )
            
            logger.info("Scout Stage 1 complete: %d chars of raw ideas", len(raw_ideas))
            
        except Exception as e:
            logger.warning("Scout Stage 1 failed: %s", e)
            state.metrics.llm_errors += 1
            raw_ideas = ""
    
    # === STAGE 2: Claude Sonnet - Refinement ===
    if anthropic_client:
        try:
            if raw_ideas:
                # Refinement mode: improve local ideas
                logger.info("Scout Stage 2: Refining ideas with Claude Sonnet")
                refined_ideas = _call_claude_refinement(
                    anthropic_client,
                    settings.WRITER_MODEL_NAME,  # Claude Sonnet 4.5
                    raw_ideas,
                    state.category
                )
            else:
                # Fallback mode: generate from scratch
                logger.info("Scout Stage 2: Fallback - generating with Claude Sonnet")
                fallback_prompt = _build_fallback_prompt(state.category, 20)
                
                response = anthropic_client.messages.create(
                    model=settings.WRITER_MODEL_NAME,
                    max_tokens=2048,
                    system="אתה מומחה ליצירת תרחישי אימון לאבטחת תחבורה ציבורית.",
                    messages=[{"role": "user", "content": fallback_prompt}],
                )
                refined_ideas = (response.content[0].text if response.content else "").strip()
            
            logger.info("Scout Stage 2 complete: %d chars refined", len(refined_ideas))
            
        except Exception as e:
            logger.warning("Scout Stage 2 failed: %s", e)
            state.metrics.llm_errors += 1
            # Use raw ideas if refinement failed
            refined_ideas = raw_ideas
    else:
        # No Claude available - use raw ideas directly
        refined_ideas = raw_ideas
    
    # === Parse and store seeds ===
    final_text = refined_ideas or raw_ideas
    
    if final_text:
        seeds = _parse_seeds(final_text)
        state.scout_seeds = seeds
        logger.info(
            "Scout pipeline complete: %d seeds generated (Local: %s, Claude: %s)",
            len(seeds),
            "✓" if local_client else "✗",
            "✓" if anthropic_client else "✗"
        )
    else:
        logger.warning("Scout failed: No ideas generated, continuing without seeds")
    
    return state


__all__ = ["scout_node"]

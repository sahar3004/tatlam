"""
tatlam/graph/nodes/writer.py - The Writer Node

The Writer generates scenario candidates using the local LLM.
It leverages the existing prompt engineering from run_batch.py
and supports critique-driven regeneration for repair cycles.

Key Features:
- Uses local LLM (Qwen) with cloud fallback
- Incorporates Gold examples for quality
- Supports repair mode with critique feedback
- Structured logging for observability
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from tatlam.graph.state import SwarmState, ScenarioStatus, WorkflowPhase
from tatlam.settings import get_settings

if TYPE_CHECKING:
    from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_clients() -> tuple["OpenAI | None", "OpenAI | None"]:
    """Get local and cloud clients."""
    from tatlam.core.llm_factory import client_local, client_cloud, ConfigurationError

    local_client = None
    cloud_client = None

    try:
        local_client = client_local()
    except (ConfigurationError, Exception) as e:
        logger.warning("Local LLM not available: %s", e)

    try:
        cloud_client = client_cloud()
    except (ConfigurationError, Exception) as e:
        logger.debug("Cloud client not available: %s", e)

    return local_client, cloud_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_llm(client: "OpenAI", model: str, messages: list[dict], temperature: float = 0.7) -> str:
    """Call LLM with retry logic."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()


def _get_doctrine_context() -> str:
    """
    Extract key doctrine elements for the Writer prompt.
    This ensures the Writer generates scenarios aligned with the doctrine.
    """
    from tatlam.core.doctrine import TRINITY_DOCTRINE

    doctrine = TRINITY_DOCTRINE

    # Safety distances
    safety = doctrine.get("procedures", {}).get("suspicious_object", {}).get("safety_distances", {})

    # Legal framework
    legal = doctrine.get("legal_framework", {})
    fire = legal.get("open_fire_regulations", {})

    # Venue context
    venue = doctrine.get("venue_allenby", {})

    return f"""
📚 תורת ההפעלה (DOCTRINE) - חובה!

🚨 טווחי בטיחות:
- חפץ חשוד עירוני: {safety.get('object_urban', '50 מטר')}
- רכב: {safety.get('car', '100 מטר')} | משאית: {safety.get('truck', '400 מטר')}

⚖️ פתיחה באש (Ultima Ratio):
- עקרון: {fire.get('core_principle', 'אמצעי אחרון')}
- תנאים: סכנת חיים + אמצעי + כוונה

🏢 תחנת אלנבי:
- עומק: {venue.get('specs', {}).get('depth', '28 מטר')}
- מפלס -2: שטח סטרילי (כל אדם = אירוע)
"""


def _build_generation_prompt(state: SwarmState, repair_critique: str = "") -> str:
    """
    Build the user prompt for scenario generation.

    Based on build_batch_user_prompt from run_batch.py but adapted
    for the multi-agent context. Integrates doctrine context and scout seeds.
    """
    category = state.category
    count = state.batch_size
    bundle_id = state.bundle_id

    # Get doctrine context
    doctrine_context = _get_doctrine_context()

    # Repair mode
    repair_section = ""
    if repair_critique:
        repair_section = f"""
⚠️ תיקון נדרש:
{repair_critique}
"""

    # Scout seeds section (from Scout-Curator pipeline)
    seeds_section = ""
    if state.scout_seeds:
        seeds_list = "\n".join([f"• {seed}" for seed in state.scout_seeds[:count]])
        seeds_section = f"""
🌱 רעיונות שנבחרו מהגשש (פתח כל אחד לתרחיש מלא):
{seeds_list}

הנחיה: פתח כל רעיון לתרחיש מלא ומפורט לפי הפורמט למטה.
"""

    # Gold examples
    gold_section = ""
    if state.gold_examples:
        gold_section = f"\nדוגמאות Gold:\n{state.gold_examples[:3000]}"

    prompt = f"""{doctrine_context}
{repair_section}
{seeds_section}
batch_id: {bundle_id}
category: {category}
count: {count}

מטרה: צור {count} תטל״מים ייחודיים בקטגוריה "{category}".

🧠 מועצת המומחים (The Hexagon - דיון פנימי):
1) קמב"ץ — נטרול איום, חתירה למגע
2) יועמ"ש — חוק הסמכויות 2005, מידתיות
3) קמ"ן — איום הייחוס 2025, אינדיקטורים
4) מהנדס בטיחות — מבנה אלנבי, סכנות המון
5) קצין אתיקה — מניעת פרופיילינג
6) מנהל הביטחון (MAGEN) — פק"מ, מעגלי אבטחה

כללי איכות:
- שונות מלאה בין תטל״מים
- עברית מקצועית, תפעולית
- שרשרת פיקוד: מאבטח ↔ מוקד ↔ משטרה/חבלן
- נתונים מדויקים מהדוקטרינה

פורמט לכל תטל״ם:
🧩 כותרת: [קצרה]
📂 קטגוריה: {category}
🔥 רמת סיכון: [נמוכה/בינונית/גבוהה/גבוהה מאוד]
📊 רמת סבירות: [נמוכה/בינונית/גבוהה]
🧠 רמת מורכבות: [נמוכה/בינונית/גבוהה]

📋 סיפור מקרה:
- מיקום: [מפלס + אזור באלנבי]
- תיאור: [עלילה, Actors, דילמה]

🎯 שלבי תגובה:
• צעד 1-4 לפי הנהלים

🔫 נוהל פתיחה באש: [לפי Ultima Ratio]
😷 שימוש במסכה: [כן/לא + סיבה]
🎥 רקע מבצעי: [אירוע אמיתי או "אין תיעוד"]
📎 לינק: [ריק אם אין]
CCTV: [מה לבקש מהמוקד]
סמכויות: [חוק הסמכויות 2005]
נקודות הכרעה: [דילמות + הפניה חוקית]
תנאי הסלמה: [מתי להעלות רמה]
הצלחת אירוע: [קריטריונים]
כשל אירוע: [מה השתבש]
לקחים: [2-4 נקודות]
וריאציות: [גרסאות]
{gold_section}
"""
    return prompt.strip()


def _load_gold_examples(category: str) -> str:
    """Load gold examples from DB or filesystem."""
    # Import here to avoid circular imports
    from sqlalchemy import func, select
    from tatlam.infra.db import get_session
    from tatlam.infra.models import Scenario

    gold_text = ""
    try:
        with get_session() as session:
            stmt = (
                select(Scenario.title, Scenario.background, Scenario.steps)
                .where(func.lower(Scenario.approved_by) == "gold")
                .order_by(Scenario.id.desc())
                .limit(10)
            )

            rows = session.execute(stmt).fetchall()
            parts = []
            for title, background, steps in rows:
                part = f"### {title}\nרקע: {background or ''}\n"
                parts.append(part)
            gold_text = "\n".join(parts)
    except Exception as e:
        logger.debug("Failed to load gold examples: %s", e)

    return gold_text[:4000] if gold_text else ""


def writer_node(state: SwarmState) -> SwarmState:
    """
    Writer Node: Generate scenario candidates.

    This node:
    1. Loads Gold examples for quality guidance
    2. Builds the generation prompt (with repair critique if applicable)
    3. Calls the local LLM (with cloud fallback)
    4. Stores raw drafts in state for the Clerk to validate

    Args:
        state: Current SwarmState

    Returns:
        Updated SwarmState with new draft candidates
    """
    state.log_phase_change(WorkflowPhase.WRITING)
    state.iteration += 1

    logger.info(
        "Writer starting iteration %d for category '%s' (need %d more)",
        state.iteration, state.category, state.target_count - len(state.approved_scenarios)
    )

    # Load gold examples if not already loaded
    if not state.gold_examples:
        state.gold_examples = _load_gold_examples(state.category)

    # Check for repair mode (scenarios needing rework)
    repair_critique = ""
    scenarios_to_repair = [
        c for c in state.candidates
        if c.status == ScenarioStatus.REJECTED and c.attempt_count <= state.max_retries_per_scenario
    ]
    if scenarios_to_repair:
        critiques = [c.critique for c in scenarios_to_repair if c.critique]
        repair_critique = "\n".join(critiques[:3])  # Top 3 critiques

    # Build prompt
    user_prompt = _build_generation_prompt(state, repair_critique)

    # Load system prompt
    from tatlam.core.prompts import load_system_prompt, memory_addendum
    system_prompt = load_system_prompt()
    memory_msg = memory_addendum()

    # Get LLM clients
    local_client, cloud_client = _get_clients()
    settings = get_settings()

    # Determine primary model based on settings
    use_cloud_first = settings.WRITER_MODEL_PROVIDER in ("anthropic", "openai", "google")
    
    draft_text = ""
    model_used = ""

    # Strategy: Cloud First (if configured)
    if use_cloud_first and cloud_client:
        try:
             # Use specific writer model if defined, else generic gen model
            model_used = settings.WRITER_MODEL_NAME or settings.GEN_MODEL
            logger.debug("Calling Cloud Writer (%s): %s", settings.WRITER_MODEL_PROVIDER, model_used)
            
            # Use specific client method based on provider if needed, currently specialized wrappers 
            # should handle this, but here we use the generic _call_llm wrapper which expects OpenAI-like interface
            # For Anthropic/Gemini, we need to ensure the client wrapper adapts it, 
            # OR we use the specific client protocols.
            
            # NOTE: For now, assuming cloud_client is OpenAI-compatible (via LiteLLM or direct)
            # If WRITER_MODEL_PROVIDER is anthropic, we might need specific handling if not proxied.
            
            draft_text = _call_llm(
                cloud_client,
                model_used,
                [
                    {"role": "system", "content": system_prompt},
                    memory_msg,
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception as e:
            logger.warning("Cloud Writer failed: %s, falling back to Local if available", e)
            state.metrics.llm_errors += 1

    # Strategy: Local (Primary or Fallback)
    if not draft_text and local_client:
        try:
            model_used = settings.LOCAL_MODEL_NAME
            logger.debug("Calling Local Writer: %s", model_used)
            draft_text = _call_llm(
                local_client,
                model_used,
                [
                    {"role": "system", "content": system_prompt},
                    memory_msg,
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
            )
        except Exception as e:
            logger.warning("Local Writer failed: %s", e)
            state.metrics.llm_errors += 1

    # Strategy: Cloud Fallback (if Local was primary and failed)
    if not draft_text and not use_cloud_first and cloud_client:
         try:
            model_used = settings.GEN_MODEL
            logger.debug("Calling Cloud Fallback: %s", model_used)
            draft_text = _call_llm(
                cloud_client,
                model_used,
                [
                    {"role": "system", "content": system_prompt},
                    memory_msg,
                    {"role": "user", "content": user_prompt},
                ],
            )
         except Exception as e:
            logger.error("Cloud Fallback failed: %s", e)
            state.metrics.llm_errors += 1

    if not draft_text:
        state.add_error("Writer failed: all configured LLMs failed")
        return state

    if not draft_text:
        state.add_error("Writer failed: no LLM response received")
        return state

    # Store the raw draft for the Clerk to process
    # We store it as a special "raw" candidate
    raw_candidate = state.add_candidate({
        "_raw_text": draft_text,
        "_model": model_used,
        "_is_raw_draft": True,
        "category": state.category,
    })
    raw_candidate.status = ScenarioStatus.DRAFT

    logger.info(
        "Writer completed: generated %d chars of draft text using %s",
        len(draft_text), model_used
    )

    return state


__all__ = ["writer_node"]

"""
tatlam/graph/nodes/writer.py - The Writer Node

The Writer generates full scenario candidates using Claude Sonnet 4.5.
It expands seed ideas from the Scout/Curator pipeline into complete,
doctrine-compliant training scenarios.

Key Features:
- Uses Claude Sonnet 4.5 as primary model (Cloud First)
- Local LLM available as fallback
- Incorporates seed ideas from Scout pipeline
- Incorporates Gold examples for quality
- Supports repair mode with Judge critique feedback
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tatlam.graph.state import ScenarioStatus, SwarmState, WorkflowPhase
from tatlam.settings import get_settings

if TYPE_CHECKING:
    from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_clients() -> tuple[OpenAI | None, OpenAI | None, Any]:
    """Get local, cloud (OpenAI), and Anthropic clients."""
    from tatlam.core.llm_factory import (
        ConfigurationError,
        client_cloud,
        client_local,
        create_writer_client,
    )

    local_client = None
    cloud_client = None
    anthropic_client = None

    try:
        local_client = client_local()
    except (ConfigurationError, Exception) as e:
        logger.warning("Local LLM not available: %s", e)

    try:
        cloud_client = client_cloud()
    except (ConfigurationError, Exception) as e:
        logger.debug("Cloud client (OpenAI) not available: %s", e)

    try:
        anthropic_client = create_writer_client()
    except (ConfigurationError, Exception) as e:
        logger.debug("Anthropic client not available: %s", e)

    return local_client, cloud_client, anthropic_client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_llm(client: OpenAI, model: str, messages: list[dict], temperature: float = 0.7) -> str:
    """Call LLM with retry logic (OpenAI interface)."""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return (response.choices[0].message.content or "").strip()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _call_anthropic(client: Any, model: str, system: str, user_prompt: str) -> str:
    """Call Anthropic LLM (Claude) with retry logic."""
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[
            {"role": "user", "content": user_prompt},
        ],
    )
    return (response.content[0].text if response.content else "").strip()


def _get_doctrine_context(venue_type: str = "allenby") -> str:
    """
    Extract key doctrine elements for the Writer prompt.
    This ensures the Writer generates scenarios aligned with the doctrine.
    """
    from tatlam.core.doctrine import TRINITY_DOCTRINE

    doctrine = TRINITY_DOCTRINE

    if venue_type == "jaffa":
        # Surface doctrine
        venue = doctrine.get("venue_surface_jaffa", {})
        safety_rules = """
🚨 כללי ברזל ליפו (Surface):
- אין לגעת בחפץ חשוד! (50 מ')
- אופנוע 100 מ', רכב 200 מ'
- אין שערים = סריקה ויזואלית ותגובה רכובה
"""
        venue_desc = f"""
🏢 ציר יפו (רכבת קלה סביבה פתוחה):
- סוג: {venue.get('specs', {}).get('type', 'מערכת פתוחה')}
- כוח: אופנוענים + מאבטחי רכבות (אין עמדות קבועות)
- איום: {venue.get('threats_specific', ['ירי', 'אבנים'])[0]}
"""
    else:
        # Allenby doctrine
        safety = (
            doctrine.get("procedures", {}).get("suspicious_object", {}).get("safety_distances", {})
        )
        venue_data = doctrine.get("venue_allenby", {})

        safety_rules = f"""
🚨 טווחי בטיחות (אלנבי):
- חפץ חשוד עירוני: {safety.get('object_urban', '50 מטר')}
- רכב: {safety.get('car', '100 מטר')} | משאית: {safety.get('truck', '400 מטר')}
"""
        venue_desc = f"""
🏢 תחנת אלנבי:
- עומק: {venue_data.get('specs', {}).get('depth', '28 מטר')}
- מפלס -2: שטח סטרילי (כל אדם = אירוע)
"""

    # Legal framework (Shared)
    legal = doctrine.get("legal_framework", {})
    fire = legal.get("open_fire_regulations", {})

    return f"""
📚 תורת ההפעלה (DOCTRINE) - חובה!
{safety_rules}
⚖️ פתיחה באש (Ultima Ratio):
- עקרון: {fire.get('core_principle', 'אמצעי אחרון')}
- תנאים: סכנת חיים + אמצעי + כוונה
{venue_desc}
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

    bundle_id = state.bundle_id

    # Determine venue
    venue_type = "allenby"
    if (
        "jaffa" in str(state.category).lower()
        or "surface" in str(state.category).lower()
        or "tachanot-iliyot" in str(state.category).lower()
    ):
        venue_type = "jaffa"

    if "יפו" in str(state.category) or "עילי" in str(state.category):
        venue_type = "jaffa"

    # Get doctrine context
    doctrine_context = _get_doctrine_context(venue_type)

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
        state.iteration,
        state.category,
        state.target_count - len(state.approved_scenarios),
    )

    # Load gold examples if not already loaded
    if not state.gold_examples:
        state.gold_examples = _load_gold_examples(state.category)

    # Check for repair mode (scenarios needing rework)
    repair_critique = ""
    scenarios_to_repair = [
        c
        for c in state.candidates
        if c.status == ScenarioStatus.REJECTED and c.attempt_count <= state.max_retries_per_scenario
    ]
    if scenarios_to_repair:
        critiques = [c.critique for c in scenarios_to_repair if c.critique]
        repair_critique = "\n".join(critiques[:3])  # Top 3 critiques

    # Build prompt
    user_prompt = _build_generation_prompt(state, repair_critique)

    # Load system prompt
    from tatlam.core.prompts import get_prompt_manager, memory_addendum

    # Use prompt manager to get dynamic system prompt (injecting venue)
    pm = get_prompt_manager()

    # Infer venue type again for system prompt
    venue_type = "allenby"
    if (
        "jaffa" in str(state.category).lower()
        or "surface" in str(state.category).lower()
        or "tachanot-iliyot" in str(state.category).lower()
    ):
        venue_type = "jaffa"
    if "יפו" in str(state.category) or "עילי" in str(state.category):
        venue_type = "jaffa"

    # Build Rule Engine Context
    rule_context = {
        "category": (
            "suspicious_object" if "חפץ חשוד" in state.category else "general"
        ),  # Map Hebrew to rule keys
        "venue": venue_type,
        "location_type": "surface" if venue_type == "jaffa" else "underground",
        "risk_level": "high",  # default
    }

    # Simple mapping for common Hebrew categories to English rule keys
    if "חפץ חשוד" in state.category:
        rule_context["category"] = "suspicious_object"
    elif "רכב חשוד" in state.category:
        rule_context["category"] = "suspicious_vehicle"

    system_prompt = pm.get_trinity_prompt("writer", venue=venue_type, context=rule_context)
    memory_msg = memory_addendum()

    # Get LLM clients
    local_client, cloud_client, anthropic_client = _get_clients()
    settings = get_settings()

    # Determine primary model based on settings
    use_anthropic = settings.WRITER_MODEL_PROVIDER == "anthropic"
    use_cloud_first = settings.WRITER_MODEL_PROVIDER in ("anthropic", "openai", "google")

    draft_text = ""
    model_used = ""

    # Strategy 1: Anthropic (Claude) - Primary for Writer
    if use_anthropic and anthropic_client:
        try:
            model_used = settings.WRITER_MODEL_NAME
            logger.debug("Calling Cloud Writer (Anthropic): %s", model_used)

            draft_text = _call_anthropic(
                anthropic_client,
                model_used,
                system_prompt,  # Claude accepts system prompt separately
                f"{memory_msg}\n{user_prompt}",  # Append memory to user prompt
            )
        except Exception as e:
            logger.warning("Anthropic Writer failed: %s, falling back...", e)
            state.metrics.llm_errors += 1

    # Strategy 2: Cloud OpenAI/Generic (if Anthropic failed or not selected)
    if not draft_text and use_cloud_first and cloud_client and not use_anthropic:
        try:
            model_used = settings.WRITER_MODEL_NAME or settings.GEN_MODEL
            logger.debug("Calling Cloud Writer (OpenAI): %s", model_used)

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
            logger.warning("Cloud Writer failed: %s, falling back...", e)
            state.metrics.llm_errors += 1

    # Strategy 3: Local LLM (Primary or Fallback)
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

    # Strategy 4: Cloud Fallback (if Local was primary and failed)
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

    # Store the raw draft for the Clerk to process
    # We store it as a special "raw" candidate
    raw_candidate = state.add_candidate(
        {
            "_raw_text": draft_text,
            "_model": model_used,
            "_is_raw_draft": True,
            "category": state.category,
        }
    )
    raw_candidate.status = ScenarioStatus.DRAFT

    logger.info(
        "Writer completed: generated %d chars of draft text using %s", len(draft_text), model_used
    )

    return state


__all__ = ["writer_node"]

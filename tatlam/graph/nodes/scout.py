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
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tatlam.graph.state import SwarmState, WorkflowPhase
from tatlam.settings import get_settings

if TYPE_CHECKING:
    import anthropic
    from openai import OpenAI

logger = logging.getLogger(__name__)


def _get_local_client() -> OpenAI | None:
    """Get the local LLM client."""
    from tatlam.core.llm_factory import ConfigurationError, client_local

    try:
        return client_local()
    except (ConfigurationError, Exception) as e:
        logger.debug("Local LLM not available for Scout: %s", e)
        return None


def _get_anthropic_client() -> anthropic.Anthropic | None:
    """Get the Anthropic Claude client for Stage 2."""
    from tatlam.core.llm_factory import ConfigurationError, create_writer_client

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
def _call_local_llm(client: OpenAI, model: str, system: str, prompt: str) -> str:
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


def _get_learning_context(category: str) -> dict[str, Any]:
    """Get Hall of Fame examples and Graveyard patterns for context-aware curation."""
    try:
        from tatlam.infra.repo import get_learning_context
        return get_learning_context(category=category)
    except Exception as e:
        logger.debug("Failed to get learning context: %s", e)
        return {"positive_examples": [], "negative_patterns": []}


def _call_local_llm_batch(
    client: OpenAI,
    model: str,
    category: str,
    rounds: int,
    per_round: int,
    venue_type: str,
) -> list[str]:
    """
    Run multiple rounds of idea generation with variations.
    
    This maximizes the value of the FREE local LLM by generating
    diverse ideas across different time/context variations.
    """
    all_ideas: list[str] = []
    
    variations = [
        "התמקד באירועים בשעות הבוקר (06:00-12:00)",
        "התמקד באירועים בשעת שיא הערב (17:00-20:00)",
        "התמקד בתרחישי קצה נדירים ומפתיעים",
        "התמקד באירועים בלילה מאוחר או סוף שבוע",
        "התמקד באירועים בימי חג או אירועים המוניים",
    ]
    
    system_prompt = "אתה יוצר רעיונות יצירתי ומגוון. תפקידך להציע רעיונות מאתגרים ולא שגרתיים לתרחישי אבטחה."
    
    for i in range(rounds):
        try:
            prompt = _build_scout_prompt(category, per_round, venue_type)
            prompt += f"\n\n🎲 וריאציה נוספת: {variations[i % len(variations)]}"
            
            response = _call_local_llm(client, model, system_prompt, prompt)
            ideas = _parse_seeds(response)
            all_ideas.extend(ideas)
            
            logger.debug("Round %d: generated %d ideas", i + 1, len(ideas))
            
        except Exception as e:
            logger.warning("Round %d failed: %s", i + 1, e)
            continue
    
    # Remove duplicates while preserving order
    seen = set()
    unique_ideas = []
    for idea in all_ideas:
        normalized = idea.strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            unique_ideas.append(idea)
    
    logger.info("Generated %d unique ideas from %d rounds", len(unique_ideas), rounds)
    return unique_ideas


def _local_self_curate(
    client: OpenAI,
    model: str,
    ideas: list[str],
    learning_context: dict[str, Any],
    top_k: int,
    category: str,
) -> list[str]:
    """
    Use local LLM to filter ideas using learning context (FREE!).
    
    The local model receives:
    - Hall of Fame examples (what works)
    - Graveyard patterns (what to avoid)
    - All generated ideas
    
    Returns the top K best ideas.
    """
    if len(ideas) <= top_k:
        return ideas
    
    # Format learning context
    positive = learning_context.get("positive_examples", [])
    negative = learning_context.get("negative_patterns", [])
    
    positive_text = "\n".join([
        f"✅ {ex.get('title', ex) if isinstance(ex, dict) else ex}"
        for ex in positive[:3]
    ]) or "(אין דוגמאות עדיין - המערכת לומדת)"
    
    negative_text = "\n".join([
        f"❌ {pat}" for pat in negative[:5]
    ]) or "(אין דפוסים שליליים עדיין)"
    
    # Build ideas list
    ideas_text = "\n".join([f"{i+1}. {idea}" for i, idea in enumerate(ideas)])
    
    system = """אתה מסנן רעיונות מקצועי למערכת אימון ביטחוני.
יש לך גישה לדוגמאות מוצלחות (Hall of Fame) ולטעויות נפוצות (Graveyard).
בחר רק את הרעיונות הטובים ביותר:
- שדומים לדוגמאות המוצלחות
- שנמנעים מהטעויות הנפוצות
- שמתאימים לקטגוריה המבוקשת
- שמציבים דילמה אמיתית למאבטח"""

    prompt = f"""📂 קטגוריה: {category}

📊 דוגמאות מוצלחות (Hall of Fame):
{positive_text}

⚠️ טעויות נפוצות להימנע מהן (Graveyard):
{negative_text}

📋 רשימת {len(ideas)} רעיונות לסינון:
{ideas_text}

🎯 בחר את {top_k} הרעיונות הטובים ביותר.
החזר רק את המספרים של הרעיונות שבחרת, מופרדים בפסיקים.
לדוגמה: 3, 7, 12, 15, 22"""

    try:
        response = _call_local_llm(client, model, system, prompt)
        
        # Parse selected indices
        selected = []
        for num in re.findall(r'\d+', response):
            idx = int(num) - 1  # Convert to 0-indexed
            if 0 <= idx < len(ideas) and ideas[idx] not in selected:
                selected.append(ideas[idx])
            if len(selected) >= top_k:
                break
        
        if selected:
            logger.info("Self-curation selected %d ideas from %d", len(selected), len(ideas))
            return selected
        
    except Exception as e:
        logger.warning("Self-curation failed: %s", e)
    
    # Fallback: return first top_k
    return ideas[:top_k]


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


def _build_scout_prompt(category: str, count: int = 25, venue_type: str = "allenby") -> str:
    """Build the prompt for Stage 1 seed generation."""

    venue_desc = """📍 זירת הפעולה: תחנת רכבת קלה "אלנבי" בתל אביב
   - מפלס 0: רחוב, כניסה ראשית
   - מפלס -1: כרטוס, בידוק, מבואה
   - מפלס -2: קומה טכנית (סטרילי)
   - מפלס -3: רציפים"""

    if venue_type == "jaffa":
        venue_desc = """📍 זירת הפעולה: ציר יפו (רכבת קלה - עילי)
   - מפלס רחוב/רציף: חשוף לרחוב ללא גדרות
   - בתוך הרכבת: חלל סגור וצפוף
   - סביבה: אוכלוסייה מעורבת, צפיפות עירונית, אין שערים"""

    return f"""🎯 משימה: ייצור {count} רעיונות גולמיים ומגוונים לתרחישי אבטחה (זירה: {venue_type})

📂 קטגוריה: "{category}"

{venue_desc}

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
        line = re.sub(r"^[\d]+[.)]\s*", "", line)
        line = re.sub(r"^[-*•]\s*", "", line)
        line = line.strip()

        # Filter valid seeds (reasonable length)
        if 15 < len(line) < 250:
            seeds.append(line)

    return seeds


def scout_node(state: SwarmState) -> SwarmState:
    """
    Scout Node: Multi-Round Local Generation with Context-Aware Self-Curation.

    Maximizes FREE local LLM usage:
    1. Multi-round generation (3 rounds × 50 ideas = 150 ideas)
    2. Context-aware self-curation using Hall of Fame & Graveyard
    3. TOP 10 ideas passed to Claude for final refinement

    Args:
        state: Current SwarmState

    Returns:
        Updated SwarmState with scout_seeds populated
    """
    state.log_phase_change(WorkflowPhase.SCOUTING)

    settings = get_settings()
    
    # New multi-round configuration
    rounds = settings.SCOUT_ROUNDS  # Default: 3
    ideas_per_round = settings.SCOUT_IDEAS_PER_ROUND  # Default: 50
    top_k = settings.SCOUT_TOP_K_TO_CLAUDE  # Default: 10

    logger.info(
        "Scout starting multi-round pipeline for '%s' (%d rounds × %d ideas, top %d to Claude)",
        state.category,
        rounds,
        ideas_per_round,
        top_k,
    )

    # Determine venue type
    venue_type = "allenby"
    if (
        "jaffa" in str(state.category).lower()
        or "surface" in str(state.category).lower()
        or "tachanot-iliyot" in str(state.category).lower()
    ):
        venue_type = "jaffa"

    # Get clients
    local_client = _get_local_client()
    anthropic_client = _get_anthropic_client()

    curated_ideas: list[str] = []
    refined_ideas = ""

    # === STAGE 1: Multi-Round Local Generation (FREE!) ===
    if local_client:
        try:
            logger.info("Scout Stage 1: Multi-round generation with Local LLM")
            
            raw_ideas = _call_local_llm_batch(
                local_client,
                settings.LOCAL_MODEL_NAME,
                state.category,
                rounds,
                ideas_per_round,
                venue_type,
            )
            
            logger.info("Stage 1 complete: %d unique ideas generated", len(raw_ideas))
            
            # === STAGE 1.5: Context-Aware Self-Curation (FREE!) ===
            if len(raw_ideas) > top_k:
                logger.info("Scout Stage 1.5: Self-curation with learning context")
                
                learning_context = _get_learning_context(state.category)
                
                curated_ideas = _local_self_curate(
                    local_client,
                    settings.LOCAL_MODEL_NAME,
                    raw_ideas,
                    learning_context,
                    top_k,
                    state.category,
                )
                
                logger.info("Stage 1.5 complete: curated to %d ideas", len(curated_ideas))
            else:
                curated_ideas = raw_ideas

        except Exception as e:
            logger.warning("Scout Stage 1 failed: %s", e)
            state.metrics.llm_errors += 1
            curated_ideas = []

    # === STAGE 2: Claude Refinement ($$) ===
    if anthropic_client:
        try:
            if curated_ideas:
                # Refinement mode: polish the TOP curated ideas
                logger.info("Scout Stage 2: Refining %d curated ideas with Claude", len(curated_ideas))
                curated_text = "\n".join([f"• {idea}" for idea in curated_ideas])
                refined_ideas = _call_claude_refinement(
                    anthropic_client,
                    settings.WRITER_MODEL_NAME,
                    curated_text,
                    state.category,
                )
            else:
                # Fallback mode: generate from scratch (no local LLM)
                logger.info("Scout Stage 2: Fallback - generating with Claude Sonnet")
                fallback_prompt = _build_fallback_prompt(state.category, 20)

                response = anthropic_client.messages.create(
                    model=settings.WRITER_MODEL_NAME,
                    max_tokens=2048,
                    system="אתה מומחה ליצירת תרחישי אימון לאבטחת תחבורה ציבורית.",
                    messages=[{"role": "user", "content": fallback_prompt}],
                )
                # Safe text extraction
                if response.content and hasattr(response.content[0], 'text'):
                    refined_ideas = response.content[0].text.strip()
                else:
                    refined_ideas = ""

            logger.info("Scout Stage 2 complete: %d chars refined", len(refined_ideas))

        except Exception as e:
            logger.warning("Scout Stage 2 failed: %s", e)
            state.metrics.llm_errors += 1
            # Use curated ideas if refinement failed
            refined_ideas = "\n".join(curated_ideas)
    else:
        # No Claude available - use curated ideas directly
        refined_ideas = "\n".join(curated_ideas)

    # === Parse and store seeds ===
    if refined_ideas:
        seeds = _parse_seeds(refined_ideas)
        state.scout_seeds = seeds
        logger.info(
            "Scout pipeline complete: %d seeds (Local: %s, Claude: %s)",
            len(seeds),
            "✓" if local_client else "✗",
            "✓" if anthropic_client else "✗",
        )
    elif curated_ideas:
        # Fallback to curated ideas if parsing failed
        state.scout_seeds = curated_ideas
        logger.info("Scout complete: using %d curated ideas directly", len(curated_ideas))
    else:
        logger.warning("Scout failed: No ideas generated, continuing without seeds")

    return state


__all__ = ["scout_node"]

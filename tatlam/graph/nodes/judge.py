"""
tatlam/graph/nodes/judge.py - The Judge Node

The Judge evaluates scenarios for quality and doctrine compliance using:
1. Local doctrine validation (validate_scenario_doctrine)
2. LLM-based quality scoring with detailed critique

Key Features:
- Uses doctrine from doctrine.py for scoring logic
- Integrates with existing validator functions
- Returns structured critique for repair cycles
- Uses system_prompt for consistent evaluation
"""

from __future__ import annotations

import json
import logging
from typing import Any

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from tatlam.core.doctrine import TRINITY_DOCTRINE, get_system_prompt
from tatlam.core.validators import validate_scenario_doctrine
from tatlam.graph.state import ScenarioStatus, SwarmState, WorkflowPhase
from tatlam.settings import get_settings

logger = logging.getLogger(__name__)

# ==== Iron Dome Configuration ====
# These constants define the "Iron Dome" gatekeeper behavior:
# - No scenario passes to user unless score >= IRON_DOME_THRESHOLD
# - Auto-repair attempts before giving up

IRON_DOME_THRESHOLD = 70  # Minimum score to pass Iron Dome and reach user
MAX_AUTO_REPAIR_ATTEMPTS = 3  # Maximum auto-repair cycles before human escalation


def _build_judge_rubric() -> str:
    """
    Build the scoring rubric from doctrine.

    This ensures the Judge uses the same scoring logic defined in TRINITY_DOCTRINE.
    """
    scoring = TRINITY_DOCTRINE.get("scoring_logic", {})

    safety = scoring.get("safety", {})
    legality = scoring.get("legality", {})
    tactics = scoring.get("tactics", {})

    rubric = f"""
📊 קריטריוני ניקוד (0-100):

1. בטיחות (Safety) - משקל 30%
   ✅ עובר: {safety.get('pass', 'שמירה על טווחים')}
   ❌ נכשל: {safety.get('fail', 'נגיעה בחפץ חשוד = ציון 0')}

2. חוקיות (Legality) - משקל 30%
   ✅ עובר: {legality.get('pass', 'כוח סביר, ירי מוצדק')}
   ❌ נכשל: {legality.get('fail', 'ירי ללא סכנת חיים = ציון 0')}

3. טקטיקה (Tactics) - משקל 20%
   ✅ עובר: {tactics.get('pass', 'חתירה למגע, ניצול מחסות')}
   ❌ נכשל: {tactics.get('fail', 'בריחה בפח"ע')}

4. ניהול ונהלים (Management) - משקל 20%
   ✅ עובר: עבודה לפי פק"מ, דיווח תקין
   ❌ נכשל: חריגה מנהלים, דיווח לקוי

🚨 כשלים קריטיים (ציון 0 מיידי):
- נגיעה בחפץ חשוד
- פתיחה באש ללא סכנת חיים
- אפליה/פרופיילינג גזעי
- חריגה מסמכויות (מעצר ללא עילה)
"""
    return rubric


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _score_with_llm(scenario: dict[str, Any], rubric: str) -> tuple[float, str]:
    """
    Score a scenario using Claude Opus for deep, actionable critique.

    Returns:
        (score, critique)
    """
    from tatlam.core.llm_factory import ConfigurationError, create_writer_client

    settings = get_settings()

    try:
        anthropic_client = create_writer_client()
        if not anthropic_client:
            raise ConfigurationError("Anthropic client not available")
    except (ConfigurationError, Exception) as e:
        logger.warning("Anthropic client unavailable for Judge: %s", e)
        return 70.0, "לא ניתן לבצע הערכת LLM"

    # Infer context for Rule Engine
    category_str = str(scenario.get("category", ""))
    location_str = str(scenario.get("location", ""))

    venue = "allenby"
    if (
        "jaffa" in location_str.lower()
        or "surface" in location_str.lower()
        or "יפו" in location_str
        or "עילי" in location_str
    ):
        venue = "jaffa"

    rule_context = {
        "category": "suspicious_object" if "חפץ חשוד" in category_str else "general",
        "venue": venue,
        "location_type": "surface" if venue == "jaffa" else "underground",
        "risk_level": "high",
    }

    # Get Judge system prompt with active rules
    judge_prompt = get_system_prompt("judge", venue=venue, context=rule_context)

    # Build the evaluation prompt with actionable repair instructions
    scenario_json = json.dumps(scenario, ensure_ascii=False, indent=2)

    eval_prompt = f"""
{rubric}

📋 תרחיש להערכה:
{scenario_json}

הוראות למהלך הביקורת:
1. בצע את סריקת הבטיחות/חוקיות/איכות (Audit Logic) ותעד ב-audit_log.
2. דרג את התרחיש לפי הקריטריונים (0-100).
3. ציין נקודות חוזק וחולשה **ספציפיות** (לא כלליות).
4. אם יש כשל קריטי (בטיחות/חוקיות) - ציון 0.

🔧 הוראות לשיפור (CRITICAL - זה מה שהכותב יקבל):
אם הציון נמוך מ-80, עליך לספק הוראות תיקון מדויקות וברורות:
- מה בדיוק צריך לשנות? (ציין שדה ספציפי)
- למה זה בעייתי? (הפניה לדוקטרינה/חוק)
- איך לתקן? (הצע ניסוח חלופי או כיוון)

פורמט פלט (JSON בלבד):
{{
  "audit_log": "תמצית הסריקה: [בטיחות: X], [חוקיות: Y], [איכות: Z]",
  "score": int,
  "critique": "סיכום כללי של האיכות...",
  "strengths": ["חוזקה 1 (ספציפית)", "חוזקה 2"],
  "weaknesses": ["חולשה 1 (ספציפית)", "חולשה 2"],
  "repair_instructions": [
    {{"field": "שדה לתיקון", "issue": "הבעיה", "fix": "הצעה לתיקון"}},
    ...
  ]
}}
"""

    # Call Anthropic Claude Opus
    response = anthropic_client.messages.create(
        model=settings.JUDGE_MODEL_NAME,
        max_tokens=2048,
        system=judge_prompt,
        messages=[
            {"role": "user", "content": eval_prompt},
        ],
    )

    text = (response.content[0].text if response.content else "{}").strip()

    try:
        result = json.loads(text)
        score = float(result.get("score", 70))
        critique = result.get("critique", "")
        audit_log = result.get("audit_log", "")

        # Add strengths/weaknesses and audit log to critique
        strengths = result.get("strengths", [])
        weaknesses = result.get("weaknesses", [])
        repair_instructions = result.get("repair_instructions", [])

        if audit_log:
            critique = f"🔍 לוג בדיקה:\n{audit_log}\n\n📝 סיכום:\n{critique}"

        if strengths:
            critique += f"\n\n✅ חוזקות: {', '.join(strengths)}"
        if weaknesses:
            critique += f"\n\n❌ חולשות: {', '.join(weaknesses)}"

        # Add actionable repair instructions for the Writer
        if repair_instructions:
            repair_text = "\n\n🔧 הוראות תיקון לכותב:\n"
            for instr in repair_instructions:
                field = instr.get("field", "כללי")
                issue = instr.get("issue", "")
                fix = instr.get("fix", "")
                repair_text += f"• [{field}]: {issue} → {fix}\n"
            critique += repair_text

        return score, critique.strip()

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse Judge response: %s", e)
        return 60.0, "שגיאה בפרסור תגובת השופט"


def judge_node(state: SwarmState) -> SwarmState:
    """
    Judge Node: Evaluate scenarios for quality and doctrine compliance.

    This node:
    1. Runs local doctrine validation first (fast, no API)
    2. Calls LLM for detailed scoring and critique
    3. Combines scores and marks scenarios as APPROVED or REJECTED
    4. Stores critique for repair cycles

    Args:
        state: Current SwarmState

    Returns:
        Updated SwarmState with judged candidates
    """
    state.log_phase_change(WorkflowPhase.JUDGING)

    # Find unique candidates to judge
    candidates_to_judge = [c for c in state.candidates if c.status == ScenarioStatus.UNIQUE]

    if not candidates_to_judge:
        logger.info("Judge: No unique candidates to evaluate")
        return state

    logger.info("Judge evaluating %d candidates", len(candidates_to_judge))

    # Build rubric from doctrine
    rubric = _build_judge_rubric()

    scores: list[float] = []

    for candidate in candidates_to_judge:
        # Step 1: Local doctrine validation (fast)
        doctrine_result = validate_scenario_doctrine(candidate.data)
        doctrine_score = doctrine_result.doctrine_score

        # If doctrine validation fails critically, reject immediately
        if not doctrine_result.is_valid:
            candidate.status = ScenarioStatus.REJECTED
            candidate.add_feedback(f"כשל דוקטרינה: {', '.join(doctrine_result.errors)}", 0.0)
            state.metrics.total_rejected += 1
            logger.debug("Rejected by doctrine: %s", candidate.title)
            continue

        # Step 2: LLM scoring for quality
        try:
            llm_score, llm_critique = _score_with_llm(candidate.data, rubric)
        except Exception as e:
            logger.warning("LLM scoring failed: %s, using doctrine score", e, exc_info=True)
            state.metrics.llm_errors += 1
            llm_score = doctrine_score
            llm_critique = (
                f"שימוש בציון דוקטרינה בלבד. אזהרות: {', '.join(doctrine_result.warnings)}"
            )

        # Combine scores (weighted average)
        # Doctrine: 40%, LLM: 60%
        final_score = (doctrine_score * 0.4) + (llm_score * 0.6)

        # Build full critique
        full_critique = llm_critique
        if doctrine_result.warnings:
            full_critique += f"\n\n⚠️ אזהרות דוקטרינה: {', '.join(doctrine_result.warnings)}"

        # Record feedback
        candidate.add_feedback(full_critique, final_score)
        scores.append(final_score)

        # Decision: approve or reject (Iron Dome Gatekeeper)
        # Using IRON_DOME_THRESHOLD for consistent gatekeeper behavior
        if final_score >= IRON_DOME_THRESHOLD:
            candidate.status = ScenarioStatus.JUDGE_APPROVED
            state.metrics.total_approved += 1
            logger.info("Judge Approved (Iron Dome): %s (score=%.1f >= %d)", 
                       candidate.title, final_score, IRON_DOME_THRESHOLD)
        else:
            candidate.status = ScenarioStatus.REJECTED
            state.metrics.total_rejected += 1
            logger.debug(
                "Rejected (Iron Dome): %s (score=%.1f < %d)",
                candidate.title,
                final_score,
                IRON_DOME_THRESHOLD,
            )

    # Update score statistics
    if scores:
        state.metrics.update_score_stats(scores)

    logger.info(
        "Judge completed: %d approved, %d rejected (avg_score=%.1f)",
        state.metrics.total_approved,
        state.metrics.total_rejected,
        state.metrics.average_score,
    )

    return state


__all__ = ["judge_node", "IRON_DOME_THRESHOLD", "MAX_AUTO_REPAIR_ATTEMPTS"]

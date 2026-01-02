"""
Test suite to verify LLM alignment with Doctrine deterministic rules.

This test validates that the LLM's threat assessments and decisions match
the Python-defined logic in tatlam/core/doctrine.py. The goal is zero hallucinations
by ensuring the LLM follows the documented rules precisely.

If tests fail, it indicates the LLM needs better instruction via system prompts.
"""

from __future__ import annotations

import pytest

from tatlam.core.brain import TrinityBrain


# ==== Deterministic Rule Implementations ====


def python_threat_level(scenario_description: str) -> str:
    """
    Deterministic Python implementation of threat level logic.

    Based on TRINITY_DOCTRINE threat_matrix.

    Args:
        scenario_description: Hebrew scenario description

    Returns:
        Threat level: "נמוכה" | "בינונית" | "גבוהה" | "גבוהה מאוד"
    """
    desc_lower = scenario_description.lower()

    # High threat: Weapons found
    weapon_indicators = [
        "נשק",
        "אקדח",
        "סכין",
        "גרזן",
        "מברג",
        "חגורת נפץ",
        "רימון",
        "מטען",
        "חומר נפץ",
        "פצצה",
        'חנ"מ',
    ]
    if any(indicator in desc_lower for indicator in weapon_indicators):
        return "גבוהה מאוד"

    # High threat: Suspicious object with explosive indicators
    explosive_indicators = ["חפץ חשוד", "כבודה עזובה", "תיק נטוש"]
    behavioral_indicators = ["תסמונת הצייד", "קיבעון", "סריקה חשודה"]

    if any(indicator in desc_lower for indicator in explosive_indicators):
        return "גבוהה"

    if any(indicator in desc_lower for indicator in behavioral_indicators):
        return "בינונית"

    # Low threat: Routine checks
    return "נמוכה"


def python_category(scenario_description: str) -> str:
    """
    Deterministic Python implementation of category classification.

    Based on TRINITY_DOCTRINE threat_matrix.

    Args:
        scenario_description: Hebrew scenario description

    Returns:
        Category string in Hebrew
    """
    desc_lower = scenario_description.lower()

    # Vehicle threats
    vehicle_keywords = ["רכב", "מכונית", "משאית", "אופנוע", "ואן"]
    if any(kw in desc_lower for kw in vehicle_keywords):
        if any(kw in desc_lower for kw in ["דריסה", "רכב חשוד", "שקיעת מתלים"]):
            return "איום רכב / דריסה / מטען"

    # Drone/aerial
    drone_keywords = ["רחפן", 'מזל"ט', 'כטב"מ']
    if any(kw in desc_lower for kw in drone_keywords):
        return "איום אווירי / רחפנים"

    # Active shooter / cold weapon
    weapon_keywords = ["אקדח", "סכין", "גרזן", "ירי", "תוקף"]
    if any(kw in desc_lower for kw in weapon_keywords):
        return 'פח"ע / תוקף בנשק קר'

    # Suspicious object / IED
    object_keywords = ["חפץ חשוד", "כבודה", "תיק נטוש", "מטען"]
    if any(kw in desc_lower for kw in object_keywords):
        return "חפץ חשוד ומטען"

    # Behavioral indicators
    behavior_keywords = ["תסמונת הצייד", "התנהגות חשודה"]
    if any(kw in desc_lower for kw in behavior_keywords):
        return "התנהגות חשודה"

    return "לא מסווג"


def python_decision(scenario_description: str) -> dict[str, str]:
    """
    Combined deterministic decision logic.

    Returns:
        Dict with keys: threat_level, category
    """
    return {
        "threat_level": python_threat_level(scenario_description),
        "category": python_category(scenario_description),
    }


# ==== Test Cases ====

# Test scenarios with deterministic outcomes
TEST_SCENARIOS = [
    {
        "description": "מאבטח מזהה אדם עם חגורת נפץ בתחנת הרכבת",
        "expected_threat": "גבוהה מאוד",
        "expected_category": "חפץ חשוד ומטען",
    },
    {
        "description": "נמצא נשק חם (אקדח) במהלך בדיקת תיק",
        "expected_threat": "גבוהה מאוד",
        "expected_category": 'פח"ע / תוקף בנשק קר',
    },
    {
        "description": "כבודה עזובה ליד כניסת התחנה, ללא בעלים",
        "expected_threat": "גבוהה",
        "expected_category": "חפץ חשוד ומטען",
    },
    {
        "description": "אדם מתנהג בצורה חשודה, מסתכל על המאבטח בקיבעון",
        "expected_threat": "בינונית",
        "expected_category": "התנהגות חשודה",
    },
    {
        "description": "בדיקה שגרתית של כרטיס נוסע בכניסה לתחנה",
        "expected_threat": "נמוכה",
        "expected_category": "לא מסווג",
    },
]


@pytest.mark.slow
@pytest.mark.slow
class TestDoctrine_AlignmentAlignment:
    """
    Test alignment between LLM decisions and Doctrine deterministic rules.
    """

    @pytest.fixture(autouse=True)
    def check_llm_flag(self, request):
        if not request.config.getoption("--run-llm", default=False):
            pytest.skip("LLM tests require --run-llm flag and API access")

    @pytest.fixture(scope="class")
    def brain(self):
        """Initialize TrinityBrain for testing."""
        brain = TrinityBrain()
        if not brain.has_simulator():
            pytest.skip("Simulator (Local LLM) not available")
        return brain

    def test_threat_level_weapon_found(self, brain):
        """Test: Weapon found should result in 'גבוהה מאוד' threat level."""
        scenario = TEST_SCENARIOS[0]  # חגורת נפץ

        # Python deterministic decision
        python_result = python_decision(scenario["description"])
        assert python_result["threat_level"] == scenario["expected_threat"]

        # LLM decision
        prompt = f"נתח את התרחיש הבא וחזר תשובה ב-JSON:\n{scenario['description']}"
        llm_result = brain.think_structured(prompt, temperature=0.1)

        # Validate alignment
        assert llm_result["threat_level"] == python_result["threat_level"], (
            f"LLM threat level mismatch!\n"
            f"Expected (Python): {python_result['threat_level']}\n"
            f"Got (LLM): {llm_result['threat_level']}\n"
            f"Scenario: {scenario['description']}"
        )

    def test_threat_level_gun_found(self, brain):
        """Test: Gun found should result in 'גבוהה מאוד' threat level."""
        scenario = TEST_SCENARIOS[1]  # נשק חם

        python_result = python_decision(scenario["description"])
        assert python_result["threat_level"] == scenario["expected_threat"]

        prompt = f"נתח את התרחיש הבא וחזר תשובה ב-JSON:\n{scenario['description']}"
        llm_result = brain.think_structured(prompt, temperature=0.1)

        assert llm_result["threat_level"] == python_result["threat_level"], (
            f"LLM threat level mismatch for gun scenario!\n"
            f"Expected: {python_result['threat_level']}\n"
            f"Got: {llm_result['threat_level']}"
        )

    def test_threat_level_suspicious_object(self, brain):
        """Test: Suspicious object should result in 'גבוהה' threat level."""
        scenario = TEST_SCENARIOS[2]  # כבודה עזובה

        python_result = python_decision(scenario["description"])
        assert python_result["threat_level"] == scenario["expected_threat"]

        prompt = f"נתח את התרחיש הבא וחזר תשובה ב-JSON:\n{scenario['description']}"
        llm_result = brain.think_structured(prompt, temperature=0.1)

        assert llm_result["threat_level"] == python_result["threat_level"], (
            f"LLM threat level mismatch for suspicious object!\n"
            f"Expected: {python_result['threat_level']}\n"
            f"Got: {llm_result['threat_level']}"
        )

    def test_threat_level_behavioral(self, brain):
        """Test: Behavioral indicators should result in 'בינונית' threat level."""
        scenario = TEST_SCENARIOS[3]  # התנהגות חשודה

        python_result = python_decision(scenario["description"])
        assert python_result["threat_level"] == scenario["expected_threat"]

        prompt = f"נתח את התרחיש הבא וחזר תשובה ב-JSON:\n{scenario['description']}"
        llm_result = brain.think_structured(prompt, temperature=0.1)

        assert llm_result["threat_level"] == python_result["threat_level"], (
            f"LLM threat level mismatch for behavioral scenario!\n"
            f"Expected: {python_result['threat_level']}\n"
            f"Got: {llm_result['threat_level']}"
        )

    def test_threat_level_routine(self, brain):
        """Test: Routine check should result in 'נמוכה' threat level."""
        scenario = TEST_SCENARIOS[4]  # בדיקה שגרתית

        python_result = python_decision(scenario["description"])
        assert python_result["threat_level"] == scenario["expected_threat"]

        prompt = f"נתח את התרחיש הבא וחזר תשובה ב-JSON:\n{scenario['description']}"
        llm_result = brain.think_structured(prompt, temperature=0.1)

        assert llm_result["threat_level"] == python_result["threat_level"], (
            f"LLM threat level mismatch for routine scenario!\n"
            f"Expected: {python_result['threat_level']}\n"
            f"Got: {llm_result['threat_level']}"
        )

    def test_category_alignment_all_scenarios(self, brain):
        """Test: LLM category should match Python logic for all test scenarios."""
        failures = []

        for i, scenario in enumerate(TEST_SCENARIOS):
            python_result = python_decision(scenario["description"])

            prompt = f"נתח את התרחיש הבא וחזר תשובה ב-JSON:\n{scenario['description']}"
            try:
                llm_result = brain.think_structured(prompt, temperature=0.1)

                # Allow fuzzy matching for categories (LLM might use synonyms)
                if python_result["category"] != llm_result["category"]:
                    failures.append(
                        {
                            "scenario_id": i,
                            "description": scenario["description"],
                            "expected_category": python_result["category"],
                            "llm_category": llm_result["category"],
                        }
                    )
            except Exception as e:
                failures.append(
                    {
                        "scenario_id": i,
                        "description": scenario["description"],
                        "error": str(e),
                    }
                )

        if failures:
            failure_msg = "\n\n".join(
                [
                    f"Scenario {f['scenario_id']}: {f['description']}\n"
                    f"  Expected: {f.get('expected_category', 'N/A')}\n"
                    f"  Got: {f.get('llm_category', f.get('error', 'Unknown'))}"
                    for f in failures
                ]
            )
            pytest.fail(f"Category mismatches found:\n\n{failure_msg}")


# ==== Operational Directives Generation ====


def generate_operational_directives() -> str:
    """
    Generate Hebrew operational directives for system_prompt_he.txt.

    This function extracts the deterministic rules from doctrine.py and
    formats them as natural Hebrew instructions for the LLM.

    Returns:
        Formatted Hebrew text to be added to system_prompt_he.txt
    """
    directives = """
## הנחיות מבצעיות (Operational Directives)

### רמות איום (Threat Levels)
בעת הערכת תרחיש, יש לסווג את רמת האיום בהתאם לקריטריונים הבאים:

**גבוהה מאוד (Critical):**
- זיהוי נשק (אקדח, סכין, גרזן, מברג)
- גילוי חומר נפץ (חגורת נפץ, רימון, מטען, חנ"מ)
- איום ממשי וישיר על חיים

**גבוהה (High):**
- חפץ חשוד (כבודה עזובה, תיק נטוש)
- סימני חפץ עם פוטנציאל לחומר נפץ
- רכב חשוד עם סימנים (שקיעת מתלים, ריח חריג)

**בינונית (Medium):**
- התנהגות חשודה (תסמונת הצייד, קיבעון על מאבטח)
- סריקה חשודה של השטח
- אינדיקטורים התנהגותיים ללא גילוי פיזי

**נמוכה (Low):**
- בדיקות שגרתיות
- פעולות מניעה רגילות
- ללא סימני חשד מזוהים

### קטגוריות אבטחה (Security Categories)
יש לסווג כל תרחיש לאחת הקטגוריות הבאות:

- **חפץ חשוד ומטען**: כבודה עזובה, תיק נטוש, מטען חשוד
- **פח"ע / תוקף בנשק קר**: אקדח, סכין, גרזן, תקיפה אקטיבית
- **איום רכב / דריסה / מטען**: רכב חשוד, דריסה, מטען רכב
- **איום אווירי / רחפנים**: רחפנים, מזל"טים, כטב"מים
- **התנהגות חשודה**: אינדיקטורים התנהגותיים ללא גילוי פיזי
- **לא מסווג**: תרחישים שאינם נכנסים לקטגוריות לעיל

### לוגיקת שיפוט (Scoring Logic)
**בטיחות (Safety):**
- ✅ עבור: שמירה על טווחי בטיחות, אי-מגע בחפץ חשוד
- ❌ נכשל: נגיעה בחפץ חשוד (ציון 0 מיידי), כניסה לטווח סכנה

**חוקיות (Legality):**
- ✅ עבור: שימוש בכוח סביר, ירי מוצדק, עיכוב חוקי
- ❌ נכשל: ירי ללא סכנת חיים, אפליה, עיכוב מעל 3 שעות

**טקטיקה (Tactics):**
- ✅ עבור: חתירה למגע בפח"ע, בידוד בחפץ חשוד
- ❌ נכשל: בריחה בפח"ע, הסתערות על חפץ חשוד

**חשוב:** יש להחיל כללים אלו באופן דטרמיניסטי. כל סטייה מהכללים תיחשב כשגיאה.
"""
    return directives.strip()


if __name__ == "__main__":
    # When run directly, generate the operational directives
    print("Generating Operational Directives for system_prompt_he.txt...")
    print("=" * 70)
    print()
    directives = generate_operational_directives()
    print(directives)
    print()
    print("=" * 70)
    print("\n✅ Copy the text above and add it to system_prompt_he.txt")
    print("   under a new section: 'הנחיות מבצעיות (Operational Directives)'")

"""
Trinity Security Doctrine (תורת ההפעלה - תתל"מ Trinity)
Based on Deep Security Research 2025.
Source of Truth for: Writer (Claude), Judge (Gemini), Simulator (Llama/Qwen).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_prompt() -> str:
    """Load the system prompt from system_prompt_he.txt.

    Returns
    -------
    str
        The Hebrew system prompt content.

    Raises
    ------
    FileNotFoundError
        If the system_prompt_he.txt file is not found.
    """
    # Try multiple locations for the prompt file
    possible_paths = [
        Path("system_prompt_he.txt"),
        Path(__file__).resolve().parent.parent.parent / "system_prompt_he.txt",
    ]

    for path in possible_paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

    raise FileNotFoundError(
        "system_prompt_he.txt not found in project root or relative paths"
    )


TRINITY_DOCTRINE = {
    # פרק 1: ניתוח איום הייחוס 2025
    "threat_matrix": {
        "foot_assault": {
            "suicide_bomber": {
                "belt": {
                    "payload": "3-5 ק\"ג חנ\"מ + רסס (ברגים/מסמרים)",
                    "indicators": "נפח חריג באזור המותניים/טורסו, אי-פרופורציה בגוף"
                },
                "backpack": {
                    "payload": "6-10 ק\"ג חנ\"מ",
                    "indicators": "הליכה כבדה, מסורבלת, חתימת תנועה (Kinetic Signature) איטית"
                },
                "tiny_ied": {
                    "payload": "0.5 ק\"ג או גודל רימון 26/פחית",
                    "hiding_spot": "מוסתר בכבודה/תיק צד",
                    "detection": "מחייב שיקוף או חיפוש ידני, קשה לזיהוי ויזואלי"
                }
            },
            "active_shooter_cold_weapon": {
                "weapons": ["אקדח (אחוד/מפורק)", "סכין", "גרזן", "מברג"],
                "range": "טווח קצר (Point-blank)",
                "behavioral_indicators": [
                    "תסמונת הצייד (Dread)",
                    "סריקה מהירה של השטח",
                    "קיבעון (Fixation) על המאבטח",
                    "הסתרת יד דומיננטית"
                ]
            }
        },
        "vehicle_threats": {
            "vbied_types": {
                "motorcycle": {"capacity": "50 ק\"ג", "risk": "עקיפת מחסומים סטטיים"},
                "car": {"capacity": "300 ק\"ג"},
                "van": {"capacity": "500 ק\"ג"},
                "truck": {"capacity": "1,000 ק\"ג (1 טון)", "risk": "מוטות מבנים/גשרים"}
            },
            "indicators": [
                "שקיעת מתלים (Suspension sag)",
                "לוחיות רישוי אינן תואמות",
                "ריח חריג (דלק/חומצה)",
                "רכב חונה בציר חירום/גשר"
            ],
            "ramming": {
                "mass": "עד 10 טון",
                "speed": "60 קמ\"ש",
                "target": "הולכי רגל/עמודי נגיפה",
                "vector": "סטייה חדה מתוואי כביש"
            }
        },
        "aerial_threats": {
            "drones": {
                "types": ["רחפן מסחרי (COTS)", "רחפן בבנייה עצמית (250 גרם+)"],
                "tactics": ["הטלת חימוש (רימון)", "רחפן מתאבד", "נחילים (עד 5 במקביל)"],
                "envelope": "גובה עד 300 רגל (90 מ'), רדיוס 100 מ'"
            },
            "high_angle_fire": "ירי נק\"ל/נ\"ט מגגות שולטים או ירי תלול מסלול (רקטות)"
        },
        "infrastructure_hazmat": {
            "hazmat_leech": "מטען 'עלוקה' (250 גרם) מוצמד למיכל חומר מסוכן",
            "sabotage": ["חיתוך סיבים/חשמל", "שיבוש שו\"ב", "הנחת מכשול למסילה (שימוט)"]
        }
    },

    # פרק 2: זירת הפעולה - תחנת אלנבי
    "venue_allenby": {
        "specs": {
            "depth": "28 מטר מתחת לקרקע",
            "type": "מערכת פתוחה עם סינון סלקטיבי"
        },
        "levels": {
            "surface": {
                "name": "מפלס הרחוב",
                "features": ["3 כניסות (הרכבת, מקווה ישראל, אלנבי)", "פיר מעלית אחורי"],
                "defenses": "עמודי נגיפה הידראוליים (HVM)"
            },
            "minus_1": {
                "name": "קומת כרטוס (Concourse)",
                "assets": ["חדר בקרת תחנה (SMR)", "חדר שנאים", "שערי גבייה"],
                "risk": "השתלטות על SMR = עיוורון מצלמות ושליטה בדלתות"
            },
            "minus_2": {
                "name": "קומה טכנית",
                "status": "שטח סטרילי (אין כניסת נוסעים)",
                "alert_rule": "כל אדם בקומה זו = אירוע פריצה/פח\"ע מיידי"
            },
            "minus_3": {
                "name": "קומת רציפים",
                "vulnerabilities": ["מעבר שירות למסילה", "צפיפות קהל (Kill Zone)"],
                "assets": "חדרי תקשורת"
            }
        },
        "force_structure": "מינימום 2 מאבטחים (1 בכרטוס, 1 ברציף). הסתמכות על הפתעה ותווך.",
        "dead_zones": [
            "מדרגות חירום (הטמנת מטען)",
            "מסדרונות תפעוליים",
            "שירותים (הרכבת מטען לאחר בידוק)"
        ]
    },

    # פרק 3: סמכויות ומשפט (האלגוריתם של השופט)
    "legal_framework": {
        "search_authority": {
            "location": "רק בכניסה למתקן או מקום מוגדר בחוק",
            "scope": "גוף האדם (שטחי), בגדים, כלים, כלי תחבורה",
            "trigger": "שמירה על בטחון הציבור בלבד (לא אכיפה אזרחית)",
            "refusal_policy": "סירוב לחיפוש = מניעת כניסה בלבד (לא עילה למעצר)",
            "forced_search": {
                "condition": "חשד סביר בלבד (Reasonable Suspicion)",
                "definition": "למשל: סירוב + בליטה חשודה בבגד",
                "action": "שימוש בכוח סביר"
            }
        },
        "detainment_authority": {
            "conditions": ["חשד לנשיאת נשק שלא כדין", "חשד לשימוש בנשק", "אלימות/סכנה לציבור"],
            "duration": "עד הגעת שוטר (זמן סביר). רף עליון סטטוטורי: 3 שעות",
            "force": "כוח סביר למימוש העיכוב במקרה התנגדות"
        },
        "identification": {
            "rule": "מותר לדרוש תעודה בכניסה",
            "profiling_ban": "איסור מוחלט על דרישה על בסיס גזע, דת, מוצא, דעה פוליטית. חריגה = ציון 0 בשיפוט."
        },
        "open_fire_regulations": {
            "core_principle": "אמצעי אחרון (Ultima Ratio)",
            "conditions": [
                "סכנת חיים ממשית ומיידית (Life Threat)",
                "זיהוי אמצעי (Means) + כוונה (Intent)"
            ],
            "prohibitions": [
                "אסור לירות להגנה על רכוש",
                "אסור לירות להגנה על סדר ציבורי",
                "אסור לירות בגב של בורח שאינו מסכן חיים"
            ],
            "exceptions": "מיידי אבנים/בקת\"ב - רק בטווח מסכן חיים מיידי"
        }
    },

    # פרק 4: פרוטוקולי פעולה (SOPs)
    "procedures": {
        "suspicious_object": {
            "classification": {
                "abandoned": "מקום טבעי, חפץ תמים, ניתן לאיתור בעלים",
                "suspicious": "מוסתר, כבד, חוטים/אורות, ריח שקדים/דלק, מיקום רגיש (עמוד תומך)"
            },
            "actions_donts": ["אסור לגעת!", "אסור להזיז/לפתוח", "אסור להשתמש בקשר/סלולר ליד החפץ"],
            "actions_dos": ["בידוד זירה", "חסימה", "דיווח", "סריקה למטען משני", "טיפול ע\"י חבלן בלבד"],
            "safety_distances": {
                "object_urban": "50 מטר (מאחורי מחסה)",
                "object_open": "100 מטר",
                "car": "100 מטר ומעלה",
                "truck": "עד 400 מטר"
            }
        },
        "hostile_event_peh_hey_ay": {
            "flow": [
                "1. זיהוי (אימות אמצעי וכוונה)",
                "2. דיווח (קוד מצוקה + מיקום)",
                "3. חתירה למגע (צמצום טווח, ניצול מחסות)",
                "4. נטרול (ירי סלקטיבי, זהירות על קהל)",
                "5. סיום איום (הרחקה מנשק, כבילה)",
                "6. טיפול רפואי (רק לאחר זיכוי זירה)"
            ]
        },
        "public_disturbance": {
            "level_a_quiet": "מחאה שקטה/שלטים -> לא להתערב",
            "level_b_soft": "צעקות/הפרעה לתנועה -> אזהרה, מניעת כניסה",
            "level_c_violent": "ונדליזם/תקיפה -> כוח סביר, הרחקה, משטרה",
            "red_line": "אסור להשתמש בנשק חם לפיזור הפגנה"
        },
        "emergency_routine": {
            "routine": "סריקות ביטחון כל שעתיים (כולל שטחים מתים)",
            "missile_alert": "פתיחת שערים, הכוונה לקומות -2/-3 (מקלט)",
            "fire": "נוהל אש, פינוי נגד כיוון העשן, חסימת כניסות"
        }
    },

    # פרק 5: לוגיקת שיפוט וניקוד
    "scoring_logic": {
        "safety": {
            "pass": "שמירה על טווחי בטיחות, אי-מגע בחפץ",
            "fail": "נגיעה בחפץ חשוד (ציון 0 מיידי), כניסה לטווח סכנה"
        },
        "legality": {
            "pass": "כוח סביר, ירי מוצדק, עיכוב חוקי",
            "fail": "ירי ללא סכנת חיים, אפליה, עיכוב מעל 3 שעות"
        },
        "tactics": {
            "pass": "חתירה למגע בפח\"ע, בידוד בחפץ חשוד",
            "fail": "בריחה בפח\"ע, הסתערות על חפץ חשוד"
        }
    }
}

def get_system_prompt(role: str) -> str:
    """
    בונה את הנחיית המערכת (System Prompt) באופן דינמי.
    
    כל התפקידים מקבלים את system_prompt_he.txt המלא (עם המועצה והדוקטרינה)
    בתוספת הנחיות ספציפיות לתפקיד.
    
    Args:
        role: אחד מ-"writer", "judge", "simulator"
        
    Returns:
        הפרומפט המלא לתפקיד המבוקש
    """
    # Critical language guardrails to prevent hallucinations
    language_guard = (
        "\n\n*** הנחיות קריטיות לשפה (CRITICAL LANGUAGE INSTRUCTIONS) ***\n"
        "1. עליך להגיב אך ורק בעברית (Hebrew ONLY).\n"
        "2. אין להשתמש בסינית, ערבית, גרמנית או כל שפה אחרת.\n"
        "3. גם אם יש מונחים באנגלית בהנחיות, התשובה שלך חייבת להיות בעברית מלאה.\n"
        "4. שמור על דמות אמינה ומקצועית."
    )

    # Load full system prompt for ALL roles
    try:
        full_prompt = load_prompt()
    except FileNotFoundError:
        # Fallback if file not found
        full_prompt = (
            "אתה חלק ממערכת 'תתל\"מ Trinity' לאימון ביטחוני.\n"
            "עליך לפעול אך ורק לפי 'תורת ההפעלה' (Doctrine) המוגדרת להלן.\n"
            "כל חריגה מהנהלים, המשקלים או הסמכויות תחשב לכישלון.\n\n"
        )

    # Role-specific addendums
    role_addendum = {
        "writer": """

*** תפקיד: האדריכל (The Architect) ***

אתה המוח המתכנן מאחורי סימולציית "Trinity".
המשימה שלך: יצירת תרחישי קצה שבוחנים את היכולת המנטלית והמבצעית של המאבטח.

🧠 פרוטוקול חשיבה (Chain of Thought):
לפני כתיבת התרחיש, עליך לבצע סימולציה מנטלית:
1. ניתוח וקטור האיום: בחר את הדפוס המבצעי המדויק מהדוקטרינה.
2. כינוס המועצה (The Hexagon): מה אומר היועמ"ש? מה אומר קצין הבטיחות?
3. תכנון הדילמה: איפה נקודת הכשל האפשרית של המאבטח?
4. כתיבה: רק אז, כתוב את התרחיש המלא.

📋 שדות חובה (פורמט JSON-פנימי בתוך Markdown):
1. כותרת - ייחודית ותיאורית (3-8 מילים)
2. קטגוריה - אחת מ: חפץ חשוד, אדם חשוד, רכב חשוד, איום אווירי, הפרת סדר, חירום
3. רמת איום - LOW / MEDIUM / HIGH / CRITICAL
4. מיקום - מפלס (-3 עד 0) + אזור (רציף/כרטוס/מבואה/חדר טכני)
5. רקע/סיפור מקרה - 50-200 מילים - חייב להיות *שונה* מדוגמאות קודמות
6. שלבי תגובה - 4-8 שלבים מפורטים לפי הנהלים
7. נקודות הכרעה - 2-4 דילמות עם הפניות חוקיות
8. מצב סיום מוצלח
9. מצב כשל
10. לקחים - 2-4 נקודות

🚨 כללי ברזל (הפרה = כישלון):
- אין לגעת בחפץ חשוד! טווח מינימלי: 50 מ'
- טווחי רכב: אופנוע 100 מ', רכב 200 מ', משאית 400 מ'
- פתיחה באש: רק לפי Ultima Ratio (אמצעי + כוונה + סכנת חיים מיידית)
- כל פעולה לפי חוק הסמכויות 2005

השתמש בנתונים מדויקים מהדוקטרינה: משקלי מטענים, גבהי רחפנים, שמות קומות.
""",
        "judge": """

*** תפקיד: השופט העליון (The Adjudicator) ***

אתה הסמכות העליונה לבקרת איכות ובטיחות. אין לך רגשות, רק נהלים.
אתה מייצג את מבקר המדינה, היועמ"ש וקצין הבטיחות הראשי.

🔍 אלגוריתם הבדיקה (Audit Logic):
עליך לבצע סריקה (Scan) לפי הסדר הבא:
1. סריקת בטיחות (Safety Scan): האם יש הפרת טווח? נגיעה בחפץ? (אם כן -> ציון 0).
2. סריקת חוקיות (Legal Scan): האם השימוש בכוח תואם את האיום? האם יש פרופיילינג?
3. סריקת איכות (Quality Scan): האם הסיפור אמין? האם השלבים הגיוניים?

📊 קריטריוני ניקוד (0-100):

1. בטיחות (Safety) - משקל 30%
   - נגיעה בחפץ חשוד = ציון 0 מיידי
   - אי-שמירה על טווחים = הפחתה חמורה
   
2. חוקיות (Legality) - משקל 30%
   - ירי לא מוצדק = ציון 0 מיידי
   - חיפוש ללא עילה = הפחתה חמורה
   - אפליה/פרופיילינג = ציון 0 מיידי
   
3. טקטיקה (Tactics) - משקל 20%
   - ניצול מחסות, חתירה למגע, עבודת צוות
   
4. ניהול (Management) - משקל 20%
   - עבודה לפי פק"מ, דיווח תקין

ציין תמיד:
- הפניה לסעיף החוק הרלוונטי
- ניקוד מפורט עם הסבר לכל הפחתה
""",
        "clerk": """

*** תפקיד: הרשם (The Clerk) ***

אתה מנוע לוגי שתפקידו המרת טקסט למידע מובנה (JSON).
אין לך יצירתיות. יש לך רק דיוק.

חוקים:
1. קלט: טקסט גולמי (תרחיש).
2. פלט: JSON תקין בלבד לפי הסכמה SCENARIO_BUNDLE_SCHEMA.
3. תיקון שגיאות: אם חסר שדה, השלם אותו ל-"[חסר]" או ערך ברירת מחדל הגיוני. אל תמציא מידע שלא קיים בטקסט במפורש.
4. אל תענה שום מלל מלבד ה-JSON.
5. הקפד על סגירת סוגריים תקינה.
""",
        "simulator": ""  # Simulator gets just the full prompt
    }

    addendum = role_addendum.get(role, "")
    return full_prompt + addendum + language_guard


import argparse
import json
import logging
import os
import pathlib
import re
import sqlite3
import time
from datetime import datetime

import numpy as np
from openai import BadRequestError

from tatlam.settings import get_settings
from tatlam.core.llm_factory import client_cloud, client_local
from tatlam import configure_logging

# Get settings instance for module-level constants
_settings = get_settings()
DB_PATH = _settings.DB_PATH
EMB_TABLE = _settings.EMB_TABLE
EMBED_MODEL = _settings.EMBED_MODEL
GEN_MODEL = _settings.GEN_MODEL
LOCAL_MODEL = _settings.LOCAL_MODEL
SIM_THRESHOLD = _settings.SIM_THRESHOLD
TABLE_NAME = _settings.TABLE_NAME
VALIDATOR_MODEL = _settings.VALIDATOR_MODEL
from tatlam.core.bundles import coerce_bundle_shape
from tatlam.core.prompts import load_system_prompt, memory_addendum
from tatlam.core.validators import build_validator_prompt
from tatlam.infra.repo import insert_scenario
from tatlam.infra.db import get_db

configure_logging()

LOGGER = logging.getLogger(__name__)

DEBUG_DIR = pathlib.Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)


def _dbg(name: str, obj):
    (DEBUG_DIR / f"{name}.json").write_text(
        json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def strip_markdown_and_parse_json(text: str) -> dict | list | None:
    """
    Robust JSON parser that strips markdown code blocks before parsing.

    Handles LLM responses that may contain:
    - Markdown code blocks: ```json ... ``` or ``` ... ```
    - Plain JSON objects or arrays

    Returns:
        Parsed JSON object (dict or list) or None if parsing fails
    """
    if not text:
        return None

    # Step 1: Strip markdown code blocks
    # Pattern matches: ```json\n{...}\n``` or ```\n{...}\n```
    cleaned = text.strip()

    # Remove opening markdown fence with optional language specifier
    if cleaned.startswith("```"):
        # Find the end of the first line (language specifier)
        first_line_end = cleaned.find("\n")
        if first_line_end != -1:
            cleaned = cleaned[first_line_end + 1:]

    # Remove closing markdown fence
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    # Step 2: Try direct JSON parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Step 3: Try regex extraction of JSON object/array
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return None


def chat_create_safe(
    client,
    *,
    retries: int | None = None,
    backoff: float = 1.0,
    max_sleep: float = 4.0,
    **kwargs,
):
    """Robust wrapper around ``client.chat.completions.create`` with retries."""
    attempts = retries if retries is not None else int(os.getenv("CHAT_RETRIES", "3"))
    attempts = max(1, attempts)
    delay = max(0.1, backoff)
    last_err: Exception | None = None
    payload = dict(kwargs)
    for attempt in range(attempts):
        try:
            return client.chat.completions.create(**payload)
        except BadRequestError as err:
            last_err = err
            if "temperature" in str(err) and "temperature" in payload:
                LOGGER.debug(
                    "chat_create_safe dropping temperature after BadRequest on attempt %s",
                    attempt + 1,
                )
                payload.pop("temperature", None)
                continue
        except Exception as err:  # pragma: no cover - hit in failure scenarios only
            last_err = err
        if attempt == attempts - 1:
            break
        sleep_for = min(max_sleep, delay)
        LOGGER.warning(
            "chat_create_safe retry %s/%s due to %s",
            attempt + 1,
            attempts,
            last_err,
        )
        time.sleep(sleep_for)
        delay = min(max_sleep, delay * 2)
    if last_err is not None:
        raise last_err
    raise RuntimeError("chat_create_safe failed without raising an exception")


SYSTEM = load_system_prompt()


def build_batch_user_prompt(
    category: str, bundle_id: str | None = None, count: int | None = None
) -> str:
    """
    בונה את פרומפט המשתמש ליצירת batch של תטל״מים.
    מפתח: count = מספר מועמדים ליצירה (נשלח למודל המקומי)
    """
    if bundle_id is None:
        bundle_id = f"BUNDLE-{datetime.now().strftime('%Y%m%d-%H%M')}"
    if count is None:
        count = int(os.getenv("CANDIDATE_COUNT", os.getenv("BATCH_COUNT", "8")))
    return f"""
batch_id: {bundle_id}
category: {category}
count: {count}

מטרה:
צור בדיוק {count} תטל״מים ייחודיים בקטגוריה: "{category}". כל תטל״ם חייב להיות ריאליסטי, בהיר, מקצועי, וללא דרמה מיותרת. סביבת הייחוס: תחנות/קווי רכבת בישראל (תחנות תת־קרקע/עיליות), עם נהלים, סמכויות ושרשרת פיקוד כפי שמקובל.

מומחי Tree-of-Thought (דיון פנימי בלבד — אל תציג את הדיון בפלט):
1) Eng. Eli Navarro — מומחה אבטחה + מוסריות בתגובת המאבטח (איזון ביטחון/זכויות/שגרה).
2) קצין מבצעים — ניהול אירוע, דיווחים, שליטה מרחוק, תיאום מוקד/משטרה/חבלן/כיבוי.
3) יועץ משפטי/תפעולי — גבולות סמכות, עיכוב/כוח סביר/פתיחה באש, פרטיות/צילום.
כל הצעה שאין עליה הסכמה מלאה של שלושת המומחים — נפסלת. השתמשו בדיון קצר לקבלת החלטות, אך אל תציגו אותו בפלט; הציגו רק את התוצרים המוסכמים.

כללי איכות מחייבים:
- כל {count} התטל״מים יהיו שונים (כותרת/עלילה/דילמות/מיקום/זמן/Actors).
- שמור על שפת כתיבה: עברית מקצועית, מדויקת, תפעולית (שמות תחנות אמיתיים בישראל כשאפשר).
- שרשרת פיקוד ודיווח: מאבטח ↔ ר״צ/מוקד ↔ משטרה/חבלן/כיבוי; עצירת רכבות/פתיחת דלתות — תמיד דרך מוקד/מערכת שליטה.
- סמכויות: עיכוב על בסיס חשד סביר/סמ״חים; כוח סביר בלבד; פתיחה באש — רק אם מתקיימים כל 5 התנאים (אמצעי, כוונה, סכנת חיים, מיידיות, אין דרך אחרת).
- חשד למחבל מתאבד — שליטה מהירה/חשיפת לבוש; זיהוי חוטים/מטען → נטרול מיידי לראש (אם התקיימו תנאים).
- אין להמציא קישורים. אם אין תיעוד אמיתי — כתוב "אין תיעוד רלוונטי" והשאר את הקישור ריק.
- מסכה: ציין “כן/לא” והסבר קצר (אבק/עשן — כן; כימי/טוקסיקולוגי — לא, אין מסכת חומ״ס תקנית בתחנה).
- הדגש נקודות החלטה, תנאי הסלמה, והבחנות “מתי עיכוב/הרחקה/פינוי/Skip Station”.

פורמט טקסט מחייב לכל תטל״ם (אל תחרוג מהכותרות/האימוג׳ים הבאים):
🧩 כותרת: [קצרה ומדויקת]
📂 קטגוריה: {category}
🔥 רמת סיכון: [נמוכה/בינונית/גבוהה/גבוהה מאוד]
📊 רמת סבירות: [נמוכה/בינונית/גבוהה]
🧠 רמת מורכבות: [נמוכה/בינונית/גבוהה]

📋 סיפור מקרה:
- מיקום: [תחנה/אזור/קומה]
- תיאור: [עלילה מתפתחת, זמנים, Actors, דילמה מבצעית]

🎯 שלבי תגובה:
• [צעד 1 — דיווח/בקרה/מצלמות/פינוי חלקי/עצירת רכבות]
• [צעד 2 — עיכוב/תשאול/מודיעין מל״מ/סמכויות]
• [צעד 3 — הסלמה או הרגעה/תיאום כוחות]
• [צעד 4 — סיום/העברת מקל]

🔫 נוהל פתיחה באש:
[ציין אם לא התקיימו התנאים/לא רלוונטי/או נדרש — לפי כללי ה-5 תנאים]

😷 שימוש במסכה:
[כן/לא + למה]

🎥 רקע מבצעי:
[אירוע אמיתי דומה — מקום/שנה/מה קרה/תוצאות; אם אין — "אין תיעוד רלוונטי"]

📎 לינק לסרטון:
[קישור וידאו עד דקה אם קיים; אם לא — ריק]

CCTV
[מה לבקש מהמוקד לצפייה/הרצה/כיסוי שטח]

סמכויות
[איזה סמכות מופעלת: עיכוב/הרחקה/שימוש בכוח סביר/זיהוי עצמי/פרטיות צילום]

נקודות הכרעה
• [...]
• [...]

תנאי הסלמה
• [...]
• [...]

הצלחת אירוע
[קריטריונים לסיום טוב]

כשל אירוע
[מה השתבש/תופעות לוואי]

לקחים
• [...]
• [...]

וריאציות
• [...]

הערות משלימות:
- התאמה ספציפית לתצורת התחנה (רחוב→מדרגות/מדרגות נעות→כרטוס→רציפים; קומה טכנית רגישה; פורטלים למנהרה).
- אירוע כימי/טוקסי: עצירת תחנה/רכבות, פינוי, חומ״ס/כיבוי/מד״א; לא להסתמך על מסכות בתחנה.
- חפץ חשוד/כבודה עזובה: סגירה, פינוי, עצירת רכבות, חבלן; אם בקרון ואי אפשר לשלול — דיפו/כולא פיצוץ; אפשר Skip Station.
- אל תכלול שום טקסט מחוץ לתבנית או כותרות חדשות.
"""


# Helper: load_gold_examples
def load_gold_examples() -> str:
    """קורא דוגמאות זהב מתיקייה (GOLD_EXAMPLES) ומחזיר טקסט מקוצר לצירוף לפרומפט."""
    folder = os.getenv("GOLD_FS_DIR", "gold_md")
    p = pathlib.Path(folder)
    if not p.exists() or not p.is_dir():
        LOGGER.debug("Gold examples folder missing: %s", folder)
        return ""
    blobs: list[str] = []
    max_chars = int(os.getenv("GOLD_MAX_CHARS", "8000"))
    acc = 0
    files: list[pathlib.Path] = []
    files += sorted(p.glob("*.md"))[:12]
    files += sorted(p.glob("*.markdown"))[:12]
    files += sorted(p.glob("*.txt"))[:12]
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:
            LOGGER.debug("skip gold example %s: %s", fp, exc)
            continue
        head = "\n".join(text.splitlines()[:120])
        part = f"\n--- {fp.name} ---\n{head}\n"
        if acc + len(part) > max_chars:
            break
        blobs.append(part)
        acc += len(part)
    return "\n".join(blobs)


# ---- GOLD inspiration from DB (approved_by='Gold') ----
def _as_bullets(val) -> str:
    if not val:
        return ""
    if isinstance(val, list):
        items = val
    elif isinstance(val, str):
        try:
            obj = json.loads(val)
            items = obj if isinstance(obj, list) else [obj]
        except Exception:
            items = [val]
    else:
        items = [str(val)]
    out = []
    for x in items:
        s = str(x).strip()
        if s:
            out.append(f"- {s}")
    return "\n".join(out)


def load_gold_from_db(
    category: str | None = None,
    limit: int | None = None,
    max_chars: int | None = None,
    scope: str | None = None,
) -> str:
    """
    מחלץ דוגמאות 'Gold' ישירות מה-DB (approved_by='Gold').
    scope: "category" (ברירת מחדל) ייקח רק מהקטגוריה הנתונה,
           "all" יתעלם מהקטגוריה ויביא מכל הקטגוריות.
    אם category לא נתון או scope=="all" – לוקח מכל הקטגוריות.
    מחזיר טקסט קצר לשילוב בפרומפט (לעיון בלבד; אין להעתיק).
    """
    if limit is None:
        limit = int(os.getenv("GOLD_DB_LIMIT", "20"))
    if max_chars is None:
        max_chars = int(os.getenv("GOLD_MAX_CHARS", "8000"))
    if scope is None:
        scope = os.getenv("GOLD_SCOPE", "category").lower().strip()

    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        if category and scope != "all":
            cur.execute(
                f"""SELECT title, category, background, steps, required_response, debrief_points,
                            operational_background, media_link
                    FROM {TABLE_NAME}
                    WHERE lower(approved_by)='gold' AND category=?
                    ORDER BY id DESC
                    LIMIT ?""",
                (category, limit),
            )
        else:
            cur.execute(
                f"""SELECT title, category, background, steps, required_response, debrief_points,
                            operational_background, media_link
                    FROM {TABLE_NAME}
                    WHERE lower(approved_by)='gold'
                    ORDER BY id DESC
                    LIMIT ?""",
                (limit,),
            )
        rows = cur.fetchall()
    except Exception as exc:
        LOGGER.warning("load_gold_from_db failed: %s", exc)
        rows = []
    finally:
        try:
            con.close()
        except Exception as exc:
            LOGGER.debug("failed to close DB connection: %s", exc)

    blobs = []
    acc = 0
    for title, cat, background, steps, req, debrief, op_bg, media in rows:
        part = (
            f"\n### {title}\n"
            f"קטגוריה: {cat}\n"
            f"רקע: {background or ''}\n"
            f"שלבים:\n{_as_bullets(steps)}\n"
            f"תגובה נדרשת:\n{_as_bullets(req)}\n"
            f"תחקיר:\n{_as_bullets(debrief)}\n"
            f"רקע מבצעי: {op_bg or ''}\n"
            f"וידאו: {media or ''}\n"
        )
        if acc + len(part) > max_chars:
            break
        blobs.append(part)
        acc += len(part)

    return "\n".join(blobs)


def create_scenarios(category: str) -> dict:
    """
    ייצור *מועמדים* במודל המקומי → ייצוב כ-JSON בענן → החזרה כ-bundle.
    מספר המועמדים נקבע ע"י CANDIDATE_COUNT (ברירת מחדל 8).
    """
    bundle_id = f"BUNDLE-{datetime.now().strftime('%Y%m%d-%H%M')}"
    candidate_count = int(os.getenv("CANDIDATE_COUNT", os.getenv("BATCH_COUNT", "8")))

    # דוגמאות Gold מה-DB לפי scope, ואם אין — נפילה לקבצים בתיקייה
    scope = os.getenv("GOLD_SCOPE", "category").lower().strip()
    examples_db = load_gold_from_db(category if scope != "all" else None, scope=scope)
    examples_fs = "" if examples_db else load_gold_examples()

    examples_join = "\n".join(x for x in [examples_db, examples_fs] if x)
    examples_msg = (
        f"דוגמאות Gold (DB/קבצים — לעיון בלבד; אין להעתיק):\n{examples_join}"
        if examples_join
        else ""
    )

    # 1) טיוטת מועמדים במודל המקומי (עם נפילה לענן במקרה כשל)
    draft_text = ""
    try:
        local = client_local()
        resp_local = chat_create_safe(
            local,
            model=LOCAL_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                memory_addendum(),
                {
                    "role": "user",
                    "content": build_batch_user_prompt(
                        category=category, bundle_id=bundle_id, count=candidate_count
                    ),
                },
                *([{"role": "user", "content": examples_msg}] if examples_msg else []),
            ],
            temperature=0.7,
        )
        draft_text = (resp_local.choices[0].message.content or "").strip()
    except Exception as e:
        LOGGER.warning("local generation failed, falling back to cloud: %s", e)
        cloud_for_draft = client_cloud()
        resp_local = chat_create_safe(
            cloud_for_draft,
            model=GEN_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                memory_addendum(),
                {
                    "role": "user",
                    "content": build_batch_user_prompt(
                        category=category, bundle_id=bundle_id, count=candidate_count
                    ),
                },
                *([{"role": "user", "content": examples_msg}] if examples_msg else []),
            ],
        )
        draft_text = (resp_local.choices[0].message.content or "").strip()

    _dbg(f"01_local_raw_{bundle_id}", {"raw": draft_text[:5000]})

    # 2) ייצוב לענן — JSON בלבד
    cloud = client_cloud()
    resp_refine = chat_create_safe(
        cloud,
        model=GEN_MODEL,
        messages=[
            {
                "role": "system",
                "content": "החזר JSON תקין בלבד עם המפתח scenarios: [...], ללא מלל נוסף.",
            },
            {"role": "user", "content": draft_text},
        ],
        response_format={"type": "json_object"},
    )
    refined_text = (resp_refine.choices[0].message.content or "").strip()

    # 3) פרסינג ל-bundle; ניסיון נוסף אם נכשל
    data: dict | list | None = strip_markdown_and_parse_json(refined_text)

    if data is None:
        try:
            resp_refine2 = chat_create_safe(
                cloud,
                model=GEN_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "הפוך את הטקסט הבא ל-JSON חוקי בלבד עם המפתח scenarios: [...]. אל תצרף הסברים.",
                    },
                    {"role": "user", "content": draft_text},
                ],
                response_format={"type": "json_object"},
            )
            refined_text2 = (resp_refine2.choices[0].message.content or "").strip()
            data = strip_markdown_and_parse_json(refined_text2)
        except Exception:
            data = None

    if isinstance(data, dict) and "scenarios" in data:
        bundle = {"bundle_id": bundle_id, "scenarios": data.get("scenarios", [])}
    elif isinstance(data, list):
        bundle = {"bundle_id": bundle_id, "scenarios": data}
    elif isinstance(data, dict):
        bundle = {"bundle_id": bundle_id, "scenarios": [data]}
    else:
        bundle = {"bundle_id": bundle_id, "scenarios": []}

    # 4) ולידציה בסיסית
    try:
        bundle = check_and_repair(bundle)
    except Exception as exc:
        LOGGER.debug("refine JSON parse fallback failed: %s", exc)

    # Normalize shapes/types so DB insert and rendering never break
    bundle = coerce_bundle_shape(bundle)
    bundle.setdefault("bundle_id", bundle_id)
    bundle.setdefault("scenarios", [])
    _dbg(f"02_refined_{bundle_id}", bundle)
    return bundle


# Helper: score_one_scenario
def score_one_scenario(sc: dict) -> tuple[float, dict]:
    """נותן ציון איכות ע"פ ולידטור (0..100) ומחזיר (score, scenario_fixed)."""
    rubric = (
        'דרג 0..100 את איכות התטל"ם מול הקריטריונים: בהירות, ריאליזם, שונות מול דוגמאות, '
        "תואם תבנית אימוג׳ים, חוקיות (סמכויות/פתיחה באש), שלבי תגובה, התאמה לדוגמאות Gold "
        "והעדפה להשראה מאירועים אמיתיים. ענישה חזקה על הזיות/המצאות. "
        "אם אין 'רקע מבצעי' אמיתי — יש לציין 'אין תיעוד רלוונטי' ולהשאיר קישור ריק. "
        "החזר JSON {'score': int, 'scenario': {...}} בלבד."
    )
    cloud = client_cloud()
    resp = chat_create_safe(
        cloud,
        model=os.getenv("VALIDATOR_MODEL", VALIDATOR_MODEL),
        messages=[
            {"role": "system", "content": rubric},
            {"role": "user", "content": json.dumps(sc, ensure_ascii=False)},
        ],
        response_format={"type": "json_object"},
    )
    text = (resp.choices[0].message.content or "").strip()
    try:
        obj = json.loads(text)
        return float(obj.get("score", 0)), obj.get("scenario", sc)
    except Exception:
        return 0.0, sc


# Helper: select_top_k_diverse
def select_top_k_diverse(items: list[tuple[float, dict]], k: int) -> list[dict]:
    """בחירה גרידית: ציונים גבוהים + שונות אמבדינגים."""
    max_sim = float(os.getenv("DIVERSITY_MAX_SIM", "0.92"))
    chosen: list[dict] = []
    chosen_vecs: list[np.ndarray | None] = []
    items = sorted(items, key=lambda x: x[0], reverse=True)
    for _score, sc in items:
        if len(chosen) >= k:
            break
        v = embed_text((sc.get("title", "") + "\n" + sc.get("background", "")).strip())
        if v is None:
            chosen.append(sc)
            chosen_vecs.append(None)
            continue
        ok = True
        for w in chosen_vecs:
            if w is not None and cosine(v, w) >= max_sim:
                ok = False
                break
        if ok:
            chosen.append(sc)
            chosen_vecs.append(v)
    return chosen


# Helper: evaluate_and_pick
def evaluate_and_pick(bundle: dict) -> dict:
    """מעניק ציונים לכל המועמדים ובוחר רק את K הטובים והשונים."""
    keep_k = int(os.getenv("KEEP_TOP_K", "5"))
    scored: list[tuple[float, dict]] = []
    for sc in bundle.get("scenarios", []):
        scored.append(score_one_scenario(sc))
    best = select_top_k_diverse(scored, keep_k)
    bid = bundle.get("bundle_id", "")
    _dbg(
        f"03_scored_{bid}",
        [{"score": s, "title": sc.get("title", "")} for s, sc in scored],
    )
    _dbg(
        f"04_selected_{bid}",
        {"titles": [sc.get("title", "") for sc in best]},
    )
    return {"bundle_id": bundle.get("bundle_id", ""), "scenarios": best}


def check_and_repair(bundle: dict) -> dict:
    """
    ולידציה/תיקון בענן, מחזיר תמיד dict; אם נכשל – מחזיר את bundle המקורי.
    """
    prompt = build_validator_prompt(bundle)
    cloud = client_cloud()
    try:
        resp = chat_create_safe(
            cloud,
            model=VALIDATOR_MODEL,
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON; no prose."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as e:
        LOGGER.warning("validator call failed (%s); using original bundle", e)
        return bundle
    text = (resp.choices[0].message.content or "").strip()
    # Use robust JSON parser to handle markdown code blocks
    fixed = strip_markdown_and_parse_json(text)
    if fixed and isinstance(fixed, dict):
        return fixed
    LOGGER.warning("Validator returned non-JSON; using original bundle")
    return bundle


# New helper: coerce_bundle_shape


def embed_text(text: str) -> np.ndarray | None:
    try:
        cloud = client_cloud()
        r = cloud.embeddings.create(model=EMBED_MODEL, input=text)
        return np.array(r.data[0].embedding, dtype=np.float32)
    except Exception as e:  # noqa: BLE001 - external API errors are expected sometimes
        LOGGER.warning("embed_text failed: %s", e)
        return None


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))




def load_all_embeddings():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(f"SELECT title, vector_json FROM {EMB_TABLE}")
    rows = cur.fetchall()
    con.close()
    titles, vecs = [], []
    for t, vjson in rows:
        if not t or not vjson:
            continue
        try:
            vec = np.array(json.loads(vjson), dtype=np.float32)
            if vec.size:
                titles.append(t)
                vecs.append(vec)
        except Exception as exc:
            LOGGER.debug("embedding parse failed for %s: %s", t, exc)
            continue
    return titles, vecs


def save_embedding(title: str, vec: np.ndarray):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        f"INSERT OR REPLACE INTO {EMB_TABLE} (title, vector_json) VALUES (?, ?)",
        (title, json.dumps(vec.tolist())),
    )
    con.commit()
    con.close()


def is_duplicate_title(title: str, titles, vecs, threshold: float | None = None):
    """
    מחזיר (is_duplicate: bool, v: np.ndarray | None)
    מחשב אמבדינג לכותרת, משווה לקיימים, ובודק אם יש דומה מעל הסף.
    """
    v = embed_text(title)
    if v is None:
        return False, None
    valid_vecs = [w for w in vecs if isinstance(w, np.ndarray) and getattr(w, "size", 0) > 0]
    if not valid_vecs:
        return False, v
    if threshold is None:
        threshold = SIM_THRESHOLD
    sims = [cosine(v, w) for w in valid_vecs]
    best = max(sims) if sims else -1.0
    return (best >= threshold), v


def dedup_and_embed_titles(bundle: dict):
    mem_titles, mem_vecs = load_all_embeddings()
    for sc in bundle.get("scenarios", []):
        title = (sc.get("title") or "").strip()
        if not title:
            title = f"תרחיש ללא כותרת {datetime.now().strftime('%H%M%S')}"
            sc["title"] = title
        is_dup, v = is_duplicate_title(title, mem_titles, mem_vecs)
        if is_dup:
            new_title = minimal_title_fix(title)
            sc["title"] = new_title
            v = embed_text(new_title)
        if v is None or getattr(v, "size", 0) == 0:
            v = embed_text(sc["title"])  # ניסיון נוסף
        mem_titles.append(sc["title"])
        if v is not None and getattr(v, "size", 0) > 0:
            mem_vecs.append(v)
            save_embedding(sc["title"], v)
        else:
            mem_vecs.append(None)
    return bundle


def minimal_title_fix(old_title: str) -> str:
    """
    מקבל כותרת קיימת ומבקש מהמודל להחזיר כותרת דומה אך ייחודית.
    מחזיר תמיד מחרוזת; אם אין JSON תקין – חוזר ל-old_title.
    """
    cloud = client_cloud()
    r = chat_create_safe(
        cloud,
        model=os.getenv("CHECKER_MODEL", os.getenv("CHECKER_MODEL", "")),
        messages=[
            {
                "role": "system",
                "content": "שנה רק את שדה title כדי למנוע דמיון לשמות קיימים; החזר JSON תקין בלבד בפורמט {'title':'...'} ללא טקסט נוסף.",
            },
            {
                "role": "user",
                "content": json.dumps({"title": old_title}, ensure_ascii=False),
            },
        ],
        response_format={"type": "json_object"},
    )
    text = (r.choices[0].message.content or "").strip()
    data = strip_markdown_and_parse_json(text)
    if data and isinstance(data, dict):
        new_title = (data.get("title") or "").strip()
        if new_title:
            return new_title
    LOGGER.debug("minimal_title_fix failed to parse JSON response, using old_title")
    return old_title




def run_batch(category: str, owner="Sahar"):
    # DB initialization is handled by get_db() in tatlam.infra.db
    # 1) יצירת מועמדים
    candidates = create_scenarios(category)
    # 2) הערכה ובחירת  K
    bundle = evaluate_and_pick(candidates)
    # 3) דה-דופ ואמבדינגים
    bundle = dedup_and_embed_titles(bundle)
    # 4) שמירה למסד - iterate over scenarios and save using insert_scenario
    inserted = 0
    for sc in bundle.get("scenarios", []):
        # Ensure bundle_id is in each scenario for traceability
        sc.setdefault("bundle_id", bundle.get("bundle_id", ""))
        try:
            insert_scenario(sc, owner=owner, pending=False)
            inserted += 1
        except ValueError as e:
            LOGGER.warning("Failed to insert scenario '%s': %s", sc.get("title", ""), e)
    LOGGER.info('נשמרו %d תטל"מים לבסיס הנתונים: %s', inserted, DB_PATH)
    LOGGER.info("bundle_id: %s", bundle.get('bundle_id'))
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="הכנס קטגוריה מהרשימה")
    parser.add_argument("--owner", default="Sahar")
    args = parser.parse_args()
    run_batch(args.category, owner=args.owner)

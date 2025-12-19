"""Import GOLD markdown examples and insert into DB."""

import os
import re
import sys
import unicodedata
from datetime import datetime

from run_batch import check_and_repair, dedup_and_embed_titles, ensure_db, insert_bundle

# ------------------------------- קונפיג וזיהוי סקשנים -------------------------------

SEC_NAMES = [
    "סיפור מקרה",
    "שלבי תגובה",
    "נוהל פתיחה באש",
    "רקע מבצעי",
    "קישור",
    "לינק",
    "CCTV",
    "סמכויות",
    "נקודות הכרעה",
    "תנאי הסלמה",
    "הצלחת אירוע",
    "כשל אירוע",
    "לקחים",
    "וריאציות",
    # שדות מטא שיכולים להופיע כסקשן עם ערך בשורה הבאה
    "קטגוריה",
    "רמת סיכון",
    "רמת סבירות",
    "רמת מורכבות",
    "מיקום",
    "שימוש במסכה",
]

# דרוש אחד: כותרת Markdown (##+), מודגשת (**שם**), או שם סקשן עם נקודתיים
_HDR_RE = re.compile(
    r"^\s*(?:#{2,}\s*(?P<h1>.+?)\s*$|\*\*\s*(?P<h2>.+?)\s*\*\*\s*$|(?P<h3>[^:]{2,60}):\s*$)",
    re.M,
)

KV_MAP = {
    "קטגוריה": "category",
    "רמת סיכון": "threat_level",
    "רמת סבירות": "likelihood",
    "רמת מורכבות": "complexity",
    "נוהל פתיחה באש": "rules_of_engagement",
    "שימוש במסכה": "mask_usage",
    "מיקום": "location",
}

# --- ניקוי אמוג'י ותווי קישוט מכותרות שדות/סקשנים ---
_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF\U00002600-\U000026FF\U00002B00-\U00002BFF\U0000FE0F]+",
    re.UNICODE,
)


def _normalize_hebrew(text: str) -> str:
    """Apply Unicode NFC normalization to Hebrew text.

    NFC (Canonical Decomposition, followed by Canonical Composition) ensures
    that Hebrew characters with diacritics are stored in their canonical composed form,
    preventing comparison issues with visually identical but byte-different strings.
    """
    if not text:
        return text
    return unicodedata.normalize("NFC", text)


def _clean_label(s: str) -> str:
    # מסיר אמוג'י, תווי עיצוב, # ו-*, ומשאיר רק טקסט נקי להשוואה מול המפתח העברי
    s = _EMOJI_RE.sub("", s or "")
    s = s.replace("**", "").replace("#", "").strip()
    # נטרול רווחים כפולים
    s = re.sub(r"\s+", " ", s)
    # Apply NFC normalization for consistent Hebrew comparison
    return _normalize_hebrew(s)


def _map_k(k: str) -> str | None:
    """מקבל תווית בעברית (לאחר ניקוי) ומחזיר את שם השדה הקנוני ב-JSON לפי KV_MAP."""
    k = _clean_label(k)
    # ניסיון התאמה ישירה
    if k in KV_MAP:
        return KV_MAP[k]
    # ניסיון התאמה ע"י הכלה דו-כיוונית (לכותרות עם מילים נוספות)
    for he_key, canon in KV_MAP.items():
        if he_key in k or k in he_key:
            return canon
    return None


LINK_RE = re.compile(r"\((https?://[^\s)]+)\)|\b(https?://[^\s)]+)")

# --------------------------------- עזרי המרה ---------------------------------


def _he_bool(v: str):
    v = (v or "").strip().lower()
    if v in {"yes", "כן", "true", "y"}:
        return "כן"
    if v in {"no", "לא", "false", "n"}:
        return "לא"
    return None if not v else v  # ריק => None, אחרת החזר המקור


def _is_heading_line(line: str) -> str | None:
    """
    אם השורה היא כותרת סקשן – החזר את שם הכותרת; אחרת None.
    מכסה: ## כותרת, **כותרת**, או 'כותרת:'.
    """
    m = _HDR_RE.match(line)
    if not m:
        return None
    name = m.group("h1") or m.group("h2") or m.group("h3") or ""
    name = name.strip().strip("*").strip()
    # נבדוק שהיא אחת מרשימת הסקשנים המוכרים (או מכילה אותם)
    for nm in SEC_NAMES:
        if nm in name:
            return nm
    return None


def _section(md: str, wanted_name: str) -> str:
    """
    חילוץ טקסט בין כותרת הסקשן המבוקש לכותרת הסקשן הבאה.
    """
    lines = md.splitlines(True)  # כולל \n
    start_idx = None
    for i, ln in enumerate(lines):
        hdr = _is_heading_line(ln)
        if hdr and wanted_name in ln:
            start_idx = i + 1
            break
    if start_idx is None:
        return ""
    end_idx = len(lines)
    for j in range(start_idx, len(lines)):
        if _is_heading_line(lines[j]):
            end_idx = j
            break
    return "".join(lines[start_idx:end_idx]).strip()


def _lines_or_sentences(txt: str) -> list[str]:
    txt = (txt or "").strip()
    if not txt:
        return []
    lines = [line.strip(" \t-•") for line in txt.splitlines() if line.strip()]
    if len(lines) > 1:
        return lines
    parts = re.split(r"[.!?]\s+", txt)
    return [p.strip(" \n-•") for p in parts if p.strip()]


def _first_nonempty_line(txt: str) -> str:
    for ln in (txt or "").splitlines():
        val = ln.strip()
        if val:
            return val
    return ""


def _canon_level(val: str | None) -> str | None:
    if not val:
        return None
    v = val.strip()
    mapping = globals().get("CANON_LEVELS", {}) or {}
    return mapping.get(v, v)


# --------------------------------- פרסור MD ---------------------------------


def parse_md_to_scenario(md_text: str) -> dict:
    # Normalize Unicode to NFC for consistent Hebrew text handling
    md = _normalize_hebrew(md_text.replace("\r\n", "\n"))

    # כותרת: "# ..." או "🧩 כותרת: ..."
    title = None
    m = re.search(r"^\s*#\s*(.+)$", md, re.M)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r"🧩\s*כותרת[:：]\s*(.+)", md)
        if m:
            title = m.group(1).strip()
    if not title:
        title = "ללא כותרת"

    # בלוק כותרת-על: עד כותרת סקשן ראשונה
    lines = md.splitlines()
    header_end = len(lines)
    for i, ln in enumerate(lines):
        if _is_heading_line(ln):
            header_end = i
            break
    header_block = "\n".join(lines[:header_end])

    # מפה של KV
    kv = {}
    for line in header_block.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = _clean_label(k)
        v = v.strip()
        key = _map_k(k)
        if not key:
            continue
        if key in {"mask_usage", "rules_of_engagement"}:
            kv[key] = _he_bool(v)
        elif key in {"threat_level", "likelihood", "complexity"}:
            kv[key] = _canon_level(v)
        else:
            kv[key] = v

    # --- Fallback: נסה לחלץ ערכים שמופיעים כסקשן עם ערך בשורה הבאה ---
    for he_key, canon in KV_MAP.items():
        if kv.get(canon):
            continue
        sec_txt = _section(md, he_key)
        if not sec_txt:
            continue
        val = _first_nonempty_line(sec_txt)
        if not val:
            continue
        if canon == "rules_of_engagement":
            # לטקסט המלא נטפל בהמשך ב-roe_text
            continue
        if canon == "mask_usage":
            kv[canon] = _he_bool(val)
        elif canon in {"threat_level", "likelihood", "complexity"}:
            kv[canon] = _canon_level(val)
        else:
            kv[canon] = val

    # שליפות סקשנים
    background = _section(md, "סיפור מקרה")
    steps_raw = _section(md, "שלבי תגובה")
    roe_text = _section(md, "נוהל פתיחה באש")
    op_bg = _section(md, "רקע מבצעי")
    media_sec = _section(md, "קישור") or _section(md, "לינק")
    cctv_sec = _section(md, "CCTV")
    auth_sec = _section(md, "סמכויות")
    dp_sec = _section(md, "נקודות הכרעה")
    esc_sec = _section(md, "תנאי הסלמה")
    succ_sec = _section(md, "הצלחת אירוע")
    fail_sec = _section(md, "כשל אירוע")
    lessons_sec = _section(md, "לקחים")
    vars_sec = _section(md, "וריאציות")

    steps = _lines_or_sentences(steps_raw)
    decision_points = _lines_or_sentences(dp_sec)
    escalation = _lines_or_sentences(esc_sec)
    lessons = _lines_or_sentences(lessons_sec)
    variations = _lines_or_sentences(vars_sec)

    # קישור למדיה (תומך גם ב-(http...) וגם ב-טקסט חשוף)
    m = LINK_RE.search(media_sec or "")
    media_link = (m.group(1) or m.group(2)) if m else None

    scenario = {
        "external_id": "",
        "title": title,
        "category": kv.get("category") or "",
        "threat_level": kv.get("threat_level"),
        "likelihood": kv.get("likelihood"),
        "complexity": kv.get("complexity"),
        "location": kv.get("location") or "",
        "background": background or "",
        "steps": steps,
        "required_response": [],
        "debrief_points": [],
        "operational_background": op_bg or "אין תיעוד רלוונטי",
        "media_link": media_link,
        "mask_usage": kv.get("mask_usage"),  # "כן"/"לא"/None
        "authority_notes": auth_sec or "",
        "cctv_usage": cctv_sec or "",
        "comms": [],
        "decision_points": decision_points,
        "escalation_conditions": escalation,
        "end_state_success": succ_sec or "",
        "end_state_failure": fail_sec or "",
        "lessons_learned": lessons,
        "variations": variations,
        "validation": ["json_valid", "ethical_balance_ok"],
    }

    # ROE
    roe_text = (roe_text or "").strip()
    if roe_text:
        scenario["rules_of_engagement"] = roe_text
    elif kv.get("rules_of_engagement") in {"כן", "לא"}:
        scenario["rules_of_engagement"] = kv["rules_of_engagement"]
    else:
        scenario["rules_of_engagement"] = None

    return scenario


# --------------------------------- main ---------------------------------


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_gold_md.py <folder_with_md>")
        sys.exit(1)

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print("התיקייה לא קיימת:", folder)
        sys.exit(1)

    files = sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(".md"))
    if not files:
        print("לא נמצאו קבצי .md בתיקייה:", folder)
        sys.exit(1)

    scenarios = []
    errors = 0

    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                md = fh.read()
            sc = parse_md_to_scenario(md)
            sc["external_id"] = f"GOLD-{os.path.splitext(os.path.basename(path))[0]}"
            scenarios.append(sc)
        except Exception as e:
            errors += 1
            print(f"⚠️  שגיאה בפרסור '{os.path.basename(path)}': {e}")

    # סינון תסריטים ריקים (למשל אם אין כותרת ותוכן)
    scenarios = [s for s in scenarios if s.get("title") and (s.get("background") or s.get("steps"))]

    bundle = {
        "bundle_id": f"GOLD-{datetime.now().strftime('%Y%m%d-%H%M')}",
        "scenarios": scenarios,
    }

    # הכנסה מסודרת ל־DB – עם נפילות רכות
    ensure_db()

    try:
        bundle = check_and_repair(bundle)
    except Exception as e:
        print(f"⚠️  check_and_repair נכשל: {e} — ממשיכים עם הנתונים הגולמיים")

    try:
        bundle = dedup_and_embed_titles(bundle)
    except Exception as e:
        print(f"⚠️  אמבדינג/דדופ נכשל: {e} — נשמר בלי אמבדינג")

    insert_bundle(bundle, owner="GoldSeed", approved_by="Gold")

    print(f"✔ הוכנסו {len(bundle['scenarios'])} תטל\"מים כ-Gold. bundle_id={bundle['bundle_id']}")
    if errors:
        print(f"ℹ️  היו {errors} קבצים עם שגיאות פרסור — ראו לוג למעלה.")
    for sc in bundle["scenarios"]:
        print(" •", sc.get("title", "(ללא כותרת)"))


if __name__ == "__main__":
    main()

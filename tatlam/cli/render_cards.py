from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from jinja2 import Template

from config import DB_PATH, TABLE_NAME

# שדות שמאוחסנים ב-SQLite כמחרוזות JSON, ונרצה להמיר חזרה למבני פייתון
JSON_LIST_FIELDS = [
    "steps",
    "required_response",
    "debrief_points",
    "decision_points",
    "escalation_conditions",
    "lessons_learned",
    "variations",
    "comms",
    "validation",
]


def _json_to_list(val: Any) -> list[Any]:
    """המרת תוכן עמודה (שעלול להיות list/str/None) לרשימה.
    - אם כבר list → החזר כמו שהוא
    - אם None/ריק → []
    - אם str שמכיל JSON תקין → פרס
    - אחרת → עטוף כמחרוזת יחידה בתוך רשימה כדי לא להפיל רינדור
    """
    if isinstance(val, list):
        return val
    if val is None:
        return []
    if isinstance(val, str):
        s = val.strip()
        if not s or s.lower() in {"null", "none", "[]"}:
            return []
        try:
            parsed = json.loads(s)
            # אם יצא אובייקט בודד (dict/str/num) – נהפוך לרשימה כדי להתאים לתבנית שמצפה לרשימות
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except Exception:
            return [val]
    # טיפוסים אחרים (int/float/dict) – נהפוך לרשימה שמכילה אותם
    return [val]


def _none_if_blank(s: str | None) -> str | None:
    if s is None:
        return None
    s2 = str(s).strip()
    return s2 or None


def coerce_row_types(row: dict[str, Any]) -> dict[str, Any]:
    """מחזיר עותק של הרשומה עם המרות טיפוסים לשדות JSON וערכי ברירת מחדל בטוחים."""
    r = dict(row)
    for k in JSON_LIST_FIELDS:
        r[k] = _json_to_list(r.get(k))

    # ערכי ברירת מחדל לשדות טקסטואליים
    r.setdefault("title", "ללא כותרת")
    r.setdefault("category", "לא מסווג")
    r.setdefault("threat_level", "לא צוין")
    r.setdefault("likelihood", "לא צוין")
    r.setdefault("complexity", "לא צוין")
    r.setdefault("location", "")
    r.setdefault("background", "")
    r.setdefault("operational_background", "אין תיעוד רלוונטי")
    r["media_link"] = _none_if_blank(r.get("media_link"))

    # נורמליזציה לשדה מסכה: החזר "כן"/"לא"/None בלבד
    mu = r.get("mask_usage")
    if isinstance(mu, str):
        mu_l = mu.strip().lower()
        if mu_l in {"yes", "true", "y", "כן"}:
            r["mask_usage"] = "כן"
        elif mu_l in {"no", "false", "n", "לא"}:
            r["mask_usage"] = "לא"
        else:
            r["mask_usage"] = None
    elif mu is None:
        r["mask_usage"] = None

    r.setdefault("cctv_usage", "")
    r.setdefault("authority_notes", "")
    return r


# נתיב ברירת מחדל לתבנית – יחסי לקובץ זה
DEFAULT_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "templates" / "tatlam_card.md.j2"
)


def load_template(path: str | None = None) -> Template:
    tpl_path = Path(path) if path else DEFAULT_TEMPLATE_PATH
    with open(tpl_path, encoding="utf-8") as f:
        return Template(f.read())


def _safe_table(name: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError("Unsafe table name")
    return name


def fetch(category: str | None = None, bundle_id: str | None = None) -> list[dict[str, Any]]:
    # שימוש ב-row_factory כדי לאפשר גישה לשמות עמודות כמו dict
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()

        tn = _safe_table(TABLE_NAME)
        if category and bundle_id:
            sql = f"SELECT * FROM {tn} WHERE category=? AND bundle_id=? ORDER BY id DESC"  # nosec
            cur.execute(sql, (category, bundle_id))
        elif category:
            sql = f"SELECT * FROM {tn} WHERE category=? ORDER BY id DESC"  # nosec
            cur.execute(sql, (category,))
        elif bundle_id:
            sql = f"SELECT * FROM {tn} WHERE bundle_id=? ORDER BY id DESC"  # nosec
            cur.execute(sql, (bundle_id,))
        else:
            sql = f"SELECT * FROM {tn} ORDER BY id DESC"  # nosec
            cur.execute(sql)

        rows = [dict(r) for r in cur.fetchall()]
    return rows


_HEB_SAFE = re.compile(r"[^0-9A-Za-z\u0590-\u05FF _.-]")
_WS = re.compile(r"[\s\n\r]+")


def safe_filename(title: str) -> str:
    """slug פשוט ששומר עברית, אותיות לטיניות, ספרות, רווח/נקודה/קו/קו תחתון."""
    title = title or "scenario"
    title = _WS.sub(" ", title).strip()
    title = title.replace("/", "-").replace("\\", "-")
    title = _HEB_SAFE.sub("", title)
    title = title.replace(" ", "_")
    return title or "scenario"


def unique_path(base_dir: Path, name: str) -> Path:
    """מבטיח שם קובץ ייחודי בתיקייה (מוסיף -1, -2 ... אם צריך)."""
    p = base_dir / name
    if not p.exists():
        return p
    stem = p.stem
    suf = p.suffix
    i = 1
    while True:
        cand = base_dir / f"{stem}-{i}{suf}"
        if not cand.exists():
            return cand
        i += 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='ייצוא תטל"מים ל-Markdown')
    ap.add_argument("--category", help="סינון לפי קטגוריה", default=None)
    ap.add_argument("--bundle", help="סינון לפי bundle_id", default=None)
    ap.add_argument("--limit", type=int, default=None, help="כמה כרטיסיות להפיק לכל היותר")
    ap.add_argument("--out", required=True, help="תיקיית יעד לקבצי ה-Markdown")
    ap.add_argument(
        "--template",
        default=None,
        help="נתיב חלופי לתבנית Jinja2 (ברירת מחדל: templates/tatlam_card.md.j2)",
    )
    ap.add_argument(
        "--subdirs-by-category", action="store_true", help="שמור לתת-תיקיות לפי קטגוריה"
    )
    ap.add_argument(
        "--prefix-id",
        action="store_true",
        help="קדם את שם הקובץ עם מזהה הרשומה (id_) כדי למנוע התנגשות שמות",
    )
    args = ap.parse_args(argv)

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tmpl = load_template(args.template)

    rows = fetch(category=args.category, bundle_id=args.bundle)
    if args.limit is not None:
        rows = rows[: args.limit]

    count = 0
    for row in rows:
        r = coerce_row_types(row)
        # בניית שם קובץ
        base_name = safe_filename(r.get("title", "scenario")) + ".md"
        if args.prefix_id and row.get("id") is not None:
            base_name = f"{row['id']}_{base_name}"

        target_dir = out_dir
        if args.subdirs_by_category:
            cat_slug = safe_filename(r.get("category", "uncategorized"))
            target_dir = out_dir / cat_slug
            target_dir.mkdir(parents=True, exist_ok=True)

        fname = unique_path(target_dir, base_name)

        # רינדור וכתיבה
        md = tmpl.render(**r)
        with open(fname, "w", encoding="utf-8") as f:
            f.write(md)
        count += 1

    print(f"✔ נוצרו {count} קבצי Markdown בתיקייה {out_dir}")
    return 0


__all__ = [
    "JSON_LIST_FIELDS",
    "_json_to_list",
    "_none_if_blank",
    "coerce_row_types",
    "DEFAULT_TEMPLATE_PATH",
    "load_template",
    "fetch",
    "safe_filename",
    "unique_path",
    "main",
]

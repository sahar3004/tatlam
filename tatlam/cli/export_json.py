from __future__ import annotations

import argparse
import json
import re
import sqlite3
from typing import Any

from config import DB_PATH, TABLE_NAME


def _safe_table(name: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError("Unsafe table name")
    return name


def fetch_rows(category: str | None = None, bundle_id: str | None = None) -> list[dict[str, Any]]:
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    tn = _safe_table(TABLE_NAME)
    if category:
        cur.execute(f"SELECT * FROM {tn} WHERE category=?", (category,))  # nosec
    elif bundle_id:
        cur.execute(f"SELECT * FROM {tn} WHERE bundle_id=?", (bundle_id,))  # nosec
    else:
        cur.execute(f"SELECT * FROM {tn}")  # nosec
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    con.close()
    return rows


def normalize(row: dict[str, Any]) -> dict[str, Any]:
    def load(x: Any) -> Any:
        try:
            return json.loads(x) if x else []
        except Exception:
            return []

    for key in [
        "steps",
        "required_response",
        "debrief_points",
        "comms",
        "decision_points",
        "escalation_conditions",
        "lessons_learned",
        "variations",
        "validation",
    ]:
        row[key] = load(row.get(key))
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--category")
    ap.add_argument("--bundle_id")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    rows = fetch_rows(args.category, args.bundle_id)
    data = [normalize(r) for r in rows]
    with open(args.out, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✔ נכתב {len(data)} רשומות ל- {args.out}")
    return 0


__all__ = ["fetch_rows", "normalize", "main"]

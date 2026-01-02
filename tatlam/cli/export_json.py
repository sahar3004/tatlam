from __future__ import annotations

import argparse
import json
from typing import Any

from sqlalchemy import select

from tatlam.infra.db import get_session
from tatlam.infra.models import Scenario
from tatlam.settings import get_settings

# Get settings for module-level constants
_settings = get_settings()
DB_PATH = _settings.DB_PATH
TABLE_NAME = _settings.TABLE_NAME


def fetch_rows(category: str | None = None, bundle_id: str | None = None) -> list[dict[str, Any]]:
    """Fetch scenarios from the database using SQLAlchemy.

    Parameters
    ----------
    category : str | None
        Filter by category.
    bundle_id : str | None
        Filter by bundle ID.

    Returns
    -------
    list[dict[str, Any]]
        List of scenario dictionaries.
    """
    with get_session() as session:
        stmt = select(Scenario)

        if category:
            stmt = stmt.where(Scenario.category == category)
        elif bundle_id:
            stmt = stmt.where(Scenario.bundle_id == bundle_id)

        scenarios = session.scalars(stmt).all()
        return [s.to_dict() for s in scenarios]


def normalize(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a scenario row - ensures JSON fields are parsed.

    Note: This is now largely a no-op since Scenario.to_dict() already
    parses JSON fields. Kept for backward compatibility.
    """

    def load(x: Any) -> Any:
        if isinstance(x, (list, dict)):
            return x
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

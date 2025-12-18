from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from config import REQUIRE_APPROVED_ONLY, TABLE_NAME
from tatlam.core.categories import CATS, category_to_slug
from tatlam.infra.db import get_db


def _getconn() -> sqlite3.Connection:
    return get_db()


def db_has_column(table: str, col: str) -> bool:
    try:
        # Resolve DB_PATH at call time to respect tests that reload config
        from importlib import import_module

        cfg = import_module("config")
        with sqlite3.connect(cfg.DB_PATH) as _c:
            cur = _c.cursor()
            cur.execute(f"PRAGMA table_info({table})")  # nosec B608 - table is trusted
            return any(r[1] == col for r in cur.fetchall())
    except Exception:
        return False


_HAS_STATUS = db_has_column(TABLE_NAME, "status")

JSON_FIELDS: list[str] = [
    "steps",
    "required_response",
    "debrief_points",
    "comms",
    "decision_points",
    "escalation_conditions",
    "lessons_learned",
    "variations",
    "validation",
]


def _parse_json_field(val: Any) -> list[Any] | dict[str, Any]:
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str) and not val.strip():
        return []
    try:
        loaded = json.loads(val)
    except Exception:
        return []
    if isinstance(loaded, (list, dict)):
        return loaded
    return []


def normalize_row(row: sqlite3.Row) -> dict[str, Any]:
    r: dict[str, Any] = {k: row[k] for k in row.keys()}
    # Normalize JSON-like text fields
    for key in JSON_FIELDS:
        r[key] = _parse_json_field(r.get(key))
    return r


def is_approved_row(row: dict[str, Any]) -> bool:
    if not REQUIRE_APPROVED_ONLY:
        return True
    if _HAS_STATUS:
        return (row.get("status") or "").strip().lower() == "approved"
    ab = (row.get("approved_by") or "").strip().lower()
    return ab in {"admin", "human", "approved", "manager"}


def fetch_all_basic_categories() -> list[dict[str, Any]]:
    con = _getconn()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT id, title, category, status, approved_by, created_at FROM {TABLE_NAME} "  # noqa: S608  # nosec
            "ORDER BY datetime(created_at) DESC, id DESC"
        )
    except sqlite3.OperationalError:
        select_cols = ["id", "title", "category"]
        if db_has_column(TABLE_NAME, "status"):
            select_cols.append("status")
        if db_has_column(TABLE_NAME, "approved_by"):
            select_cols.append("approved_by")
        cur.execute(
            f"SELECT {', '.join(select_cols)} FROM {TABLE_NAME} ORDER BY id DESC"  # noqa: S608  # nosec
        )
    rows = [dict(x) for x in cur.fetchall()]
    rows = [r for r in rows if is_approved_row(r)]
    con.close()
    return rows


def fetch_all(limit: int | None = None, offset: int | None = None) -> list[dict[str, Any]]:
    con = _getconn()
    cur = con.cursor()
    base = (
        f"SELECT * FROM {TABLE_NAME} "  # noqa: S608  # nosec
        "ORDER BY datetime(created_at) DESC, id DESC"
    )
    try:
        if limit is not None and offset is not None:
            cur.execute(base + " LIMIT ? OFFSET ?", (limit, offset))
        else:
            cur.execute(base)
    except sqlite3.OperationalError:
        fallback = f"SELECT * FROM {TABLE_NAME} ORDER BY id DESC"  # noqa: S608  # nosec
        if limit is not None and offset is not None:
            cur.execute(fallback + " LIMIT ? OFFSET ?", (limit, offset))
        else:
            cur.execute(fallback)
    rows = [normalize_row(x) for x in cur.fetchall()]
    rows = [r for r in rows if is_approved_row(r)]
    con.close()
    return rows


def fetch_count(where_sql: str = "", params: tuple[Any, ...] = ()) -> int:
    con = _getconn()
    cur = con.cursor()
    base = f"SELECT COUNT(*) AS c FROM {TABLE_NAME}"  # noqa: S608  # nosec
    if REQUIRE_APPROVED_ONLY and _HAS_STATUS and "status" not in where_sql:
        joiner = " WHERE " if "WHERE" not in where_sql.upper() else " AND "
        where_sql = (where_sql or "") + f"{joiner}status = ?"
        params = tuple(list(params) + ["approved"])
    sql = base + " " + where_sql if where_sql else base
    cur.execute(sql, params)
    c = cur.fetchone()[0]
    con.close()
    return int(c)


def fetch_one(sid: int) -> dict[str, Any]:
    con = _getconn()
    cur = con.cursor()
    # TABLE_NAME is trusted configuration; id param is bound
    cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE id= ?", (sid,))  # nosec
    r = cur.fetchone()
    con.close()
    if not r:
        raise LookupError("not_found")
    return normalize_row(r)


def fetch_by_category_slug(
    slug: str, limit: int | None = None, offset: int | None = None
) -> list[dict[str, Any]]:
    """Return approved rows for a given category slug with optional paging.

    Raises
    ------
    LookupError
        If the slug is unknown.
    """
    if slug not in CATS:
        raise LookupError("not_found")
    all_rows = fetch_all()
    filtered = [r for r in all_rows if category_to_slug(r.get("category", "")) == slug]
    if limit is not None and offset is not None:
        return filtered[offset : offset + limit]
    return filtered


def fetch_count_by_slug(slug: str) -> int:
    """Count approved rows for a given category slug."""
    if slug not in CATS:
        return 0
    rows = fetch_all_basic_categories()
    return sum(1 for r in rows if category_to_slug(r.get("category", "")) == slug)


__all__ = [
    "normalize_row",
    "fetch_all_basic_categories",
    "fetch_all",
    "fetch_count",
    "fetch_one",
    "fetch_by_category_slug",
    "fetch_count_by_slug",
    "insert_scenario",
]


def insert_scenario(data: dict[str, Any], owner: str = "web", pending: bool = True) -> int:
    """Insert a new scenario into the configured table.

    Parameters
    ----------
    data : dict[str, Any]
        Scenario fields. Must include at least "title" and "category". Optional
        JSON-like fields (lists) will be serialized according to JSON_FIELDS.
    owner : str, default "web"
        Logical owner/creator to store in the DB.
    pending : bool, default True
        If the schema contains a "status" column, and this flag is True, the
        row will be inserted with status="pending".

    Returns
    -------
    int
        The row id of the inserted scenario.

    Raises
    ------
    ValueError
        If required fields are missing or invalid, or on uniqueness violation.

    Notes
    -----
    - This function is schema-aware: it detects optional columns ("status",
      "approved_by") and includes them only if present in the DB.
    - Table name is trusted from configuration; values are parameterized.
    """
    title = (data.get("title") or "").strip()
    category = (data.get("category") or "").strip()
    if not title:
        raise ValueError("title is required")
    if not category:
        raise ValueError("category is required")

    if category_to_slug(category) not in CATS:
        raise ValueError("unknown category")

    con = _getconn()
    cur = con.cursor()

    # Build insert statement dynamically based on available columns
    cols: list[str] = [
        "bundle_id",
        "external_id",
        "title",
        "category",
        "threat_level",
        "likelihood",
        "complexity",
        "location",
        "background",
        "steps",
        "required_response",
        "debrief_points",
        "operational_background",
        "media_link",
        "mask_usage",
        "authority_notes",
        "cctv_usage",
        "comms",
        "decision_points",
        "escalation_conditions",
        "end_state_success",
        "end_state_failure",
        "lessons_learned",
        "variations",
        "validation",
        "owner",
        # approved_by and status are optional (schema-dependent)
    ]

    vals: list[Any] = [
        data.get("bundle_id", ""),
        data.get("external_id", ""),
        title,
        category,
        data.get("threat_level", ""),
        data.get("likelihood", ""),
        data.get("complexity", ""),
        data.get("location", ""),
        data.get("background", ""),
        json.dumps(data.get("steps", []), ensure_ascii=False),
        json.dumps(data.get("required_response", []), ensure_ascii=False),
        json.dumps(data.get("debrief_points", []), ensure_ascii=False),
        data.get("operational_background", ""),
        data.get("media_link", ""),
        data.get("mask_usage", ""),
        data.get("authority_notes", ""),
        data.get("cctv_usage", ""),
        json.dumps(data.get("comms", []), ensure_ascii=False),
        json.dumps(data.get("decision_points", []), ensure_ascii=False),
        json.dumps(data.get("escalation_conditions", []), ensure_ascii=False),
        data.get("end_state_success", ""),
        data.get("end_state_failure", ""),
        json.dumps(data.get("lessons_learned", []), ensure_ascii=False),
        json.dumps(data.get("variations", []), ensure_ascii=False),
        json.dumps(data.get("validation", []), ensure_ascii=False),
        owner,
    ]

    if db_has_column(TABLE_NAME, "approved_by"):
        cols.append("approved_by")
        vals.append("")
    if db_has_column(TABLE_NAME, "status"):
        cols.append("status")
        vals.append("pending" if pending else "approved")

    cols.append("created_at")
    vals.append(datetime.now().isoformat())

    placeholders = ", ".join(["?"] * len(vals))
    sql = (
        f"INSERT INTO {TABLE_NAME} (" + ", ".join(cols) + ") VALUES (" + placeholders + ")"
    )  # noqa: S608  # nosec B608

    try:
        cur.execute(sql, tuple(vals))
        con.commit()
    except sqlite3.IntegrityError as e:
        # Likely UNIQUE(title) violation, expose a clean error
        con.rollback()
        raise ValueError("scenario already exists") from e
    finally:
        # lastrowid is still accessible after commit
        new_id = int(cur.lastrowid or 0)
        con.close()
    return new_id

from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, jsonify, request
from flask.typing import ResponseReturnValue

from config import TABLE_NAME
from tatlam.core.categories import CATS
from tatlam.infra import repo
from tatlam.infra.db import get_db
from tatlam.infra.repo import db_has_column
from tatlam.web.middleware import rate_limit

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@bp.get("/scenarios")
@rate_limit(120, 60)
def scenarios() -> ResponseReturnValue:
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size

    q = (request.args.get("q") or "").strip()
    con = get_db()
    cur = con.cursor()
    where_parts: list[str] = []
    params: list[Any] = []
    # Evaluate gating at request time to respect test env changes
    from importlib import import_module as _imp

    cfg = _imp("config")
    if cfg.REQUIRE_APPROVED_ONLY and db_has_column(TABLE_NAME, "status"):
        where_parts.append("status = ?")
        params.append("approved")
    if q:
        where_parts.append("(title LIKE ? OR category LIKE ? OR location LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    total = repo.fetch_count(where, tuple(params))

    sql = (
        f"SELECT * FROM {TABLE_NAME} "  # noqa: S608  # nosec
        + where
        + " ORDER BY datetime(created_at) DESC, id DESC LIMIT ? OFFSET ?"
    )
    cur.execute(sql, (*params, page_size, offset))
    rows = [repo.normalize_row(x) for x in cur.fetchall()]
    con.close()

    return jsonify(
        {
            "items": rows,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }
    )


@bp.get("/scenario/<int:sid>")
@rate_limit(120, 60)
def scenario_one(sid: int) -> ResponseReturnValue:
    return jsonify(repo.fetch_one(sid))


@bp.get("/cat/<slug>.json")
@rate_limit(120, 60)
def category(slug: str) -> ResponseReturnValue:
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size
    if slug not in CATS:
        abort(404)
    total = repo.fetch_count_by_slug(slug)
    rows = repo.fetch_by_category_slug(slug, limit=page_size, offset=offset)
    return jsonify(
        {
            "items": rows,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }
    )


@bp.post("/scenarios")
@rate_limit(30, 60)
def create_scenario() -> ResponseReturnValue:
    """Create a new scenario via JSON API.

    Body JSON must include at least "title" and "category". Optional list
    fields (e.g., steps) may be provided. New records are inserted as pending
    when a "status" column exists; otherwise visibility is gated by
    "approved_by" remaining empty.
    """
    payload = request.get_json(silent=True) or {}
    try:
        new_id = repo.insert_scenario(payload, owner=payload.get("owner", "web"), pending=True)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"id": new_id, "status": "pending"}), 201


__all__ = ["bp"]

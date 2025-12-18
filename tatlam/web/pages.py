from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue

from tatlam.infra import repo

bp = Blueprint("pages", __name__)


@bp.get("/")
def home() -> ResponseReturnValue:
    app_mod = import_module("app")
    counts = {slug: repo.fetch_count_by_slug(slug) for slug in app_mod.CATS}
    cats = [
        {"slug": slug, "title": meta["title"], "count": counts[slug]}
        for slug, meta in app_mod.CATS.items()
    ]
    return cast("ResponseReturnValue", app_mod.render_with_fallback("home.html", cats=cats))


@bp.get("/all")
def all_items() -> ResponseReturnValue:
    app_mod = import_module("app")
    rows = repo.fetch_all()
    q = (request.args.get("q") or "").strip()
    if q:
        ql = q.lower()

        def _hit(r: dict[str, object]) -> bool:
            for key in ("title", "category", "location", "background"):
                v = (r.get(key) or "") if isinstance(r.get(key), str) else ""
                if isinstance(v, str) and ql in v.lower():
                    return True
            return False

        rows = [r for r in rows if _hit(r)]
    return cast(
        "ResponseReturnValue",
        app_mod.render_with_fallback(
            "list.html",
            cat_title="כל התטל״מים",
            items=rows,
            page=1,
            pages=1,
            total=len(rows),
        ),
    )


@bp.get("/cat/<slug>")
def by_cat(slug: str) -> ResponseReturnValue:
    app_mod = import_module("app")
    if slug not in app_mod.CATS:
        from flask import abort

        abort(404)
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size
    total = repo.fetch_count_by_slug(slug)
    rows = repo.fetch_by_category_slug(slug, limit=page_size, offset=offset)
    pages = (total + page_size - 1) // page_size
    if not rows:
        from flask import current_app

        current_app.logger.info("/cat/%s empty after filter; total rows=%d", slug, total)
    return cast(
        "ResponseReturnValue",
        app_mod.render_with_fallback(
            "list.html",
            cat_title=app_mod.CATS[slug]["title"],
            items=rows,
            page=page,
            pages=pages,
            total=total,
        ),
    )


@bp.get("/scenario/<int:sid>")
def scenario(sid: int) -> ResponseReturnValue:
    app_mod = import_module("app")
    row = repo.fetch_one(sid)
    return cast("ResponseReturnValue", app_mod.render_with_fallback("detail.html", s=row))


@bp.get("/dbg/echo")
def dbg_echo() -> ResponseReturnValue:
    return jsonify(
        {
            "remote_addr": request.remote_addr,
            "host": request.host,
            "method": request.method,
            "path": request.path,
            "headers": {k: v for k, v in request.headers.items()},
        }
    )


@bp.get("/dbg/config")
def dbg_config() -> ResponseReturnValue:
    app_mod = import_module("app")
    return jsonify(app_mod.describe_effective_config())


@bp.get("/dbg/cats_snapshot")
def dbg_cats_snapshot() -> ResponseReturnValue:
    """Snapshot of categories in DB with normalization and known CATS metadata."""
    app_mod = import_module("app")
    from tatlam.infra.db import get_db

    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT DISTINCT category FROM {app_mod.TABLE_NAME}"  # noqa: S608 (table name trusted)  # nosec B608
        )
    except Exception as e:  # pragma: no cover - defensive
        return jsonify({"error": str(e)}), 500
    raw = [r[0] for r in cur.fetchall()]
    con.close()

    data = []
    for v in raw:
        data.append(
            {
                "raw": v,
                "normalized": app_mod.normalize_hebrew(v),
                "slug": app_mod.category_to_slug(v),
            }
        )
    cats = {
        slug: {"title": meta["title"], "aliases": meta["aliases"]}
        for slug, meta in app_mod.CATS.items()
    }
    return jsonify({"db_categories": data, "cats": cats})


__all__ = ["bp"]


@bp.get("/submit")
def submit_form() -> ResponseReturnValue:
    """Show a minimal form for submitting a new Tatlam scenario (pending)."""
    app_mod = import_module("app")
    cats = [(slug, meta["title"]) for slug, meta in app_mod.CATS.items()]
    return render_template("submit.html", cats=cats)


@bp.post("/submit")
def submit_post() -> ResponseReturnValue:
    """Handle form submission of a new scenario.

    Converts multiline text areas (e.g., steps) into lists and stores a new
    pending record. On success, redirects to a small thank-you page.
    """
    from tatlam.core.categories import CATS
    from tatlam.infra import repo

    title = (request.form.get("title") or "").strip()
    category = (request.form.get("category") or "").strip()
    if not title or not category:
        return (
            render_template(
                "submit.html",
                cats=[(slug, meta["title"]) for slug, meta in CATS.items()],
                error="חובה למלא כותרת וקטגוריה",
                form=request.form,
            ),
            400,
        )

    def to_list(key: str) -> list[str]:
        raw = (request.form.get(key) or "").strip()
        return [line.strip() for line in raw.splitlines() if line.strip()]

    payload: dict[str, Any] = {
        "title": title,
        "category": category,
        "threat_level": (request.form.get("threat_level") or "").strip(),
        "likelihood": (request.form.get("likelihood") or "").strip(),
        "complexity": (request.form.get("complexity") or "").strip(),
        "location": (request.form.get("location") or "").strip(),
        "background": (request.form.get("background") or "").strip(),
        "steps": to_list("steps"),
        "required_response": to_list("required_response"),
        "debrief_points": to_list("debrief_points"),
    }
    try:
        new_id = repo.insert_scenario(payload, owner="web", pending=True)
    except ValueError as e:
        return (
            render_template(
                "submit.html",
                cats=[(slug, meta["title"]) for slug, meta in CATS.items()],
                error=str(e),
                form=request.form,
            ),
            400,
        )

    return redirect(url_for("pages.submit_thanks", sid=new_id))


@bp.get("/submit/thanks/<int:sid>")
def submit_thanks(sid: int) -> ResponseReturnValue:
    return render_template("submit.html", success_sid=sid)

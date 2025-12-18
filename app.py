from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    render_template,
    render_template_string,
    request,
)
from jinja2 import TemplateNotFound
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from config import (
    DB_PATH,
    FLASK_SECRET_KEY,
    REQUIRE_APPROVED_ONLY,
    TABLE_NAME,
    describe_effective_config,
)
from tatlam import CATS, category_to_slug, configure_logging, normalize_hebrew
from tatlam.infra.db import get_db
from tatlam.web.admin import init_admin
from tatlam.web.api import make_legacy_api_bp, v1_bp as api_v1_bp
from tatlam.web.errors import init_error_handlers
from tatlam.web.health import bp as health_bp
from tatlam.web.middleware import init_middleware, rate_limit
from tatlam.web.pages import bp as pages_bp

configure_logging()

app = Flask(__name__)
# Use a stable secret key from config/.env (avoid random key on reload)
app.secret_key = FLASK_SECRET_KEY or ("dev-" + os.urandom(24).hex())
# Log effective config once on startup to help troubleshooting
app.logger.info("[CONFIG] %s", describe_effective_config())

# Register blueprints (modular web separation)
app.register_blueprint(health_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(api_v1_bp)
app.register_blueprint(make_legacy_api_bp())
init_error_handlers(app)

init_middleware(app)

app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # local dev
    JSON_AS_ASCII=False,
)

# חיבור ל-SQLite (אין שרת חיצוני)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Base = automap_base()
Base.prepare(autoload_with=engine)
session = Session(engine)

# ---- Status constants (workflow gating)
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


def db_has_column(table: str, col: str) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as _c:
            cur = _c.cursor()
            cur.execute(f"PRAGMA table_info({table})")  # nosec B608
            return any(r[1] == col for r in cur.fetchall())
    except Exception:  # pragma: no cover - defensive
        return False


_HAS_STATUS = db_has_column(TABLE_NAME, "status")


def is_approved_row(row: dict[str, Any]) -> bool:
    if not REQUIRE_APPROVED_ONLY:
        return True
    if _HAS_STATUS:
        return (row.get("status") or "").strip().lower() == STATUS_APPROVED
    ab = (row.get("approved_by") or "").strip().lower()
    return ab in {"admin", "human", "approved", "manager"}


# Admin (reflect table, optional status column)
admin = init_admin(app, Base, session, TABLE_NAME, _HAS_STATUS)


@app.route("/dbg/cats_snapshot")
@rate_limit(60, 60)
def dbg_cats_snapshot():
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT DISTINCT category FROM {TABLE_NAME}"  # noqa: S608
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
                "normalized": normalize_hebrew(v),
                "slug": category_to_slug(v),
            }
        )
    cats = {
        slug: {"title": meta["title"], "aliases": meta["aliases"]} for slug, meta in CATS.items()
    }
    return jsonify({"db_categories": data, "cats": cats})


# Data access helpers
def fetch_all_basic_categories() -> list[dict[str, Any]]:
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT id, title, category, status, approved_by, created_at FROM {TABLE_NAME} "
            "ORDER BY datetime(created_at) DESC, id DESC"
        )
    except sqlite3.OperationalError:
        select_cols = ["id", "title", "category"]
        if db_has_column(TABLE_NAME, "status"):
            select_cols.append("status")
        if db_has_column(TABLE_NAME, "approved_by"):
            select_cols.append("approved_by")
        cur.execute(
            f"SELECT {', '.join(select_cols)} FROM {TABLE_NAME} ORDER BY id DESC"
        )
    rows = [dict(x) for x in cur.fetchall()]
    rows = [r for r in rows if is_approved_row(r)]
    con.close()
    return rows


JSON_FIELDS = [
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


def _parse_json_field(val: Any) -> list | dict:
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str) and not val.strip():
        return []
    try:
        return json.loads(val)
    except Exception:
        return []


def normalize_row(r: sqlite3.Row) -> dict[str, Any]:
    row = dict(r)
    for k in JSON_FIELDS:
        row[k] = _parse_json_field(row.get(k))
    return row


def render_with_fallback(template_name: str, **ctx: Any) -> str:
    try:
        return render_template(template_name, **ctx)
    except TemplateNotFound:
        if template_name == "home.html":
            cats = ctx.get("cats", [])
            html = ["<h1>קטגוריות</h1>", "<ul>"]
            for c in cats:
                html.append(
                    f"<li><a href='/cat/{c['slug']}'>{c['title']}</a> – {c['count']} תטל\"מים</li>"
                )
            html.append("</ul>")
            return "\n".join(html)
        if template_name == "list.html":
            items = ctx.get("items", [])
            title = ctx.get("cat_title", "קטגוריה")
            html = [f"<h1>{title}</h1>", "<ul>"]
            for s in items:
                part1 = (
                    f"<li><a href='/scenario/{s.get('id','')}'>{s.get('title','(ללא כותרת)')}</a>"
                )
                part2 = (
                    f" – {s.get('category','')} | {s.get('threat_level','?')}/"
                    f"{s.get('likelihood','?')}/{s.get('complexity','?')}</li>"
                )
                html.append(part1 + part2)
            html.append("</ul>")
            return "\n".join(html)
        if template_name == "detail.html":
            s = ctx.get("s", {})

            def li_list(key: str) -> str:
                val = s.get(key) or []
                out: list[str] = []
                for x in val:
                    content = (
                        json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x
                    )
                    out.append(f"<li>{content}</li>")
                return "".join(out)

            html = [
                f"<h2>{s.get('title','(ללא כותרת)')}</h2>",
                f"<p><b>קטגוריה:</b> {s.get('category','')}</p>",
                f"<p><b>מיקום:</b> {s.get('location','')}</p>",
                f"<p><b>רקע:</b> {s.get('background','')}</p>",
                "<h3>🧭 שלבים</h3>",
                f"<ol>{li_list('steps')}</ol>",
                "<h3>📢 הנחיות תגובה</h3>",
                f"<ul>{li_list('required_response')}</ul>",
                "<h3>📝 תחקור</h3>",
                f"<ul>{li_list('debrief_points')}</ul>",
            ]
            return "\n".join(html)
        return render_template_string("<pre>{{ ctx | tojson(indent=2) }}</pre>", ctx=ctx)


def fetch_all(limit: int | None = None, offset: int | None = None) -> list[dict]:
    con = get_db()
    cur = con.cursor()
    base = (
        f"SELECT * FROM {TABLE_NAME} "
        "ORDER BY datetime(created_at) DESC, id DESC"
    )
    try:
        if limit is not None and offset is not None:
            cur.execute(base + " LIMIT ? OFFSET ?", (limit, offset))
        else:
            cur.execute(base)
    except sqlite3.OperationalError:
        fallback = f"SELECT * FROM {TABLE_NAME} ORDER BY id DESC"
        if limit is not None and offset is not None:
            cur.execute(fallback + " LIMIT ? OFFSET ?", (limit, offset))
        else:
            cur.execute(fallback)
    rows = [normalize_row(x) for x in cur.fetchall()]
    rows = [r for r in rows if is_approved_row(r)]
    con.close()
    return rows


def fetch_count(where_sql: str = "", params: tuple = ()) -> int:
    con = get_db()
    cur = con.cursor()
    base = f"SELECT COUNT(*) AS c FROM {TABLE_NAME}"
    if REQUIRE_APPROVED_ONLY and _HAS_STATUS and "status" not in where_sql:
        joiner = " WHERE " if "WHERE" not in where_sql.upper() else " AND "
        where_sql = (where_sql or "") + f"{joiner}status = ?"
        params = tuple(list(params) + [STATUS_APPROVED])
    sql = base + " " + where_sql if where_sql else base
    cur.execute(sql, params)
    c = cur.fetchone()[0]
    con.close()
    return int(c)


def fetch_by_category_slug(
    slug: str, limit: int | None = None, offset: int | None = None
) -> list[dict]:
    if slug not in CATS:
        abort(404)
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT * FROM {TABLE_NAME} "
            "ORDER BY datetime(created_at) DESC, id DESC"
        )
    except sqlite3.OperationalError:
        cur.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY id DESC")
    all_rows = [normalize_row(x) for x in cur.fetchall()]
    con.close()

    filtered = []
    for r in all_rows:
        if is_approved_row(r) and category_to_slug(r.get("category")) == slug:
            filtered.append(r)

    if limit is not None and offset is not None:
        return filtered[offset : offset + limit]
    return filtered


def fetch_count_by_slug(slug: str) -> int:
    if slug not in CATS:
        return 0
    rows = fetch_all_basic_categories()
    c = 0
    for r in rows:
        if category_to_slug(r.get("category")) == slug:
            c += 1
    return c


def fetch_one(sid: int) -> dict:
    con = get_db()
    cur = con.cursor()
    cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE id= ?", (sid,))
    r = cur.fetchone()
    con.close()
    if not r:
        abort(404)
    return normalize_row(r)


# --- Views ---
@app.route("/")
def home():
    counts = {slug: fetch_count_by_slug(slug) for slug in CATS}
    cats = [
        {"slug": slug, "title": meta["title"], "count": counts[slug]} for slug, meta in CATS.items()
    ]
    return render_with_fallback("home.html", cats=cats)


@app.route("/all")
def all_items():
    rows = fetch_all()
    return render_with_fallback(
        "list.html",
        cat_title="כל התטל״מים",
        items=rows,
        page=1,
        pages=1,
        total=len(rows),
    )


@app.route("/cat/<slug>")
def by_cat(slug: str):
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size

    total = fetch_count_by_slug(slug)
    rows = fetch_by_category_slug(slug, limit=page_size, offset=offset)
    pages = (total + page_size - 1) // page_size

    if not rows:
        app.logger.info("/cat/%s empty after filter; total rows=%d", slug, total)

    return render_with_fallback(
        "list.html",
        cat_title=CATS[slug]["title"],
        items=rows,
        page=page,
        pages=pages,
        total=total,
    )


@app.route("/scenario/<int:sid>")
def scenario(sid: int):
    row = fetch_one(sid)
    return render_with_fallback("detail.html", s=row)


@app.route("/dbg/echo")
def dbg_echo():
    return jsonify(
        {
            "remote_addr": request.remote_addr,
            "host": request.host,
            "method": request.method,
            "path": request.path,
            "headers": {k: v for k, v in request.headers.items()},
        }
    )


@app.route("/dbg/config")
def dbg_config():
    return jsonify(describe_effective_config())


@app.route("/api/scenarios")
@rate_limit(120, 60)
def api_all():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size

    q = (request.args.get("q") or "").strip()

    con = get_db()
    cur = con.cursor()
    where_parts: list[str] = []
    params: list[Any] = []
    if REQUIRE_APPROVED_ONLY and _HAS_STATUS:
        where_parts.append("status = ?")
        params.append(STATUS_APPROVED)
    if q:
        where_parts.append("(title LIKE ? OR category LIKE ? OR location LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    where = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    total = fetch_count(where, tuple(params))

    sql = (
        f"SELECT * FROM {TABLE_NAME} "
        + where
        + " ORDER BY datetime(created_at) DESC, id DESC LIMIT ? OFFSET ?"
    )
    cur.execute(sql, (*params, page_size, offset))
    rows = [normalize_row(x) for x in cur.fetchall()]
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


@app.route("/api/scenario/<int:sid>")
@rate_limit(120, 60)
def api_one(sid: int):
    return jsonify(fetch_one(sid))


@app.route("/api/cat/<slug>.json")
@rate_limit(120, 60)
def api_cat(slug: str):
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size

    if slug not in CATS:
        abort(404)
    all_rows = fetch_all()
    total = sum(1 for r in all_rows if category_to_slug(r.get("category")) == slug)
    rows = fetch_by_category_slug(slug, limit=page_size, offset=offset)

    return jsonify(
        {
            "items": rows,
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": (total + page_size - 1) // page_size,
        }
    )


@app.route("/events")
@rate_limit(60, 60)
def events():
    def stream():
        path = DB_PATH
        last = None
        ticks = 0
        while True:
            try:
                m = os.path.getmtime(path)
            except FileNotFoundError:
                m = 0
            if last is None:
                last = m
            elif m != last:
                last = m
                yield f"data: {m}\n\n"
            ticks += 1
            if ticks % 8 == 0:
                yield ": heartbeat\n\n"
            time.sleep(2)

    resp = Response(stream(), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@app.errorhandler(403)
def forbidden(e):  # type: ignore[override]
    if request.path.startswith("/api/"):
        return jsonify({"error": "forbidden"}), 403
    return (
        render_template_string(
            """
        <h1>403 – Forbidden</h1>
        <p>הבקשה נחסמה. אם דף זה מופיע, החסימה מגיעה מהאפליקציה עצמה.</p>
        <p>Host: {{host}} | Path: {{path}}</p>
        """,
            host=request.host,
            path=request.path,
        ),
        403,
    )


@app.errorhandler(404)
def not_found(e):  # type: ignore[override]
    if request.path.startswith("/api/"):
        return jsonify({"error": "not_found"}), 404
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal(e):  # type: ignore[override]
    if request.path.startswith("/api/"):
        return jsonify({"error": "internal_error"}), 500
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run()

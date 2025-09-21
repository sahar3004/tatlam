from __future__ import annotations

import json
import os
import sqlite3
import time
from functools import wraps
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
from flask_admin import Admin, AdminIndexView
from flask_admin.actions import action
from flask_admin.contrib.sqla import ModelView
from jinja2 import TemplateNotFound
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from wtforms import TextAreaField

from config import (
    DB_PATH,
    FLASK_SECRET_KEY,
    REQUIRE_APPROVED_ONLY,
    TABLE_NAME,
    describe_effective_config,
)
from tatlam import CATS, category_to_slug, configure_logging, normalize_hebrew

configure_logging()

app = Flask(__name__)
# Use a stable secret key from config/.env (avoid random key on reload)
app.secret_key = FLASK_SECRET_KEY or ("dev-" + os.urandom(24).hex())
# Log effective config once on startup to help troubleshooting
app.logger.info("[CONFIG] %s", describe_effective_config())


# --- Debug logging (helps to diagnose 403/other issues) ---
@app.before_request
def _log_request() -> None:
    """Log the incoming request in a structured, low-overhead manner."""
    try:
        app.logger.info(
            "REQ ip=%s host=%s method=%s path=%s ua=%s",
            request.remote_addr,
            request.host,
            request.method,
            request.path,
            request.headers.get("User-Agent", ""),
        )
    except Exception:  # noqa: BLE001 - defensive logging
        app.logger.exception("request logging failed")


@app.after_request
def _log_response(resp: Response) -> Response:
    try:
        app.logger.info("RES %s %s -> %s", request.method, request.path, resp.status)
    except Exception:  # noqa: BLE001 - defensive logging
        app.logger.exception("response logging failed")
    return resp


app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,  # לפיתוח מקומי
    JSON_AS_ASCII=False,
)


# --- Security headers ---
@app.after_request
def set_security_headers(resp: Response) -> Response:
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    # CSP שמרני לפיתוח; עדכן לפי צרכי ה-templates שלך
    csp_parts = [
        "default-src 'self'",
        "img-src 'self' data:",
        "style-src 'self' 'unsafe-inline'",
        "script-src 'self' 'unsafe-inline'",
    ]
    resp.headers.setdefault("Content-Security-Policy", "; ".join(csp_parts))
    return resp


# --- Simple in-memory rate limiter (per-IP per endpoint) ---
_RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}


def rate_limit(max_calls: int = 60, per_seconds: int = 60):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            now = time.time()
            key = (request.remote_addr or "127.0.0.1", request.endpoint or fn.__name__)
            bucket = _RATE_BUCKETS.setdefault(key, [])
            cutoff = now - float(per_seconds)
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= max_calls:
                return (jsonify({"error": "rate_limited"}), 429)
            bucket.append(now)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


# חיבור ל-SQLite (אין שרת חיצוני)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
Base = automap_base()
# SQLAlchemy 2.x: העדפה ל-autoload_with
Base.prepare(autoload_with=engine)
session = Session(engine)

# ---- Status constants (workflow gating)
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


# ---- Helpers: DB column detection + approval logic
def db_has_column(table: str, col: str) -> bool:
    try:
        with sqlite3.connect(DB_PATH) as _c:
            cur = _c.cursor()
            cur.execute(f"PRAGMA table_info({table})")  # nosec B608: table name is trusted
            return any(r[1] == col for r in cur.fetchall())
    except Exception:  # noqa: BLE001 - defensive fallback
        return False


_HAS_STATUS = db_has_column(TABLE_NAME, "status")


def is_approved_row(row: dict) -> bool:
    if not REQUIRE_APPROVED_ONLY:
        return True
    if _HAS_STATUS:
        return (row.get("status") or "").strip().lower() == STATUS_APPROVED
    # Fallback when there is no 'status' column:
    # treat only explicitly human-approved as approved; 'Gold' is NOT auto-approval
    ab = (row.get("approved_by") or "").strip().lower()
    return ab in {"admin", "human", "approved", "manager"}


# --- Admin security (basic auth via is_accessible) ---
ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")


class SecureIndex(AdminIndexView):
    def is_accessible(self) -> bool:  # type: ignore[override]
        auth = request.authorization
        if not ADMIN_USER or not ADMIN_PASS:
            # אם לא הוגדר – אל תנעל בסביבה מקומית
            return True
        return auth and auth.username == ADMIN_USER and auth.password == ADMIN_PASS

    def inaccessible_callback(self, name, **kwargs):  # type: ignore[override]
        return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Admin"'})


class ScenarioAdmin(ModelView):
    # הפוך שדות טקסט ארוכים לנוחים לעריכה
    form_overrides = {
        "background": TextAreaField,
        "rules_of_engagement": TextAreaField,
        "operational_background": TextAreaField,
        "cctv_usage": TextAreaField,
        "authority_notes": TextAreaField,
        "end_state_success": TextAreaField,
        "end_state_failure": TextAreaField,
    }
    form_widget_args = {
        "background": {"rows": 6},
        "rules_of_engagement": {"rows": 5},
        "operational_background": {"rows": 4},
        "cctv_usage": {"rows": 3},
        "authority_notes": {"rows": 3},
        "end_state_success": {"rows": 3},
        "end_state_failure": {"rows": 3},
    }

    page_size = 20
    can_view_details = True
    column_list = (
        "id",
        "title",
        "category",
        "location",
        "threat_level",
        "likelihood",
        "complexity",
        "owner",
        "approved_by",
        "status",
        "created_at",
    )
    column_default_sort = ("id", True)
    column_searchable_list = ["title", "category", "location"]
    column_filters = ["category", "threat_level", "likelihood", "complexity"]

    def is_accessible(self) -> bool:  # type: ignore[override]
        auth = request.authorization
        if not ADMIN_USER or not ADMIN_PASS:
            return True
        return auth and auth.username == ADMIN_USER and auth.password == ADMIN_PASS

    def inaccessible_callback(self, name, **kwargs):  # type: ignore[override]
        return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="Admin"'})

    @action("approve", "אשר ופרסם", "לאשר את הפריטים שנבחרו?")
    def action_approve(self, ids):
        q = self.session.query(self.model).filter(self.model.id.in_(ids))
        count = 0
        for obj in q.all():
            if _HAS_STATUS and hasattr(obj, "status"):
                obj.status = STATUS_APPROVED  # type: ignore[attr-defined]
            if hasattr(obj, "approved_by"):
                try:
                    current = (obj.approved_by or "").strip()  # type: ignore[attr-defined]
                except Exception:
                    current = ""
                if not current:
                    obj.approved_by = "Admin"  # type: ignore[attr-defined]
            count += 1
        self.session.commit()
        self.flash(f"אושרו {count} פריטים", "success")

    @action("to_pending", "החזר ל‑Pending", "להחזיר את הפריטים שנבחרו למצב Pending?")
    def action_to_pending(self, ids):
        q = self.session.query(self.model).filter(self.model.id.in_(ids))
        count = 0
        for obj in q.all():
            if _HAS_STATUS and hasattr(obj, "status"):
                obj.status = STATUS_PENDING  # type: ignore[attr-defined]
            if hasattr(obj, "approved_by"):
                obj.approved_by = ""  # type: ignore[attr-defined]
            count += 1
        self.session.commit()
        self.flash(f"עודכנו {count} פריטים ל‑Pending", "info")


# --- Pending admin view ---
class PendingAdmin(ScenarioAdmin):
    def is_visible(self):
        # Show in the menu
        return True

    def get_query(self):
        q = super().get_query()
        if _HAS_STATUS and hasattr(self.model, "status"):
            return q.filter(self.model.status == STATUS_PENDING)  # type: ignore[attr-defined]
        # Fallback: items without explicit human approval considered pending
        if hasattr(self.model, "approved_by"):
            col = self.model.approved_by  # type: ignore[attr-defined]
            return q.filter((col.is_(None)) | (col == ""))
        return q

    def get_count_query(self):
        q = super().get_count_query()
        if _HAS_STATUS and hasattr(self.model, "status"):
            return q.filter(self.model.status == STATUS_PENDING)  # type: ignore[attr-defined]
        if hasattr(self.model, "approved_by"):
            col = self.model.approved_by  # type: ignore[attr-defined]
            return q.filter((col.is_(None)) | (col == ""))
        return q


admin = Admin(app, name="Tatlam Admin", template_mode="bootstrap4", index_view=SecureIndex())

try:
    Scenarios = getattr(Base.classes, TABLE_NAME)
    # Register Pending first so it appears as /admin/pending
    admin.add_view(PendingAdmin(Scenarios, session, name="Pending", endpoint="pending"))
    admin.add_view(ScenarioAdmin(Scenarios, session, name="Scenarios", endpoint="scenarios"))
except Exception as e:
    app.logger.warning(
        "[ADMIN] failed to reflect table %s: %s. ensure DB exists; "
        "'status' column is optional but recommended",
        TABLE_NAME,
        e,
    )

# --- קטגוריות ותאימות שמות ---


@app.route("/dbg/cats_snapshot")
@rate_limit(60, 60)
def dbg_cats_snapshot():
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT DISTINCT category FROM {TABLE_NAME}"  # noqa: S608 (table name trusted)
        )
    except Exception as e:
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
    # also include known slugs/titles for reference
    cats = {
        slug: {"title": meta["title"], "aliases": meta["aliases"]} for slug, meta in CATS.items()
    }
    return jsonify({"db_categories": data, "cats": cats})


# --- Data access helpers ---


def fetch_all_basic_categories() -> list[dict]:
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT id, title, category, created_at FROM {TABLE_NAME} "  # noqa: S608
            "ORDER BY datetime(created_at) DESC, id DESC"
        )
    except sqlite3.OperationalError:
        cur.execute(f"SELECT id, title, category FROM {TABLE_NAME} ORDER BY id DESC")  # noqa: S608
    rows = [dict(x) for x in cur.fetchall()]
    # gate: only approved rows are visible in public listing
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


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


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


# --- Rendering helpers with HTML fallback if templates are missing ---


def render_with_fallback(template_name: str, **ctx: Any) -> str:
    try:
        return render_template(template_name, **ctx)
    except TemplateNotFound:
        # Minimal HTML fallback for development if Jinja templates are missing
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

            # Safely render core fields and common lists
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
        # Default debug dump
        return render_template_string("<pre>{{ ctx | tojson(indent=2) }}</pre>", ctx=ctx)


# --- Data access helpers ---


def fetch_all(limit: int | None = None, offset: int | None = None) -> list[dict]:
    con = get_db()
    cur = con.cursor()
    base = (
        f"SELECT * FROM {TABLE_NAME} "  # noqa: S608 (table name trusted)
        "ORDER BY datetime(created_at) DESC, id DESC"
    )
    try:
        if limit is not None and offset is not None:
            cur.execute(base + " LIMIT ? OFFSET ?", (limit, offset))
        else:
            cur.execute(base)
    except sqlite3.OperationalError:
        # Fallback if created_at doesn't exist or can't be casted
        fallback = f"SELECT * FROM {TABLE_NAME} ORDER BY id DESC"  # noqa: S608
        if limit is not None and offset is not None:
            cur.execute(fallback + " LIMIT ? OFFSET ?", (limit, offset))
        else:
            cur.execute(fallback)
    rows = [normalize_row(x) for x in cur.fetchall()]
    rows = [r for r in rows if is_approved_row(r)]
    con.close()
    return rows


def fetch_count(where_sql: str = "", params: tuple = ()) -> int:  # for pagination
    con = get_db()
    cur = con.cursor()
    base = f"SELECT COUNT(*) AS c FROM {TABLE_NAME}"  # noqa: S608
    # ensure approved filter when status exists and caller didn't pass one
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
    # Pull rows ordered (created_at desc fallback id desc) and filter by normalized category
    con = get_db()
    cur = con.cursor()
    try:
        cur.execute(
            f"SELECT * FROM {TABLE_NAME} "  # noqa: S608
            "ORDER BY datetime(created_at) DESC, id DESC"
        )
    except sqlite3.OperationalError:
        cur.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY id DESC")  # noqa: S608
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
    cur.execute(f"SELECT * FROM {TABLE_NAME} WHERE id= ?", (sid,))  # noqa: S608
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
def by_cat(slug):
    if slug not in CATS:
        abort(404)
    # pagination
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
    # Returns request info to help troubleshoot proxies / 403, etc.
    return jsonify(
        {
            "remote_addr": request.remote_addr,
            "host": request.host,
            "method": request.method,
            "path": request.path,
            "headers": {k: v for k, v in request.headers.items()},
        }
    )


# Debug endpoint to inspect effective config (useful in dev)
@app.route("/dbg/config")
def dbg_config():
    return jsonify(describe_effective_config())


# --- JSON API ---
@app.route("/api/scenarios")
@rate_limit(120, 60)
def api_all():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size

    # חיפוש חופשי בסיסי בכותרת/קטגוריה/מיקום
    q = (request.args.get("q") or "").strip()

    con = get_db()
    cur = con.cursor()
    where_parts = []
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
        f"SELECT * FROM {TABLE_NAME} "  # noqa: S608
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
    # pagination params to keep JSON /cat similar to HTML /cat
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 50)), 1), 200)
    offset = (page - 1) * page_size

    if slug not in CATS:
        abort(404)
    # Count via Python normalization to match the same logic as HTML view
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


# --- SSE for live refresh when DB file changes ---
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
                # heartbeat keeps the SSE connection alive
                yield ": heartbeat\n\n"
            time.sleep(2)

    resp = Response(stream(), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"  # disable proxy buffering (nginx)
    return resp


# --- Health / Readiness ---
@app.route("/health")
def health():
    db_file = os.path.exists(DB_PATH)
    db_query = False
    try:
        con = get_db()
        con.execute("SELECT 1")
        con.close()
        db_query = True
    except Exception:
        db_query = False
    return jsonify({"ok": True, "db_file": db_file, "db_query": db_query})


@app.route("/healthz/ready")
def ready():
    ok = True
    msgs = []

    if not os.path.exists(DB_PATH):
        ok = False
        msgs.append("db_file_missing")
    else:
        try:
            with get_db() as con:
                cur = con.cursor()
                # verify table exists
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (TABLE_NAME,),
                )
                if not cur.fetchone():
                    ok = False
                    msgs.append("table_missing")
                else:
                    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")  # noqa: S608
                    count = cur.fetchone()[0]
                    msgs.append(f"rows={count}")
        except Exception as e:
            ok = False
            msgs.append(f"db_error={e}")

    status = 200 if ok else 503
    return jsonify({"ready": ok, "checks": msgs}), status


@app.errorhandler(403)
def forbidden(e):  # type: ignore[override]
    if request.path.startswith("/api/"):
        return jsonify({"error": "forbidden"}), 403
    # Show a small HTML with a hint when 403 happens, to distinguish Flask vs external block
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


# --- Error handlers (JSON for /api, HTML otherwise) ---
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
    # Development server (do not enable debug flag in production)
    app.run()

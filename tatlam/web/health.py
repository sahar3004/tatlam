from __future__ import annotations

import os

from flask import Blueprint, jsonify
from flask.typing import ResponseReturnValue

from config import DB_PATH, TABLE_NAME
from tatlam.infra.db import get_db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health() -> ResponseReturnValue:
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


@bp.get("/healthz/ready")
def ready() -> ResponseReturnValue:
    ok = True
    msgs: list[str] = []

    if not os.path.exists(DB_PATH):
        ok = False
        msgs.append("db_file_missing")
    else:
        try:
            with get_db() as con:
                cur = con.cursor()
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (TABLE_NAME,),
                )
                if not cur.fetchone():
                    ok = False
                    msgs.append("table_missing")
                else:
                    cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")  # noqa: S608  # nosec
                    count = cur.fetchone()[0]
                    msgs.append(f"rows={count}")
        except Exception as e:
            ok = False
            msgs.append(f"db_error={e}")

    status = 200 if ok else 503
    return jsonify({"ready": ok, "checks": msgs}), status


__all__ = ["bp"]

from __future__ import annotations

import os
import time
from collections.abc import Iterable

from flask import Blueprint, Response

from config import DB_PATH
from tatlam.web.middleware import rate_limit

bp = Blueprint("sse", __name__)


@bp.get("/events")
@rate_limit(60, 60)
def events() -> Response:
    def stream() -> Iterable[str]:
        path = DB_PATH
        last = 0.0
        first = True
        ticks = 0
        while True:
            try:
                m = os.path.getmtime(path)
            except FileNotFoundError:
                m = 0
            if not first and m != last:
                yield f"data: {m}\n\n"
            last = m
            first = False
            ticks += 1
            if ticks % 8 == 0:
                yield ": heartbeat\n\n"
            time.sleep(2)

    resp = Response(stream(), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["X-Accel-Buffering"] = "no"  # disable proxy buffering
    return resp


__all__ = ["bp"]

from __future__ import annotations

import time
import uuid
from functools import wraps
from typing import Any, Callable

from flask import Response, g, request

_RATE_BUCKETS: dict[tuple[str, str], list[float]] = {}


def rate_limit(
    max_calls: int = 60, per_seconds: int = 60
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            now = time.time()
            key = (request.remote_addr or "127.0.0.1", request.endpoint or fn.__name__)
            bucket = _RATE_BUCKETS.setdefault(key, [])
            cutoff = now - float(per_seconds)
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= max_calls:
                return ({"error": "rate_limited"}, 429)
            bucket.append(now)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def init_middleware(app: Any) -> None:
    @app.before_request  # type: ignore[misc]
    def _before() -> None:  # noqa: D401 - internal
        try:
            rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
            g.request_id = rid
            app.logger.info(
                "REQ id=%s ip=%s host=%s method=%s path=%s ua=%s",
                rid,
                request.remote_addr,
                request.host,
                request.method,
                request.path,
                request.headers.get("User-Agent", ""),
            )
        except Exception:  # pragma: no cover - defensive logging
            app.logger.exception("request logging failed")

    @app.after_request  # type: ignore[misc]
    def _after(resp: Response) -> Response:  # noqa: D401 - internal
        try:
            rid = getattr(g, "request_id", None)
            if rid:
                resp.headers.setdefault("X-Request-ID", rid)
            # Security headers
            resp.headers.setdefault("X-Content-Type-Options", "nosniff")
            resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
            resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
            # Conservative CSP for dev
            csp_parts = [
                "default-src 'self'",
                "img-src 'self' data:",
                "style-src 'self' 'unsafe-inline'",
                "script-src 'self' 'unsafe-inline'",
            ]
            resp.headers.setdefault("Content-Security-Policy", "; ".join(csp_parts))
            app.logger.info("RES id=%s %s %s -> %s", rid, request.method, request.path, resp.status)
        except Exception:  # pragma: no cover - defensive logging
            app.logger.exception("response logging failed")
        return resp


__all__ = ["rate_limit", "init_middleware"]

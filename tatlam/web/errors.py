from __future__ import annotations

from typing import Any

from flask import jsonify, render_template, render_template_string, request
from flask.typing import ResponseReturnValue


def init_error_handlers(app: Any) -> None:
    @app.errorhandler(403)  # type: ignore[misc]
    def forbidden(e: Exception) -> ResponseReturnValue:  # noqa: ARG001
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

    @app.errorhandler(404)  # type: ignore[misc]
    def not_found(e: Exception) -> ResponseReturnValue:  # noqa: ARG001
        if request.path.startswith("/api/"):
            return jsonify({"error": "not_found"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)  # type: ignore[misc]
    def internal(e: Exception) -> ResponseReturnValue:  # noqa: ARG001
        if request.path.startswith("/api/"):
            return jsonify({"error": "internal_error"}), 500
        return render_template("500.html"), 500


__all__ = ["init_error_handlers"]

from __future__ import annotations

import os
from typing import Any

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session

from config import FLASK_SECRET_KEY, TABLE_NAME, describe_effective_config
from tatlam import configure_logging
from tatlam.infra.repo import db_has_column
from tatlam.web.admin import init_admin
from tatlam.web.api import make_legacy_api_bp, v1_bp as api_v1_bp
from tatlam.web.errors import init_error_handlers
from tatlam.web.health import bp as health_bp
from tatlam.web.middleware import init_middleware
from tatlam.web.pages import bp as pages_bp
from tatlam.web.sse import bp as sse_bp


def create_app() -> Any:
    """Create and configure the Flask app instance (factory).

    - Configures logging and security headers
    - Registers blueprints (health, pages, API v1 + legacy, SSE)
    - Initializes error handlers and middleware
    - Wires up Admin based on reflected SQLite schema
    """
    configure_logging()

    app = Flask(__name__)
    app.secret_key = FLASK_SECRET_KEY or ("dev-" + os.urandom(24).hex())
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
        JSON_AS_ASCII=False,
    )
    app.logger.info("[CONFIG] %s", describe_effective_config())

    # Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(make_legacy_api_bp())
    app.register_blueprint(sse_bp)

    init_error_handlers(app)
    init_middleware(app)

    # Admin reflection over SQLite
    try:
        from config import DB_PATH

        engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
        Base = automap_base()
        Base.prepare(autoload_with=engine)
        session = Session(engine)
        init_admin(app, Base, session, TABLE_NAME, db_has_column(TABLE_NAME, "status"))
    except Exception as e:  # pragma: no cover - admin reflection may fail in CI without DB
        app.logger.warning("[ADMIN] init failed: %s", e)

    return app


__all__ = ["create_app"]

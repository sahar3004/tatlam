"""Centralised logging configuration for CLI tools and the Flask app.

Moved from `tatlam/logging_setup.py` as part of Phase 2 modularization.
The original module path re-exports the public API for compatibility.
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
from pathlib import Path
from typing import Any, cast

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _structured_formatter(record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
        "timestamp": record.created,
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
    }
    if record.exc_info:
        payload["exception"] = logging.Formatter().formatException(record.exc_info)
    for key, value in record.__dict__.items():
        if key.startswith("_"):
            continue
        if key in payload:
            continue
        try:
            json.dumps(value)
        except TypeError:
            payload[key] = repr(value)
        else:
            payload[key] = value
    return json.dumps(payload, ensure_ascii=False)


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - inherited docstring
        return _structured_formatter(record)


def configure_logging(*, structured: bool | None = None, level: str | None = None) -> None:
    """Configure logging once per process.

    Parameters
    ----------
    structured: bool | None
        When True emit JSON logs; default controlled by LOG_STRUCTURED env var.
    level: str | None
        Optional log level override (e.g. "DEBUG").
    """
    logger = logging.getLogger()
    if getattr(configure_logging, "_configured", False):
        if level:
            logger.setLevel(level)
        return

    structured = structured if structured is not None else os.getenv("LOG_STRUCTURED") == "1"
    effective_level = level or os.getenv("LOG_LEVEL", "INFO")
    formatter: logging.Formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        fmt = os.getenv("LOG_FORMAT", _DEFAULT_FORMAT)
        datefmt = os.getenv("LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "root": {
                "handlers": ["default"],
                "level": cast("int | str", effective_level),
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "structured" if structured else "default",
                }
            },
            "formatters": {
                "default": {
                    "()": "logging.Formatter",
                    "format": formatter._fmt if hasattr(formatter, "_fmt") else _DEFAULT_FORMAT,
                    "datefmt": getattr(formatter, "datefmt", "%Y-%m-%d %H:%M:%S"),
                },
                "structured": {"()": "tatlam.infra.logging.StructuredFormatter"},
            },
        }
    )

    configure_logging._configured = True  # type: ignore[attr-defined]

    log_path = os.getenv("LOG_FILE")
    if log_path:
        p = Path(log_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(p, encoding="utf-8")
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as exc:
            logger.warning("Failed to attach file handler %s: %s", log_path, exc)

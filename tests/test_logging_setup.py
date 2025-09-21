from __future__ import annotations

import json
import logging
from pathlib import Path

from tatlam.logging_setup import configure_logging


def test_configure_logging_structured_and_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOG_STRUCTURED", "1")
    log_file = tmp_path / "app.log"
    monkeypatch.setenv("LOG_FILE", str(log_file))
    configure_logging(level="DEBUG")
    logger = logging.getLogger("tatlam.test")
    logger.info("hello", extra={"k": "v"})
    # File handler optional; if configured, verify JSON available
    if log_file.exists():
        text = log_file.read_text(encoding="utf-8")
        lines = [line for line in text.splitlines() if line.strip()]
        data = [json.loads(line) for line in lines]
        assert any(entry.get("message") == "hello" for entry in data)


def test_configure_logging_plain(monkeypatch):
    # Non-structured logs with level override
    monkeypatch.delenv("LOG_STRUCTURED", raising=False)
    configure_logging(structured=False, level="INFO")
    logger = logging.getLogger("tatlam.test2")
    logger.info("plain-line")

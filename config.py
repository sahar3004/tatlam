"""
config.py - Compatibility shim for legacy imports

This module provides backward compatibility for code that imports from 'config'.
All configuration now lives in config_trinity.py.

This shim re-exports the necessary values and provides client factory functions
that were originally in the old config.py.
"""
from __future__ import annotations

import os
from openai import OpenAI

# Import from config_trinity (the single source of truth)
from config_trinity import (
    DB_PATH,
    TABLE_NAME,
    BASE_DIR,
    REQUIRE_APPROVED_ONLY,
    # Trinity models
    WRITER_MODEL_NAME,
    JUDGE_MODEL_NAME,
    LOCAL_MODEL_NAME,
    LOCAL_BASE_URL,
    LOCAL_API_KEY,
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
)

# ==== Legacy constants for backward compatibility ====

# Embeddings table name (not in config_trinity but needed by run_batch.py)
EMB_TABLE: str = os.getenv("EMB_TABLE", "title_embeddings")

# Model names (map Trinity models to legacy names)
LOCAL_MODEL: str = LOCAL_MODEL_NAME
GEN_MODEL: str = os.getenv("GEN_MODEL", "gpt-5")
VALIDATOR_MODEL: str = os.getenv("VALIDATOR_MODEL", "gpt-5-mini")
CHECKER_MODEL: str = os.getenv("CHECKER_MODEL", "gpt-5-mini")
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# OpenAI cloud configuration
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

# Processing parameters
BATCH_COUNT: int = int(os.getenv("BATCH_COUNT", "5"))
SIM_THRESHOLD: float = float(os.getenv("SIM_THRESHOLD", "0.88"))
CANDIDATE_COUNT: int = int(os.getenv("CANDIDATE_COUNT", "8"))
KEEP_TOP_K: int = int(os.getenv("KEEP_TOP_K", "5"))
DIVERSITY_MAX_SIM: float = float(os.getenv("DIVERSITY_MAX_SIM", "0.92"))
CHAT_RETRIES: int = int(os.getenv("CHAT_RETRIES", "3"))

# Gold examples configuration
GOLD_SCOPE: str = os.getenv("GOLD_SCOPE", "category")
GOLD_DB_LIMIT: int = int(os.getenv("GOLD_DB_LIMIT", "30"))
GOLD_MAX_CHARS: int = int(os.getenv("GOLD_MAX_CHARS", "6000"))
GOLD_EXAMPLES: int = int(os.getenv("GOLD_EXAMPLES", "4"))
GOLD_FS_DIR: str = os.getenv("GOLD_FS_DIR", "gold_md")

# Flask configuration (legacy)
FLASK_SECRET_KEY: str | None = os.getenv("FLASK_SECRET_KEY")


# ==== Client factory functions ====

def client_local() -> OpenAI:
    """
    Return an OpenAI client configured for the local LLM server.

    Uses LOCAL_BASE_URL and LOCAL_API_KEY from config_trinity.
    """
    return OpenAI(
        base_url=LOCAL_BASE_URL,
        api_key=LOCAL_API_KEY
    )


def client_cloud() -> OpenAI:
    """
    Return an OpenAI client configured for the cloud API.

    Uses OPENAI_BASE_URL and OPENAI_API_KEY.
    """
    return OpenAI(
        base_url=OPENAI_BASE_URL,
        api_key=OPENAI_API_KEY
    )


# ==== Exports ====

__all__ = [
    # Database
    "DB_PATH",
    "TABLE_NAME",
    "EMB_TABLE",
    "BASE_DIR",
    # Models
    "GEN_MODEL",
    "VALIDATOR_MODEL",
    "CHECKER_MODEL",
    "EMBED_MODEL",
    "LOCAL_MODEL",
    # Endpoints
    "LOCAL_BASE_URL",
    "LOCAL_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_API_KEY",
    # Processing parameters
    "BATCH_COUNT",
    "SIM_THRESHOLD",
    "CANDIDATE_COUNT",
    "KEEP_TOP_K",
    "DIVERSITY_MAX_SIM",
    "CHAT_RETRIES",
    # Gold examples
    "GOLD_SCOPE",
    "GOLD_DB_LIMIT",
    "GOLD_MAX_CHARS",
    "GOLD_EXAMPLES",
    "GOLD_FS_DIR",
    # Filtering
    "REQUIRE_APPROVED_ONLY",
    # Legacy
    "FLASK_SECRET_KEY",
    # Client factories
    "client_local",
    "client_cloud",
]

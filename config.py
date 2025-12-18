"""
config.py - DEPRECATED: Backward compatibility shim

This module is DEPRECATED. All configuration now lives in tatlam/settings.py.

This shim re-exports values from tatlam.settings for backward compatibility.
New code should import from tatlam.settings directly:

    from tatlam.settings import get_settings
    settings = get_settings()

Or for direct attribute access (backward compatible):

    from tatlam.settings import DB_PATH, TABLE_NAME
"""
from __future__ import annotations

import warnings

# Emit deprecation warning on import
warnings.warn(
    "config is deprecated. Use 'from tatlam.settings import get_settings' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all settings for backward compatibility
from tatlam.settings import (
    BASE_DIR,
    DB_PATH,
    TABLE_NAME,
    EMB_TABLE,
    REQUIRE_APPROVED_ONLY,
    LOCAL_MODEL_NAME as LOCAL_MODEL,
    LOCAL_BASE_URL,
    LOCAL_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_API_KEY,
    GEN_MODEL,
    VALIDATOR_MODEL,
    CHECKER_MODEL,
    EMBED_MODEL,
    BATCH_COUNT,
    SIM_THRESHOLD,
    CANDIDATE_COUNT,
    KEEP_TOP_K,
    DIVERSITY_MAX_SIM,
    CHAT_RETRIES,
    GOLD_SCOPE,
    GOLD_DB_LIMIT,
    GOLD_MAX_CHARS,
    GOLD_EXAMPLES,
    GOLD_FS_DIR,
    FLASK_SECRET_KEY,
    # Trinity-specific
    WRITER_MODEL_NAME,
    JUDGE_MODEL_NAME,
    LOCAL_MODEL_NAME,
    ANTHROPIC_API_KEY,
    GOOGLE_API_KEY,
)

# Re-export client factory functions
from tatlam.core.llm_factory import client_local, client_cloud

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

"""
config_trinity.py - DEPRECATED: Backward compatibility shim

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
    "config_trinity is deprecated. Use 'from tatlam.settings import get_settings' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all settings for backward compatibility
from tatlam.settings import (
    BASE_DIR,
    GOLD_DIR,
    DB_PATH,
    TABLE_NAME,
    REQUIRE_APPROVED_ONLY,
    WRITER_MODEL_PROVIDER,
    WRITER_MODEL_NAME,
    ANTHROPIC_API_KEY,
    JUDGE_MODEL_PROVIDER,
    JUDGE_MODEL_NAME,
    GOOGLE_API_KEY,
    LOCAL_MODEL_NAME,
    LOCAL_BASE_URL,
    LOCAL_API_KEY,
    PAGE_TITLE,
)

__all__ = [
    "BASE_DIR",
    "GOLD_DIR",
    "DB_PATH",
    "TABLE_NAME",
    "REQUIRE_APPROVED_ONLY",
    "WRITER_MODEL_PROVIDER",
    "WRITER_MODEL_NAME",
    "ANTHROPIC_API_KEY",
    "JUDGE_MODEL_PROVIDER",
    "JUDGE_MODEL_NAME",
    "GOOGLE_API_KEY",
    "LOCAL_MODEL_NAME",
    "LOCAL_BASE_URL",
    "LOCAL_API_KEY",
    "PAGE_TITLE",
]

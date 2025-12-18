"""Compatibility wrapper for category helpers.

This module re-exports from `tatlam.core.categories` to preserve existing
imports while the codebase is modularized.

Deprecated: Import directly from `tatlam.core.categories`. This shim will be
removed in a future release.
"""

from __future__ import annotations

import warnings

try:
    from tatlam.core.categories import CATS, category_to_slug, normalize_hebrew
except Exception as e:  # pragma: no cover
    raise ImportError(
        "Failed to import from 'tatlam.core.categories'. Ensure the core module "
        "is available, or update your imports to 'tatlam.core.categories'."
    ) from e

warnings.warn(
    (
        "'categories' is a compatibility shim and will be removed in a future "
        "release. Import from 'tatlam.core.categories' instead."
    ),
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["CATS", "normalize_hebrew", "category_to_slug"]

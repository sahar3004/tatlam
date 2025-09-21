"""Compatibility wrapper for category helpers.

This module re-exports from `tatlam.core.categories` to preserve existing
imports while the codebase is modularized.
"""

from __future__ import annotations

from tatlam.core.categories import CATS, category_to_slug, normalize_hebrew

__all__ = ["CATS", "normalize_hebrew", "category_to_slug"]

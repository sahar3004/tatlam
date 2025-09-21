"""Compatibility layer for logging configuration.

Re-exports the public API from `tatlam.infra.logging` to preserve imports.
"""

from __future__ import annotations

from tatlam.infra.logging import StructuredFormatter, configure_logging

__all__ = ["StructuredFormatter", "configure_logging"]

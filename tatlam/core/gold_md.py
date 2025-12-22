"""Gold Markdown parser API (core re-export).

This module provides the interface for parsing Hebrew Markdown scenarios.
It delegates to the implementation in `tatlam.core.md_parser`.
"""

from __future__ import annotations

from typing import Any

from tatlam.core.md_parser import parse_md_to_scenario as _parse_impl


def parse_md_to_scenario(md_text: str) -> dict[str, Any]:
    """Parse a Gold Markdown document into a scenario dict.

    Uses the core Markdown parser to convert structured Hebrew text
    into a scenario dictionary suitable for the database.
    """
    return _parse_impl(md_text)


__all__ = ["parse_md_to_scenario"]

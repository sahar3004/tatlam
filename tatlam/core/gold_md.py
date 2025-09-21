"""Gold Markdown parser API (core re-export).

This provides a stable import path in the core package while we
incrementally modularize the original `import_gold_md.py` script.
"""

from __future__ import annotations

from typing import Any, Callable, cast


def parse_md_to_scenario(md_text: str) -> dict[str, Any]:
    """Parse a Gold Markdown document into a scenario dict.

    Delegates to the current implementation in `import_gold_md.py` via a
    dynamic import to avoid pulling CLI modules into type checking.
    """
    mod = __import__("import_gold_md")
    impl = cast(Callable[[str], dict[str, Any]], getattr(mod, "parse_md_to_scenario"))  # noqa: B009
    return impl(md_text)


__all__ = ["parse_md_to_scenario"]

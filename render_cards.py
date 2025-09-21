"""Compatibility wrapper for render-cards CLI and helpers.

Re-exports logic from `tatlam.cli.render_cards` to preserve imports.
"""

from tatlam.cli.render_cards import (
    DEFAULT_TEMPLATE_PATH,
    JSON_LIST_FIELDS,
    coerce_row_types,
    fetch,
    load_template,
    main,
    safe_filename,
    unique_path,
)

__all__ = [
    "JSON_LIST_FIELDS",
    "coerce_row_types",
    "DEFAULT_TEMPLATE_PATH",
    "load_template",
    "fetch",
    "safe_filename",
    "unique_path",
    "main",
]

if __name__ == "__main__":
    raise SystemExit(main())

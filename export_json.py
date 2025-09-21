"""Compatibility wrapper for export-json CLI and API.

Re-exports logic from `tatlam.cli.export_json` to preserve imports.
"""

from tatlam.cli.export_json import fetch_rows, main, normalize

__all__ = ["fetch_rows", "normalize", "main"]

if __name__ == "__main__":
    raise SystemExit(main())

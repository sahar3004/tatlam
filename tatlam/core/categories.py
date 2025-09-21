"""Category helpers shared between the Flask app and batch tooling.

This module was moved from `tatlam/categories.py` as part of Phase 2
modularization. The original path remains as a thin re-export wrapper to
preserve import compatibility.
"""

from __future__ import annotations

import logging
import re
from typing import TypedDict

LOGGER = logging.getLogger(__name__)


class CatMeta(TypedDict, total=False):
    title: str
    aliases: list[str]


CATS: dict[str, CatMeta] = {
    "piguim-peshutim": {
        "title": "פיגועים פשוטים",
        "aliases": ["פיגועים פשוטים", "פיגועים פשוטים (דקירה/ירי)"],
    },
    "ezrahi-murkav": {
        "title": "אזרחי מורכב",
        "aliases": ["אזרחי מורכב", "אירועים מורכבים עם אזרחים"],
    },
    "hadira-razishim": {
        "title": "חדירה לחדרים רגישים",
        "aliases": ["חדירה לחדרים רגישים"],
    },
    "tachanot-iliyot": {"title": "תחנות עיליות", "aliases": ["תחנות עיליות"]},
    "iyumim-tech": {"title": "איומים טכנולוגיים", "aliases": ["איומים טכנולוגיים"]},
    "eiroa-kimi": {"title": "אירוע כימי", "aliases": ["אירוע כימי"]},
    "bnei-aruba": {"title": "בני ערובה", "aliases": ["בני ערובה"]},
    "chefetz-chashud": {
        "title": "חפץ חשוד ומטען",
        "aliases": [
            "חפץ חשוד ומטען",
            "כבודה עזובה / חפץ חשוד / מטען",
            "כבודה עזובה/חפץ חשוד/מטען",
        ],
    },
    "uncategorized": {
        "title": "לא מסווג",
        "aliases": ["לא מסווג", "ללא קטגוריה", "לא-מסווג"],
    },
}

_ZW_CHARS = "\u200e\u200f\u200d\u202a\u202b\u202c\u202d\u202e"
_NORM_PUNCT = {
    "–": "-",
    "—": "-",
    "−": "-",
    "־": "-",
    "\u00a0": " ",
    ",": ",",
    "/": "/",
}


def normalize_hebrew(value: str | None) -> str:
    """Normalise Hebrew category labels for robust slug matching."""
    if not value:
        return ""
    text = value.translate({ord(c): None for c in _ZW_CHARS})
    text = re.sub(
        r"^\s*(קטגוריה|category)\s*[:：]\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = text.strip().strip('"').strip("'")
    for src, target in _NORM_PUNCT.items():
        text = text.replace(src, target)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def category_to_slug(category: str | None) -> str | None:
    """Resolve a category display value (Hebrew) into an internal slug."""
    if category is None:
        return None
    raw = str(category)
    normalized = normalize_hebrew(raw)
    if not normalized:
        return "uncategorized"
    if normalized in CATS:
        return normalized
    for slug, meta in CATS.items():
        aliases: list[str] = [meta.get("title", "")] + list(meta.get("aliases", []))
        for alias in aliases:
            alias_norm = normalize_hebrew(alias)
            if not alias_norm:
                continue
            if normalized == alias_norm or alias_norm == normalized:
                return slug
            if alias_norm in normalized or normalized in alias_norm:
                return slug
    if normalized in {"לא מסווג", "ללא קטגוריה", "לא-מסווג", "uncategorized"}:
        return "uncategorized"
    LOGGER.warning("[category_to_slug] unmapped category value: %r -> None", raw)
    return None


__all__ = ["CATS", "normalize_hebrew", "category_to_slug"]

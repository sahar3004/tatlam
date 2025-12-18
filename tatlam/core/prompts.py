"""Prompt helpers shared across CLI and core.

Small, pure helpers extracted from run_batch for reuse.
"""

from __future__ import annotations


def load_system_prompt(path: str = "system_prompt_he.txt") -> str:
    try:
        with open(path, encoding="utf8") as f:
            return f.read()
    except Exception:
        return (
            'אתה מסייע ליצירת תטל"מים מובְנים ואחראיים. שמור על פורמט, עברית תקנית, '
            "וריאליזם מבצעי. אל תמציא קישורים."
        )


def memory_addendum() -> dict[str, str]:
    return {
        "role": "system",
        "content": (
            "בדוק בזיכרון הארגוני דמיון לתטל״מים קיימים; אם דומה – שנה כותרת/זווית/"
            "actors/זמן/סביבה כך שתיווצר שונות. אין להשתמש בכותרת קיימת."
        ),
    }


__all__ = ["load_system_prompt", "memory_addendum"]

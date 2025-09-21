import string

import pytest
from hypothesis import given, strategies as st

from tatlam.categories import CATS, category_to_slug, normalize_hebrew


@given(st.text(alphabet=string.printable + "אבגדהוזחטיכלמנסעפצקרשת"))
def test_normalize_hebrew_removes_control_chars(raw: str) -> None:
    normalized = normalize_hebrew("\u200f" + raw + "\u200e")
    for ch in "\u200e\u200f\u200d\u202a\u202b\u202c\u202d\u202e":
        assert ch not in normalized
    assert normalized.strip() == normalized


def test_category_to_slug_matches_aliases() -> None:
    assert category_to_slug("חפץ חשוד ומטען") == "chefetz-chashud"
    assert category_to_slug("כבודה עזובה / חפץ חשוד / מטען") == "chefetz-chashud"
    assert category_to_slug("לא מסווג") == "uncategorized"


@pytest.mark.parametrize("slug", list(CATS.keys()))
def test_category_to_slug_recognises_titles(slug: str) -> None:
    meta = CATS[slug]
    assert category_to_slug(meta["title"]) == slug

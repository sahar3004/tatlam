"""
Unit tests for tatlam/core/categories.py

Tests category definitions and mapping logic.
Target: Ensure CATS dictionary contains valid Hebrew categories with proper structure.
"""

import pytest
from tatlam.core.categories import CATS, category_to_slug, normalize_hebrew


@pytest.mark.unit
class TestCategories:
    """Test suite for category definitions."""

    def test_cats_dictionary_exists(self):
        """Verify CATS dictionary is defined and not empty."""
        assert CATS is not None
        assert len(CATS) > 0

    def test_cats_keys_are_slug_strings(self):
        """Verify all category keys are valid slug strings (lowercase, hyphens)."""
        for key in CATS.keys():
            assert isinstance(key, str)
            # Slugs should be lowercase ASCII with hyphens
            assert key.islower() or "-" in key, f"Category key '{key}' is not a valid slug"

    def test_cats_values_are_dictionaries(self):
        """Verify all category values are dictionaries with title and aliases."""
        for key, value in CATS.items():
            assert isinstance(value, dict), f"Category '{key}' value should be a dict"
            assert "title" in value, f"Category '{key}' missing 'title' key"
            assert "aliases" in value, f"Category '{key}' missing 'aliases' key"

    def test_cats_titles_are_hebrew(self):
        """Verify all category titles contain Hebrew text."""
        for key, meta in CATS.items():
            title = meta.get("title", "")
            has_hebrew = any("\u0590" <= char <= "\u05FF" for char in title)
            assert has_hebrew, f"Category '{key}' title '{title}' does not contain Hebrew"

    def test_cats_no_empty_titles(self):
        """Ensure no category has an empty title."""
        for key, meta in CATS.items():
            title = meta.get("title", "")
            assert title.strip() != "", f"Category '{key}' has empty title"

    def test_expected_categories_present(self):
        """Verify key security categories exist in CATS."""
        expected_slugs = [
            "piguim-peshutim",  # Simple attacks
            "chefetz-chashud",  # Suspicious object
            "uncategorized",  # Uncategorized
        ]

        for expected in expected_slugs:
            assert expected in CATS, f"Expected category slug '{expected}' not found in CATS"

    def test_cats_immutable_structure(self):
        """Test that CATS can be safely iterated and accessed."""
        # Should not raise any exceptions
        categories_list = list(CATS.keys())
        assert len(categories_list) > 0

        # Test random access
        first_key = categories_list[0]
        assert CATS[first_key] is not None

    def test_category_to_slug_with_hebrew_input(self):
        """Test category_to_slug resolves Hebrew names to slugs."""
        # Test known Hebrew category names
        assert category_to_slug("פיגועים פשוטים") == "piguim-peshutim"
        assert category_to_slug("חפץ חשוד ומטען") == "chefetz-chashud"
        assert category_to_slug("לא מסווג") == "uncategorized"

    def test_category_to_slug_with_empty_input(self):
        """Test category_to_slug handles empty/None input."""
        assert category_to_slug("") == "uncategorized"
        assert category_to_slug(None) is None

    def test_normalize_hebrew_strips_unicode_markers(self):
        """Test normalize_hebrew removes RTL/LTR markers."""
        # Test with zero-width characters
        text_with_markers = "\u200eשלום\u200f"
        normalized = normalize_hebrew(text_with_markers)
        assert "\u200e" not in normalized
        assert "\u200f" not in normalized
        assert "שלום" in normalized

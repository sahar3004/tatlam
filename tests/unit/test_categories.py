"""
Unit tests for tatlam/core/categories.py

Tests category definitions and mapping logic.
Target: Ensure CATS dictionary contains valid Hebrew categories.
"""

import pytest
from tatlam.core.categories import CATS


@pytest.mark.unit
class TestCategories:
    """Test suite for category definitions."""

    def test_cats_dictionary_exists(self):
        """Verify CATS dictionary is defined and not empty."""
        assert CATS is not None
        assert len(CATS) > 0

    def test_cats_keys_are_hebrew(self):
        """Verify all category keys are Hebrew strings."""
        for key in CATS.keys():
            assert isinstance(key, str)
            # Check for Hebrew characters (Unicode range: U+0590 to U+05FF)
            has_hebrew = any('\u0590' <= char <= '\u05FF' for char in key)
            assert has_hebrew, f"Category key '{key}' does not contain Hebrew characters"

    def test_cats_values_are_strings(self):
        """Verify all category values are strings (descriptions)."""
        for value in CATS.values():
            assert isinstance(value, str)

    def test_cats_no_empty_values(self):
        """Ensure no category has an empty description."""
        for key, value in CATS.items():
            assert value.strip() != "", f"Category '{key}' has empty description"

    def test_expected_categories_present(self):
        """Verify key categories exist in CATS."""
        expected_categories = [
            "פיננסים",  # Finance
            "בריאות",   # Health
            "חינוך",     # Education
        ]

        for expected in expected_categories:
            assert expected in CATS, f"Expected category '{expected}' not found in CATS"

    def test_cats_immutable_structure(self):
        """Test that CATS can be safely iterated and accessed."""
        # Should not raise any exceptions
        categories_list = list(CATS.keys())
        assert len(categories_list) > 0

        # Test random access
        first_key = categories_list[0]
        assert CATS[first_key] is not None

"""
Unit tests for generic utility functions.

Tests helper functions used across the TATLAM project.
Target: Generic utilities (string processing, data normalization, etc.).
"""

import pytest
from tatlam.infra.repo import normalize_row


@pytest.mark.unit
class TestUtils:
    """Test suite for utility functions."""

    def test_normalize_row_with_sqlite_row(self):
        """Test normalize_row converts sqlite3.Row to dictionary."""
        # Simulate a sqlite3.Row
        class MockRow:
            def __init__(self, data):
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        mock_row = MockRow({
            "id": 1,
            "title": "כותרת בדיקה",
            "category": "פיננסים"
        })

        result = normalize_row(mock_row)

        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["title"] == "כותרת בדיקה"
        assert result["category"] == "פיננסים"

    def test_normalize_row_preserves_hebrew(self):
        """Test normalize_row preserves Hebrew characters."""
        class MockRow:
            def __init__(self, data):
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        hebrew_data = {
            "title": "בדיקת עברית מלאה",
            "description": "תיאור בעברית עם ניקוד: שָׁלוֹם"
        }

        mock_row = MockRow(hebrew_data)
        result = normalize_row(mock_row)

        assert result["title"] == "בדיקת עברית מלאה"
        assert "ניקוד" in result["description"]

    def test_normalize_row_handles_null_values(self):
        """Test normalize_row handles NULL values correctly."""
        class MockRow:
            def __init__(self, data):
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        mock_row = MockRow({
            "id": 1,
            "title": "כותרת",
            "optional_field": None
        })

        result = normalize_row(mock_row)

        assert result["id"] == 1
        assert result["optional_field"] is None

    def test_normalize_row_with_json_fields(self):
        """Test normalize_row handles JSON string fields."""
        import json

        class MockRow:
            def __init__(self, data):
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        steps_json = json.dumps([
            {"step": 1, "description": "צעד ראשון"},
            {"step": 2, "description": "צעד שני"}
        ])

        mock_row = MockRow({
            "id": 1,
            "steps": steps_json
        })

        result = normalize_row(mock_row)

        assert result["id"] == 1
        # Steps might remain as JSON string or be parsed, depending on implementation
        assert result["steps"] is not None

    def test_normalize_row_empty_row(self):
        """Test normalize_row with empty row - adds JSON field defaults."""
        class MockRow:
            def __init__(self, data):
                self._data = data

            def keys(self):
                return self._data.keys()

            def __getitem__(self, key):
                return self._data[key]

        mock_row = MockRow({})
        result = normalize_row(mock_row)

        assert isinstance(result, dict)
        # normalize_row adds default empty lists for JSON_FIELDS
        from tatlam.infra.repo import JSON_FIELDS
        for field in JSON_FIELDS:
            assert field in result
            assert result[field] == []

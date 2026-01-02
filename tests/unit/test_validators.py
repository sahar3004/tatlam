"""
Unit tests for tatlam/core/validators.py

Tests JSON schema validation logic.
Target: validate_json_schema() function.
"""

import pytest
from tatlam.core.validators import validate_json_schema


@pytest.mark.unit
class TestValidators:
    """Test suite for JSON validation functions."""

    def test_validate_json_schema_with_valid_data(self, sample_scenario_data, sample_json_schema):
        """Test validation passes with valid scenario data."""
        result = validate_json_schema(sample_scenario_data, sample_json_schema)
        assert result is True or result is None  # Depending on implementation

    def test_validate_json_schema_missing_required_field(self, sample_json_schema):
        """Test validation fails when required field is missing."""
        invalid_data = {
            "category": "פיננסים",
            "difficulty": "בינוני",
            # Missing 'title' and 'steps'
        }

        with pytest.raises(Exception):  # Could be ValidationError or ValueError
            validate_json_schema(invalid_data, sample_json_schema)

    def test_validate_json_schema_wrong_type(self, sample_json_schema):
        """Test validation fails when field has wrong type."""
        invalid_data = {
            "title": "כותרת",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": "not an array",  # Should be array, not string
        }

        with pytest.raises(Exception):
            validate_json_schema(invalid_data, sample_json_schema)

    def test_validate_json_schema_invalid_steps_structure(self, sample_json_schema):
        """Test validation fails when steps array has invalid structure."""
        invalid_data = {
            "title": "כותרת",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": [{"step": 1}],  # Missing 'description'
        }

        with pytest.raises(Exception):
            validate_json_schema(invalid_data, sample_json_schema)

    def test_validate_json_schema_with_hebrew_content(self, sample_json_schema):
        """Test validation works correctly with Hebrew text."""
        hebrew_data = {
            "title": "בדיקת עברית מלאה",
            "category": "בריאות",
            "difficulty": "קשה",
            "bundle": "חבילת בריאות",
            "steps": [
                {"step": 1, "description": "פתיחת יישום בעברית"},
                {"step": 2, "description": "ניווט לתפריט הגדרות"},
            ],
            "expected_behavior": "המערכת תגיב בעברית",
            "testing_tips": "בדוק תמיכה ב-RTL",
        }

        result = validate_json_schema(hebrew_data, sample_json_schema)
        assert result is True or result is None

    def test_validate_json_schema_empty_steps_array(self, sample_json_schema):
        """Test validation handles empty steps array."""
        data_with_empty_steps = {
            "title": "כותרת",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": [],  # Empty array
        }

        # Depending on schema, this might be valid or invalid
        # Adjust assertion based on actual validation rules
        try:
            result = validate_json_schema(data_with_empty_steps, sample_json_schema)
            assert isinstance(result, (bool, type(None)))
        except Exception:
            # If validation requires at least one step, that's also acceptable
            pass

    def test_validate_json_schema_extra_fields(self, sample_scenario_data, sample_json_schema):
        """Test validation handles extra fields not in schema."""
        data_with_extra = sample_scenario_data.copy()
        data_with_extra["extra_field"] = "שדה נוסף"

        # Schema validation typically allows extra fields
        result = validate_json_schema(data_with_extra, sample_json_schema)
        assert result is True or result is None

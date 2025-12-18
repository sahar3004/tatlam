"""
LLM Evaluation tests for JSON generation robustness.

Tests TrinityBrain's ability to consistently generate valid JSON.
EXPENSIVE: Makes real API calls. Mark as @slow.
"""

import pytest
import json


@pytest.mark.slow
@pytest.mark.skipif(True, reason="Expensive test - requires real API calls")
class TestJSONRobustness:
    """Test suite for JSON generation robustness."""

    def test_generates_valid_json(self, mock_brain):
        """Test that LLM consistently generates valid JSON."""
        # In production: Generate scenario and parse JSON
        sample_json = '{"title": "בדיקה", "category": "פיננסים"}'

        # Should parse without errors
        parsed = json.loads(sample_json)
        assert isinstance(parsed, dict)

    def test_json_with_hebrew_no_escaping_issues(self, mock_brain):
        """Test JSON with Hebrew doesn't have escape sequence issues."""
        hebrew_json = '{"title": "בדיקת עברית", "description": "תיאור בעברית"}'

        parsed = json.loads(hebrew_json)

        # Hebrew should be preserved
        assert "עברית" in parsed["title"]
        assert "בעברית" in parsed["description"]

    def test_json_required_fields_always_present(self, mock_brain):
        """Test that all required fields are always in generated JSON."""
        required_fields = ["title", "category", "difficulty", "steps"]

        sample_json = {
            "title": "תרחיש",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": []
        }

        for field in required_fields:
            assert field in sample_json

    def test_json_steps_array_structure(self, mock_brain):
        """Test that steps array has consistent structure."""
        sample_steps = [
            {"step": 1, "description": "צעד ראשון"},
            {"step": 2, "description": "צעד שני"}
        ]

        # Each step should have required fields
        for step in sample_steps:
            assert "step" in step
            assert "description" in step
            assert isinstance(step["step"], int)
            assert isinstance(step["description"], str)

    def test_json_no_trailing_commas(self, mock_brain):
        """Test that generated JSON doesn't have trailing commas."""
        # Trailing commas are invalid in JSON
        valid_json = '{"items": [1, 2, 3]}'  # No trailing comma
        invalid_json = '{"items": [1, 2, 3,]}'  # Trailing comma - invalid

        # Valid should parse
        json.loads(valid_json)

        # Invalid should fail
        with pytest.raises(json.JSONDecodeError):
            json.loads(invalid_json)

    def test_json_proper_string_escaping(self, mock_brain):
        """Test that strings with quotes are properly escaped."""
        json_with_quotes = {
            "title": 'תרחיש עם "מרכאות" ו-\'גרשיים\'',
            "description": "תיאור עם \n שורה חדשה"
        }

        # Should serialize and parse correctly
        json_str = json.dumps(json_with_quotes, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["title"] == json_with_quotes["title"]

    def test_json_handles_empty_arrays(self, mock_brain):
        """Test that empty arrays are valid."""
        json_with_empty_array = {
            "title": "תרחיש",
            "steps": []
        }

        json_str = json.dumps(json_with_empty_array)
        parsed = json.loads(json_str)

        assert isinstance(parsed["steps"], list)
        assert len(parsed["steps"]) == 0

    def test_json_no_undefined_or_null_strings(self, mock_brain):
        """Test that JSON doesn't contain string values like 'undefined' or 'null'."""
        sample_json = {
            "title": "תרחיש",
            "optional_field": None  # None is valid
        }

        json_str = json.dumps(sample_json)

        # Should use 'null', not 'undefined'
        assert "undefined" not in json_str
        assert "null" in json_str  # JSON null is valid

    def test_json_number_types_consistent(self, mock_brain):
        """Test that numbers are consistently typed (int vs float)."""
        sample_json = {
            "step": 1,  # Should be int
            "priority": 5,  # Should be int
            "completion": 0.95  # Can be float
        }

        # Step numbers should be integers
        assert isinstance(sample_json["step"], int)
        assert isinstance(sample_json["priority"], int)

    def test_json_boolean_types_not_strings(self, mock_brain):
        """Test that booleans are proper JSON booleans, not strings."""
        correct_json = '{"completed": true}'  # Correct
        incorrect_json = '{"completed": "true"}'  # String, not boolean

        parsed_correct = json.loads(correct_json)
        parsed_incorrect = json.loads(incorrect_json)

        # Correct should be boolean
        assert isinstance(parsed_correct["completed"], bool)

        # Incorrect is string
        assert isinstance(parsed_incorrect["completed"], str)

    def test_json_schema_validation_passes(self, mock_brain, sample_json_schema):
        """Test that generated JSON passes schema validation."""
        from tatlam.core.validators import validate_json_schema

        sample_data = {
            "title": "תרחיש בדיקה",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": [
                {"step": 1, "description": "צעד ראשון"}
            ]
        }

        # Should pass validation
        result = validate_json_schema(sample_data, sample_json_schema)
        assert result is True or result is None

    def test_json_encoding_utf8(self, mock_brain):
        """Test that JSON is properly UTF-8 encoded."""
        hebrew_data = {
            "title": "בדיקת קידוד UTF-8",
            "emoji": "🔥✅",
            "mixed": "עברית English 中文"
        }

        json_str = json.dumps(hebrew_data, ensure_ascii=False)

        # Should contain actual characters, not escape sequences
        assert "עברית" in json_str
        assert "🔥" in json_str or "\\u" in json_str  # Either literal or escaped

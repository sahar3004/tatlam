import pytest
import json
from tatlam.core.bundles import (
    validate_bundle_strict,
    coerce_bundle_shape,
    ScenarioModel,
    ScenarioBundleModel,
)
from pydantic import ValidationError


class TestBundles:

    def test_coerce_bundle_shape_defaults(self):
        """Test that missing fields are filled with defaults."""
        bundle = {"scenarios": [{"title": "Test"}]}
        fixed = coerce_bundle_shape(bundle)
        sc = fixed["scenarios"][0]
        assert sc["title"] == "Test"
        assert sc["threat_level"] == ""
        assert isinstance(sc["steps"], list)
        assert len(sc["steps"]) == 0

    def test_coerce_bundle_shape_json_string(self):
        """Test coercion of JSON string fields."""
        bundle = {
            "scenarios": [
                {
                    "title": "T",
                    "steps": json.dumps([{"step": 1}]),
                    "required_response": "single string item",
                }
            ]
        }
        fixed = coerce_bundle_shape(bundle)
        sc = fixed["scenarios"][0]
        assert sc["steps"] == [{"step": 1}]
        assert sc["required_response"] == ["single string item"]

    def test_coerce_bundle_shape_invalid_json(self):
        """Test coercion of invalid JSON string."""
        bundle = {
            "scenarios": [
                {
                    "title": "T",
                    "steps": "{invalid",
                }
            ]
        }
        fixed = coerce_bundle_shape(bundle)
        sc = fixed["scenarios"][0]
        # Should wrap invalid string in list
        assert sc["steps"] == ["{invalid"]

    def test_validate_bundle_strict_valid(self):
        """Test validation of a valid bundle."""
        bundle = {
            "bundle_id": "B1",
            "scenarios": [{"title": "Title", "category": "Cat", "steps": ["step1"]}],
        }
        validated = validate_bundle_strict(bundle)
        assert validated["bundle_id"] == "B1"
        assert validated["scenarios"][0]["title"] == "Title"

    def test_validate_bundle_strict_invalid(self):
        """Test validation raises error on invalid data."""
        bundle = {
            "bundle_id": "B1",
            "scenarios": [{"title": "", "category": "Cat"}],  # Empty title not allowed
        }
        with pytest.raises(ValidationError):
            validate_bundle_strict(bundle)

    def test_scenario_model_coercion_validator(self):
        """Test Pydantic validator for list fields."""
        # Single string -> list
        m = ScenarioModel(title="T", category="C", steps="step1")
        assert m.steps == ["step1"]

        # Valid JSON string -> list
        m = ScenarioModel(title="T", category="C", steps='["step1", "step2"]')
        assert m.steps == ["step1", "step2"]

        # None -> empty list
        # Using dict to bypass init checks if any, but field validator runs on init
        m = ScenarioModel(title="T", category="C", steps=None)
        assert m.steps == []

    def test_bundle_model_strictness(self):
        """Test that bundle model forbids extra fields."""
        with pytest.raises(ValidationError):
            ScenarioBundleModel(bundle_id="B", scenarios=[], extra_field="foo")

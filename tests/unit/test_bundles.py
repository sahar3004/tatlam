"""
Unit tests for tatlam/core/bundles.py

Tests bundle validation and normalization with Pydantic schemas.
Target: ScenarioModel, ScenarioBundleModel, coerce_bundle_shape, validate_bundle_strict
"""
from __future__ import annotations

import json
from typing import Any

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from tatlam.core.bundles import (
    ScenarioBundleModel,
    ScenarioModel,
    coerce_bundle_shape,
    validate_bundle_strict,
)


@pytest.mark.unit
class TestScenarioModel:
    """Test suite for ScenarioModel Pydantic validation."""

    def test_valid_minimal_scenario(self) -> None:
        """Test creating a scenario with only required fields."""
        scenario = ScenarioModel(title="Test Title", category="Test Category")
        assert scenario.title == "Test Title"
        assert scenario.category == "Test Category"
        assert scenario.steps == []
        assert scenario.external_id == ""

    def test_valid_full_scenario(self) -> None:
        """Test creating a scenario with all fields populated."""
        scenario = ScenarioModel(
            title="Full Scenario",
            category="Security",
            external_id="EXT-001",
            threat_level="HIGH",
            likelihood="MEDIUM",
            complexity="LOW",
            location="Allenby Station",
            background="Background text",
            operational_background="Ops background",
            media_link="https://example.com",
            mask_usage="Required",
            authority_notes="Notes here",
            cctv_usage="Active",
            end_state_success="Success state",
            end_state_failure="Failure state",
            steps=["step1", "step2"],
            required_response=["response1"],
            debrief_points=["point1"],
            comms=["comm1"],
            decision_points=["decision1"],
            escalation_conditions=["condition1"],
            lessons_learned=["lesson1"],
            variations=["variation1"],
            validation=["valid1"],
        )
        assert scenario.title == "Full Scenario"
        assert scenario.threat_level == "HIGH"
        assert len(scenario.steps) == 2
        assert len(scenario.required_response) == 1

    def test_empty_title_fails(self) -> None:
        """Test that empty title raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioModel(title="", category="Test")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_empty_category_fails(self) -> None:
        """Test that empty category raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioModel(title="Test", category="")
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_missing_required_fields_fails(self) -> None:
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError):
            ScenarioModel()  # type: ignore[call-arg]

    def test_list_field_coercion_from_string(self) -> None:
        """Test that string values are coerced to single-item lists."""
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps="single step as string",
        )
        assert scenario.steps == ["single step as string"]

    def test_list_field_coercion_from_json_string(self) -> None:
        """Test that JSON array strings are parsed to lists."""
        json_array = '["step1", "step2", "step3"]'
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps=json_array,
        )
        assert scenario.steps == ["step1", "step2", "step3"]

    def test_list_field_coercion_from_json_object(self) -> None:
        """Test that JSON object strings become single-item lists."""
        json_object = '{"key": "value"}'
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps=json_object,
        )
        assert scenario.steps == [{"key": "value"}]

    def test_list_field_coercion_from_none(self) -> None:
        """Test that None values are coerced to empty lists."""
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps=None,
        )
        assert scenario.steps == []

    def test_list_field_coercion_from_empty_string(self) -> None:
        """Test that empty strings are coerced to empty lists."""
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps="",
        )
        assert scenario.steps == []

    def test_list_field_coercion_from_whitespace_string(self) -> None:
        """Test that whitespace-only strings are coerced to empty lists."""
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps="   ",
        )
        assert scenario.steps == []

    def test_list_field_preserves_list(self) -> None:
        """Test that actual lists are preserved as-is."""
        input_list = [{"step": 1}, {"step": 2}]
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps=input_list,
        )
        assert scenario.steps == input_list

    def test_list_field_coercion_from_dict(self) -> None:
        """Test that dict values become single-item lists."""
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            steps={"key": "value"},  # type: ignore[arg-type]
        )
        assert scenario.steps == [{"key": "value"}]

    def test_extra_fields_allowed(self) -> None:
        """Test that extra fields from LLM are allowed."""
        scenario = ScenarioModel(
            title="Test",
            category="Test",
            extra_field="extra value",  # type: ignore[call-arg]
            another_extra=123,  # type: ignore[call-arg]
        )
        assert scenario.title == "Test"

    def test_hebrew_content_preserved(self) -> None:
        """Test that Hebrew content is preserved correctly."""
        hebrew_title = "תרחיש בדיקה בעברית"
        hebrew_category = "אבטחה"
        scenario = ScenarioModel(title=hebrew_title, category=hebrew_category)
        assert scenario.title == hebrew_title
        assert scenario.category == hebrew_category


@pytest.mark.unit
class TestScenarioBundleModel:
    """Test suite for ScenarioBundleModel validation."""

    def test_valid_bundle_with_scenarios(self) -> None:
        """Test creating a valid bundle with scenarios."""
        bundle = ScenarioBundleModel(
            bundle_id="BUNDLE-001",
            scenarios=[
                ScenarioModel(title="Scenario 1", category="Cat 1"),
                ScenarioModel(title="Scenario 2", category="Cat 2"),
            ],
        )
        assert bundle.bundle_id == "BUNDLE-001"
        assert len(bundle.scenarios) == 2

    def test_valid_bundle_empty_scenarios(self) -> None:
        """Test creating a bundle with no scenarios."""
        bundle = ScenarioBundleModel(bundle_id="EMPTY-BUNDLE", scenarios=[])
        assert bundle.bundle_id == "EMPTY-BUNDLE"
        assert len(bundle.scenarios) == 0

    def test_empty_bundle_id_fails(self) -> None:
        """Test that empty bundle_id raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioBundleModel(bundle_id="", scenarios=[])
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields in bundle raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            ScenarioBundleModel(
                bundle_id="TEST",
                scenarios=[],
                extra_field="not allowed",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()

    def test_bundle_with_dict_scenarios(self) -> None:
        """Test creating bundle from dict scenarios (common from JSON)."""
        bundle = ScenarioBundleModel(
            bundle_id="DICT-BUNDLE",
            scenarios=[
                {"title": "Dict Scenario", "category": "Test"},  # type: ignore[list-item]
            ],
        )
        assert len(bundle.scenarios) == 1
        assert bundle.scenarios[0].title == "Dict Scenario"


@pytest.mark.unit
class TestValidateBundleStrict:
    """Test suite for validate_bundle_strict function."""

    def test_valid_bundle_returns_dict(self) -> None:
        """Test that valid bundle returns validated dict."""
        bundle_input: dict[str, Any] = {
            "bundle_id": "VALID-001",
            "scenarios": [{"title": "Test", "category": "Cat"}],
        }
        result = validate_bundle_strict(bundle_input)
        assert isinstance(result, dict)
        assert result["bundle_id"] == "VALID-001"
        assert len(result["scenarios"]) == 1

    def test_invalid_bundle_raises_error(self) -> None:
        """Test that invalid bundle raises ValidationError."""
        bundle_input: dict[str, Any] = {
            "bundle_id": "",  # Invalid: empty
            "scenarios": [],
        }
        with pytest.raises(ValidationError):
            validate_bundle_strict(bundle_input)

    def test_missing_scenarios_raises_error(self) -> None:
        """Test that missing scenarios field raises ValidationError."""
        bundle_input: dict[str, Any] = {"bundle_id": "TEST"}
        with pytest.raises(ValidationError):
            validate_bundle_strict(bundle_input)


@pytest.mark.unit
class TestCoerceBundleShape:
    """Test suite for coerce_bundle_shape function."""

    def test_empty_bundle(self) -> None:
        """Test coercing empty bundle."""
        bundle: dict[str, Any] = {"scenarios": []}
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"] == []

    def test_missing_scenarios_key(self) -> None:
        """Test bundle without scenarios key."""
        bundle: dict[str, Any] = {}
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"] == []

    def test_fills_default_string_fields(self) -> None:
        """Test that missing string fields get empty string defaults."""
        bundle: dict[str, Any] = {
            "scenarios": [{"title": "Test", "category": "Cat"}]
        }
        result = coerce_bundle_shape(bundle)
        scenario = result["scenarios"][0]
        assert scenario["external_id"] == ""
        assert scenario["threat_level"] == ""
        assert scenario["location"] == ""

    def test_coerces_string_to_list(self) -> None:
        """Test that string values in list fields are coerced to lists."""
        bundle: dict[str, Any] = {
            "scenarios": [
                {
                    "title": "Test",
                    "category": "Cat",
                    "steps": "single step",
                }
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"][0]["steps"] == ["single step"]

    def test_coerces_json_string_to_list(self) -> None:
        """Test that JSON array strings are parsed and stored as lists."""
        bundle: dict[str, Any] = {
            "scenarios": [
                {
                    "title": "Test",
                    "category": "Cat",
                    "steps": '["step1", "step2"]',
                }
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"][0]["steps"] == ["step1", "step2"]

    def test_coerces_json_object_to_list(self) -> None:
        """Test that JSON object strings become single-item lists."""
        bundle: dict[str, Any] = {
            "scenarios": [
                {
                    "title": "Test",
                    "category": "Cat",
                    "steps": '{"key": "value"}',
                }
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"][0]["steps"] == [{"key": "value"}]

    def test_handles_none_values(self) -> None:
        """Test that None values in list fields become empty lists."""
        bundle: dict[str, Any] = {
            "scenarios": [
                {"title": "Test", "category": "Cat", "steps": None}
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"][0]["steps"] == []

    def test_handles_empty_string(self) -> None:
        """Test that empty strings in list fields become empty lists."""
        bundle: dict[str, Any] = {
            "scenarios": [
                {"title": "Test", "category": "Cat", "steps": ""}
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"][0]["steps"] == []

    def test_preserves_existing_lists(self) -> None:
        """Test that existing lists are preserved."""
        input_list = ["step1", "step2", "step3"]
        bundle: dict[str, Any] = {
            "scenarios": [
                {"title": "Test", "category": "Cat", "steps": input_list}
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"][0]["steps"] == input_list

    def test_handles_non_list_non_string(self) -> None:
        """Test that non-list/non-string values become single-item lists."""
        bundle: dict[str, Any] = {
            "scenarios": [
                {"title": "Test", "category": "Cat", "steps": 42}
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert result["scenarios"][0]["steps"] == [42]

    def test_all_list_fields_coerced(self) -> None:
        """Test that all expected list fields are coerced."""
        list_fields = [
            "steps",
            "required_response",
            "debrief_points",
            "comms",
            "decision_points",
            "escalation_conditions",
            "lessons_learned",
            "variations",
            "validation",
        ]
        bundle: dict[str, Any] = {
            "scenarios": [{
                "title": "Test",
                "category": "Cat",
                **{field: "value" for field in list_fields}
            }]
        }
        result = coerce_bundle_shape(bundle)
        scenario = result["scenarios"][0]
        for field in list_fields:
            assert isinstance(scenario[field], list), f"{field} should be a list"
            assert scenario[field] == ["value"], f"{field} should contain ['value']"

    def test_handles_null_scenario(self) -> None:
        """Test that None scenarios are handled gracefully."""
        bundle: dict[str, Any] = {"scenarios": [None]}
        result = coerce_bundle_shape(bundle)
        # Should handle None scenario by converting to empty dict
        assert len(result["scenarios"]) == 1

    def test_multiple_scenarios(self) -> None:
        """Test coercing bundle with multiple scenarios."""
        bundle: dict[str, Any] = {
            "scenarios": [
                {"title": "Scenario 1", "category": "Cat1", "steps": "step1"},
                {"title": "Scenario 2", "category": "Cat2", "steps": ["step2a", "step2b"]},
                {"title": "Scenario 3", "category": "Cat3"},
            ]
        }
        result = coerce_bundle_shape(bundle)
        assert len(result["scenarios"]) == 3
        assert result["scenarios"][0]["steps"] == ["step1"]
        assert result["scenarios"][1]["steps"] == ["step2a", "step2b"]
        assert result["scenarios"][2]["steps"] == []


@pytest.mark.unit
class TestScenarioModelPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.text(min_size=1, max_size=100))
    def test_any_nonempty_title_accepted(self, title: str) -> None:
        """Test that any non-empty string is accepted as title."""
        scenario = ScenarioModel(title=title, category="Test")
        assert scenario.title == title

    @given(st.lists(st.text(min_size=1), min_size=0, max_size=10))
    def test_any_list_preserved_as_steps(self, steps_list: list[str]) -> None:
        """Test that any list of strings is preserved as steps."""
        scenario = ScenarioModel(title="Test", category="Test", steps=steps_list)
        assert scenario.steps == steps_list

    @given(st.dictionaries(st.text(min_size=1, max_size=10), st.text(max_size=50), max_size=5))
    def test_dict_coerced_to_single_item_list(self, d: dict[str, str]) -> None:
        """Test that any dict is coerced to a single-item list."""
        if not d:
            # Skip empty dicts (they become truthy falsy edge case)
            return
        scenario = ScenarioModel(title="Test", category="Test", steps=d)  # type: ignore[arg-type]
        assert scenario.steps == [d]

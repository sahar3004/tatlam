"""Unit tests for Pydantic schemas in tatlam.core.schemas."""

import pytest
from pydantic import ValidationError
from tatlam.core.schemas import ScenarioDTO

def test_scenario_dto_defaults():
    """Test standard defaults for ScenarioDTO."""
    dto = ScenarioDTO(title="Test Scenario", category="Security")
    assert dto.title == "Test Scenario"
    assert dto.category == "Security"
    assert dto.status == "pending"
    assert dto.owner == "web"
    assert dto.steps == []
    assert isinstance(dto.created_at, str)

def test_scenario_dto_json_parsing():
    """Test handling of empty strings for list fields."""
    dto = ScenarioDTO(
        title="Test", 
        category="Security",
        steps="",  # Should become []
        required_response=None  # Should become []
    )
    assert dto.steps == []
    assert dto.required_response == []

def test_scenario_dto_validation_error():
    """Test strict validation."""
    with pytest.raises(ValidationError):
        ScenarioDTO(title="Missing Category")

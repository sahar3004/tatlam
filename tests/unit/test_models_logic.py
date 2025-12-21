"""
Unit tests for Scenario ORM model logic.
Focuses on JSON serialization/deserialization consistency.
"""
import pytest
import json
from tatlam.infra.models import Scenario

def test_scenario_json_field_parsing():
    """Test that JSON fields are correctly parsed from string to list/dict."""
    scenario = Scenario()
    
    # Test valid JSON list
    valid_json = '[{"step": 1, "action": "test"}]'
    parsed = scenario._parse_json_field(valid_json)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["step"] == 1

    # Test empty string
    assert scenario._parse_json_field("") == []
    
    # Test None
    assert scenario._parse_json_field(None) == []

    # Test already parsed list (idempotency)
    pre_parsed = [{"step": 2}]
    assert scenario._parse_json_field(pre_parsed) == pre_parsed

    # Test broken JSON (should be robust and return empty list)
    assert scenario._parse_json_field("{broken_json") == []

def test_scenario_to_dict_structure():
    """Test that to_dict returns the expected structure with parsed fields."""
    scenario = Scenario(
        id=1,
        title="Test Scenario",
        category="Test",
        steps='[{"step": 1}]',
        required_response='["Run"]',
        # Leave others as defaults
    )
    
    data = scenario.to_dict()
    
    # Check core fields
    assert data["id"] == 1
    assert data["title"] == "Test Scenario"
    
    # Check JSON parsing in to_dict
    assert isinstance(data["steps"], list)
    assert data["steps"][0]["step"] == 1
    assert isinstance(data["required_response"], list)
    assert data["required_response"][0] == "Run"
    
    # Check validation field (default empty)
    assert isinstance(data["validation"], list)
    assert len(data["validation"]) == 0

def test_scenario_initialization_defaults():
    """Ensure default values are handled correctly via __init__ and to_dict().
    
    We added logic to __init__ to prevent None values in JSON fields.
    """
    scenario = Scenario()
    
    # Raw attributes should now be initialized to defaults
    assert scenario.steps == "[]"
    assert scenario.status == "pending"
    
    # Check parsing defaults via to_dict
    data = scenario.to_dict()
    
    # JSON fields should parse correctly from the default "[]"
    assert data["steps"] == []
    
    assert data["status"] == "pending"

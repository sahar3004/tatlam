"""
Integration tests for scenario export functionality.

Tests JSON export and data serialization.
Target: Export scenarios to JSON format.
"""

import pytest
import json


@pytest.mark.integration
class TestExport:
    """Test suite for scenario export."""

    def test_export_single_scenario(self, in_memory_db, sample_scenario_data):
        """Test exporting a single scenario to JSON."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        insert_scenario(sample_scenario_data)
        scenarios = fetch_all()

        # Export to JSON
        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)

        assert json_output is not None
        assert len(json_output) > 0

        # Verify it's valid JSON
        parsed = json.loads(json_output)
        assert isinstance(parsed, list)
        assert len(parsed) >= 1

    def test_export_preserves_hebrew(self, in_memory_db):
        """Test that exported JSON preserves Hebrew characters."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        hebrew_scenario = {
            "title": "תרחיש בעברית עם ניקוד: שָׁלוֹם",
            "category": "חפץ חשוד ומטען",  # Valid CATS category
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד בעברית"}]
        }

        insert_scenario(hebrew_scenario)
        scenarios = fetch_all()

        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)

        # Verify Hebrew is preserved (not escaped)
        assert "עברית" in json_output
        assert "חפץ חשוד ומטען" in json_output

    def test_export_multiple_scenarios(self, in_memory_db, sample_scenario_data):
        """Test exporting multiple scenarios."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        # Insert multiple scenarios
        for i in range(5):
            scenario = {**sample_scenario_data, "title": f"תרחיש {i+1}"}
            insert_scenario(scenario)

        scenarios = fetch_all()
        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)

        parsed = json.loads(json_output)
        assert len(parsed) >= 5

    def test_export_with_all_fields(self, in_memory_db):
        """Test exporting scenario with all optional fields."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        complete_scenario = {
            "title": "תרחיש מלא",
            "category": "בני ערובה",  # Valid CATS category
            "difficulty": "קל",
            "bundle": "חבילה 1",
            "steps": [
                {"step": 1, "description": "צעד 1"},
                {"step": 2, "description": "צעד 2"}
            ],
            "expected_behavior": "התנהגות צפויה",
            "testing_tips": "טיפים לבדיקה"
        }

        insert_scenario(complete_scenario)
        scenarios = fetch_all()

        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)
        parsed = json.loads(json_output)

        # Find our scenario
        exported_scenario = None
        for s in parsed:
            if s.get("title") == "תרחיש מלא":
                exported_scenario = s
                break

        assert exported_scenario is not None

    def test_export_steps_structure(self, in_memory_db, sample_scenario_data):
        """Test that steps array is properly exported."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        insert_scenario(sample_scenario_data)
        scenarios = fetch_all()

        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)
        parsed = json.loads(json_output)

        # Check steps structure
        first_scenario = parsed[0]

        # Steps might be a JSON string or already parsed array
        steps = first_scenario["steps"]
        if isinstance(steps, str):
            steps = json.loads(steps)

        assert isinstance(steps, list)
        assert len(steps) > 0
        assert "step" in steps[0]
        assert "description" in steps[0]

    def test_export_by_category(self, in_memory_db):
        """Test exporting scenarios filtered by category."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        # Use valid CATS categories
        categories = ["פיגועים פשוטים", "חפץ חשוד ומטען", "בני ערובה"]

        for category in categories:
            for i in range(2):
                insert_scenario({
                    "title": f"תרחיש {category} {i}",
                    "category": category,
                    "difficulty": "בינוני",
                    "steps": [{"step": 1, "description": "צעד"}]
                })

        all_scenarios = fetch_all()

        # Filter by category
        attack_scenarios = [s for s in all_scenarios if s.get("category") == "פיגועים פשוטים"]

        json_output = json.dumps(attack_scenarios, ensure_ascii=False, indent=2)
        parsed = json.loads(json_output)

        # Verify all are attack scenarios
        for scenario in parsed:
            assert scenario["category"] == "פיגועים פשוטים"

    def test_export_by_bundle(self, in_memory_db):
        """Test exporting scenarios from a specific bundle."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        bundle_name = "חבילת ייצוא"

        for i in range(3):
            insert_scenario({
                "title": f"תרחיש bundle {i}",
                "category": "פיגועים פשוטים",  # Valid CATS category
                "difficulty": "בינוני",
                "bundle_id": bundle_name,
                "steps": [{"step": 1, "description": "צעד"}]
            })

        all_scenarios = fetch_all()
        bundle_scenarios = [s for s in all_scenarios if s.get("bundle_id") == bundle_name]

        json_output = json.dumps(bundle_scenarios, ensure_ascii=False, indent=2)
        parsed = json.loads(json_output)

        assert len(parsed) >= 3

        for scenario in parsed:
            assert scenario["bundle_id"] == bundle_name

    def test_export_empty_database(self, in_memory_db):
        """Test exporting from empty database."""
        from tatlam.infra.repo import fetch_all

        scenarios = fetch_all()
        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)

        parsed = json.loads(json_output)
        assert isinstance(parsed, list)

    def test_export_special_characters(self, in_memory_db):
        """Test export handles special characters correctly."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        scenario_with_special = {
            "title": "תרחיש עם \"מרכאות\" ו-'גרשיים'",
            "category": "פיגועים פשוטים",  # Valid CATS category
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד עם \n שורה חדשה"}]
        }

        insert_scenario(scenario_with_special)
        scenarios = fetch_all()

        # Should not crash
        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)
        parsed = json.loads(json_output)

        assert parsed is not None

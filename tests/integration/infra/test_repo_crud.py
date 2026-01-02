"""
Integration tests for tatlam/infra/repo.py

Tests CRUD operations (Create, Read, Update, Delete).
Target: insert_scenario(), fetch_all(), normalize_row().
"""

import pytest
import json


@pytest.mark.integration
class TestRepositoryCRUD:
    """Test suite for repository CRUD operations."""

    def test_insert_scenario_basic(self, in_memory_db, sample_scenario_data):
        """Test inserting a scenario into database."""
        from tatlam.infra.repo import insert_scenario

        scenario_id = insert_scenario(sample_scenario_data)

        assert scenario_id is not None
        assert isinstance(scenario_id, int)
        assert scenario_id > 0

    def test_insert_scenario_with_hebrew(self, in_memory_db):
        """Test inserting scenario with Hebrew content."""
        from tatlam.infra.repo import insert_scenario

        hebrew_scenario = {
            "title": "בדיקת הכנסת עברית",
            "category": "פיגועים פשוטים",  # Valid CATS category
            "difficulty": "קשה",
            "bundle_id": "חבילת בדיקה",
            "steps": [
                {"step": 1, "description": "פתח את היישום"},
                {"step": 2, "description": "בחר באפשרות תשלום"},
            ],
            "expected_behavior": "המשתמש יוכל להשלים תשלום",
            "testing_tips": "בדוק טיפול בשגיאות",
        }

        scenario_id = insert_scenario(hebrew_scenario)
        assert scenario_id is not None

        # Verify data was stored correctly
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT title, category FROM scenarios WHERE id = ?", (scenario_id,))
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == "בדיקת הכנסת עברית"
        assert result[1] == "פיגועים פשוטים"

    def test_insert_scenario_preserves_json_structure(self, in_memory_db, sample_scenario_data):
        """Test that steps array is properly stored as JSON."""
        from tatlam.infra.repo import insert_scenario

        scenario_id = insert_scenario(sample_scenario_data)

        cursor = in_memory_db.cursor()
        cursor.execute("SELECT steps FROM scenarios WHERE id = ?", (scenario_id,))
        result = cursor.fetchone()

        assert result is not None

        # Parse JSON
        steps = json.loads(result[0])
        assert isinstance(steps, list)
        assert len(steps) == len(sample_scenario_data["steps"])
        assert steps[0]["description"] == sample_scenario_data["steps"][0]["description"]

    def test_fetch_all_scenarios(self, in_memory_db, sample_scenario_data):
        """Test fetching all scenarios from database."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        # Insert multiple scenarios
        insert_scenario(sample_scenario_data)
        insert_scenario({**sample_scenario_data, "title": "תרחיש שני"})
        insert_scenario({**sample_scenario_data, "title": "תרחיש שלישי"})

        # Fetch all
        scenarios = fetch_all()

        assert scenarios is not None
        assert len(scenarios) >= 3

    def test_fetch_all_returns_normalized_rows(self, in_memory_db, sample_scenario_data):
        """Test that fetch_all returns normalized dictionaries."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        insert_scenario(sample_scenario_data)

        scenarios = fetch_all()

        assert len(scenarios) > 0

        # Check that results are dictionaries (normalized)
        first_scenario = scenarios[0]
        assert isinstance(first_scenario, dict)
        assert "id" in first_scenario
        assert "title" in first_scenario

    def test_fetch_all_preserves_hebrew(self, in_memory_db):
        """Test that fetch_all preserves Hebrew characters."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        hebrew_title = "בדיקת שמירת עברית"
        scenario = {
            "title": hebrew_title,
            "category": "חפץ חשוד ומטען",  # Valid CATS category
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד בעברית"}],
        }

        insert_scenario(scenario)
        scenarios = fetch_all()

        # Find our scenario
        found = False
        for s in scenarios:
            if s.get("title") == hebrew_title:
                found = True
                assert s["category"] == "חפץ חשוד ומטען"
                break

        assert found, "Scenario with Hebrew title not found in fetch_all results"

    def test_insert_scenario_with_all_fields(self, in_memory_db):
        """Test inserting scenario with all optional fields."""
        from tatlam.infra.repo import insert_scenario

        complete_scenario = {
            "title": "תרחיש מלא crud",
            "category": "בני ערובה",  # Valid CATS category
            "difficulty": "קל",
            "bundle_id": "חבילה 1",
            "steps": [
                {"step": 1, "description": "צעד 1"},
                {"step": 2, "description": "צעד 2"},
                {"step": 3, "description": "צעד 3"},
            ],
            "expected_behavior": "התנהגות צפויה",
            "testing_tips": "טיפים לבדיקה",
        }

        scenario_id = insert_scenario(complete_scenario)
        assert scenario_id is not None

    def test_insert_multiple_scenarios_different_categories(self, in_memory_db):
        """Test inserting scenarios from different categories."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        # Use valid CATS categories
        categories = ["פיגועים פשוטים", "חפץ חשוד ומטען", "בני ערובה", "אירוע כימי", "תחנות עיליות"]

        for i, category in enumerate(categories):
            scenario = {
                "title": f"תרחיש category {i+1}",
                "category": category,
                "difficulty": "בינוני",
                "steps": [{"step": 1, "description": f"צעד עבור {category}"}],
            }
            insert_scenario(scenario)

        scenarios = fetch_all()
        assert len(scenarios) >= len(categories)

        # Verify categories are preserved
        stored_categories = [s["category"] for s in scenarios]
        for cat in categories:
            assert cat in stored_categories

    def test_normalize_row_integration(self, in_memory_db, sample_scenario_data):
        """Test normalize_row with actual database rows."""
        from tatlam.infra.repo import insert_scenario, normalize_row

        scenario_id = insert_scenario(sample_scenario_data)

        # Fetch raw row
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
        raw_row = cursor.fetchone()

        # Normalize
        normalized = normalize_row(raw_row)

        assert isinstance(normalized, dict)
        assert normalized["id"] == scenario_id
        assert normalized["title"] == sample_scenario_data["title"]

    def test_insert_scenario_returns_incrementing_ids(self, in_memory_db, sample_scenario_data):
        """Test that insert_scenario returns incrementing IDs."""
        from tatlam.infra.repo import insert_scenario

        id1 = insert_scenario(sample_scenario_data)
        id2 = insert_scenario({**sample_scenario_data, "title": "תרחיש 2"})
        id3 = insert_scenario({**sample_scenario_data, "title": "תרחיש 3"})

        assert id2 > id1
        assert id3 > id2

    def test_fetch_all_empty_database(self, in_memory_db):
        """Test fetch_all with empty database."""
        from tatlam.infra.repo import fetch_all

        scenarios = fetch_all()

        assert scenarios is not None
        assert isinstance(scenarios, list)
        # May be empty or have default data

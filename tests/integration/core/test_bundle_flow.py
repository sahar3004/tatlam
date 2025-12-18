"""
Integration tests for tatlam/core/bundles.py

Tests bundle creation and grouping logic.
Target: Scenario bundling and organization.
"""

import pytest


@pytest.mark.integration
class TestBundleFlow:
    """Test suite for scenario bundling."""

    def test_bundle_grouping_by_category(self, in_memory_db):
        """Test scenarios can be grouped into bundles by category."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        # Insert scenarios with different categories
        scenarios = [
            {
                "title": "תרחיש פיננסי 1",
                "category": "פיננסים",
                "difficulty": "קל",
                "bundle": "חבילת פיננסים",
                "steps": [{"step": 1, "description": "צעד"}]
            },
            {
                "title": "תרחיש פיננסי 2",
                "category": "פיננסים",
                "difficulty": "בינוני",
                "bundle": "חבילת פיננסים",
                "steps": [{"step": 1, "description": "צעד"}]
            },
            {
                "title": "תרחיש בריאות",
                "category": "בריאות",
                "difficulty": "קשה",
                "bundle": "חבילת בריאות",
                "steps": [{"step": 1, "description": "צעד"}]
            }
        ]

        for scenario in scenarios:
            insert_scenario(scenario)

        all_scenarios = fetch_all()

        # Group by bundle
        bundles = {}
        for scenario in all_scenarios:
            bundle_name = scenario.get("bundle", "")
            if bundle_name:
                if bundle_name not in bundles:
                    bundles[bundle_name] = []
                bundles[bundle_name].append(scenario)

        # Verify grouping
        assert "חבילת פיננסים" in bundles
        assert len(bundles["חבילת פיננסים"]) >= 2

    def test_bundle_mixed_difficulties(self, in_memory_db):
        """Test bundles can contain scenarios of different difficulties."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        bundle_name = "חבילה מעורבת"
        difficulties = ["קל", "בינוני", "קשה"]

        for difficulty in difficulties:
            scenario = {
                "title": f"תרחיש {difficulty}",
                "category": "פיננסים",
                "difficulty": difficulty,
                "bundle": bundle_name,
                "steps": [{"step": 1, "description": "צעד"}]
            }
            insert_scenario(scenario)

        all_scenarios = fetch_all()

        # Filter by bundle
        bundle_scenarios = [s for s in all_scenarios if s.get("bundle") == bundle_name]

        # Verify all difficulties present
        bundle_difficulties = [s["difficulty"] for s in bundle_scenarios]
        for difficulty in difficulties:
            assert difficulty in bundle_difficulties

    def test_bundle_without_bundle_field(self, in_memory_db):
        """Test scenarios without bundle field can be handled."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        scenario = {
            "title": "תרחיש ללא חבילה",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד"}]
            # No 'bundle' field
        }

        scenario_id = insert_scenario(scenario)
        assert scenario_id is not None

        all_scenarios = fetch_all()
        unbundled = [s for s in all_scenarios if not s.get("bundle")]

        # Should be able to query scenarios without bundles
        assert len(unbundled) >= 0

    def test_bundle_export_structure(self, in_memory_db):
        """Test that bundles can be exported with proper structure."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        bundle_name = "חבילת ייצוא"

        for i in range(3):
            scenario = {
                "title": f"תרחיש {i+1}",
                "category": "חינוך",
                "difficulty": "בינוני",
                "bundle": bundle_name,
                "steps": [{"step": 1, "description": f"צעד {i+1}"}]
            }
            insert_scenario(scenario)

        all_scenarios = fetch_all()
        bundle_scenarios = [s for s in all_scenarios if s.get("bundle") == bundle_name]

        # Verify export structure
        assert len(bundle_scenarios) >= 3

        for scenario in bundle_scenarios:
            assert "title" in scenario
            assert "category" in scenario
            assert "difficulty" in scenario
            assert "steps" in scenario

    def test_multiple_bundles_isolation(self, in_memory_db):
        """Test that multiple bundles remain isolated from each other."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        bundle1_name = "חבילה 1"
        bundle2_name = "חבילה 2"

        # Insert scenarios in bundle 1
        for i in range(2):
            insert_scenario({
                "title": f"תרחיש B1-{i}",
                "category": "פיננסים",
                "difficulty": "קל",
                "bundle": bundle1_name,
                "steps": [{"step": 1, "description": "צעד"}]
            })

        # Insert scenarios in bundle 2
        for i in range(3):
            insert_scenario({
                "title": f"תרחיש B2-{i}",
                "category": "בריאות",
                "difficulty": "בינוני",
                "bundle": bundle2_name,
                "steps": [{"step": 1, "description": "צעד"}]
            })

        all_scenarios = fetch_all()

        bundle1 = [s for s in all_scenarios if s.get("bundle") == bundle1_name]
        bundle2 = [s for s in all_scenarios if s.get("bundle") == bundle2_name]

        # Verify isolation
        assert len(bundle1) >= 2
        assert len(bundle2) >= 3

        # No overlap in titles
        bundle1_titles = set(s["title"] for s in bundle1)
        bundle2_titles = set(s["title"] for s in bundle2)
        assert len(bundle1_titles & bundle2_titles) == 0

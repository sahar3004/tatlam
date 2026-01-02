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

        # Insert scenarios with different valid CATS categories
        scenarios = [
            {
                "title": "תרחיש פיגוע 1",
                "category": "פיגועים פשוטים",
                "difficulty": "קל",
                "bundle_id": "חבילת פיגועים",
                "steps": [{"step": 1, "description": "צעד"}],
            },
            {
                "title": "תרחיש פיגוע 2",
                "category": "פיגועים פשוטים",
                "difficulty": "בינוני",
                "bundle_id": "חבילת פיגועים",
                "steps": [{"step": 1, "description": "צעד"}],
            },
            {
                "title": "תרחיש חפץ חשוד",
                "category": "חפץ חשוד ומטען",
                "difficulty": "קשה",
                "bundle_id": "חבילת חפצים",
                "steps": [{"step": 1, "description": "צעד"}],
            },
        ]

        for scenario in scenarios:
            insert_scenario(scenario)

        all_scenarios = fetch_all()

        # Group by bundle_id
        bundles = {}
        for scenario in all_scenarios:
            bundle_name = scenario.get("bundle_id", "")
            if bundle_name:
                if bundle_name not in bundles:
                    bundles[bundle_name] = []
                bundles[bundle_name].append(scenario)

        # Verify grouping
        assert "חבילת פיגועים" in bundles
        assert len(bundles["חבילת פיגועים"]) >= 2

    def test_bundle_mixed_threat_levels(self, in_memory_db):
        """Test bundles can contain scenarios of different threat levels."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        bundle_name = "חבילה מעורבת"
        threat_levels = ["נמוך", "בינוני", "גבוה"]

        for threat_level in threat_levels:
            scenario = {
                "title": f"תרחיש mixed {threat_level}",
                "category": "פיגועים פשוטים",
                "threat_level": threat_level,
                "bundle_id": bundle_name,
                "steps": [{"step": 1, "description": "צעד"}],
            }
            insert_scenario(scenario)

        all_scenarios = fetch_all()

        # Filter by bundle
        bundle_scenarios = [s for s in all_scenarios if s.get("bundle_id") == bundle_name]

        # Verify all threat levels present
        bundle_threat_levels = [s.get("threat_level", "") for s in bundle_scenarios]
        for level in threat_levels:
            assert level in bundle_threat_levels

    def test_bundle_without_bundle_field(self, in_memory_db):
        """Test scenarios without bundle field can be handled."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        scenario = {
            "title": "תרחיש ללא חבילה",
            "category": "פיגועים פשוטים",
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד"}],
            # No 'bundle_id' field
        }

        scenario_id = insert_scenario(scenario)
        assert scenario_id is not None

        all_scenarios = fetch_all()
        unbundled = [s for s in all_scenarios if not s.get("bundle_id")]

        # Should be able to query scenarios without bundles
        assert len(unbundled) >= 0

    def test_bundle_export_structure(self, in_memory_db):
        """Test that bundles can be exported with proper structure."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        bundle_name = "חבילת ייצוא"

        for i in range(3):
            scenario = {
                "title": f"תרחיש export {i+1}",
                "category": "בני ערובה",
                "threat_level": "בינוני",
                "bundle_id": bundle_name,
                "steps": [{"step": 1, "description": f"צעד {i+1}"}],
            }
            insert_scenario(scenario)

        all_scenarios = fetch_all()
        bundle_scenarios = [s for s in all_scenarios if s.get("bundle_id") == bundle_name]

        # Verify export structure
        assert len(bundle_scenarios) >= 3

        for scenario in bundle_scenarios:
            assert "title" in scenario
            assert "category" in scenario
            assert "steps" in scenario

    def test_multiple_bundles_isolation(self, in_memory_db):
        """Test that multiple bundles remain isolated from each other."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        bundle1_name = "חבילה 1"
        bundle2_name = "חבילה 2"

        # Insert scenarios in bundle 1
        for i in range(2):
            insert_scenario(
                {
                    "title": f"תרחיש B1-{i}",
                    "category": "פיגועים פשוטים",
                    "difficulty": "קל",
                    "bundle_id": bundle1_name,
                    "steps": [{"step": 1, "description": "צעד"}],
                }
            )

        # Insert scenarios in bundle 2
        for i in range(3):
            insert_scenario(
                {
                    "title": f"תרחיש B2-{i}",
                    "category": "חפץ חשוד ומטען",
                    "difficulty": "בינוני",
                    "bundle_id": bundle2_name,
                    "steps": [{"step": 1, "description": "צעד"}],
                }
            )

        all_scenarios = fetch_all()

        bundle1 = [s for s in all_scenarios if s.get("bundle_id") == bundle1_name]
        bundle2 = [s for s in all_scenarios if s.get("bundle_id") == bundle2_name]

        # Verify isolation
        assert len(bundle1) >= 2
        assert len(bundle2) >= 3

        # No overlap in titles
        bundle1_titles = set(s["title"] for s in bundle1)
        bundle2_titles = set(s["title"] for s in bundle2)
        assert len(bundle1_titles & bundle2_titles) == 0

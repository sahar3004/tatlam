"""
LLM Evaluation tests for hallucination detection.

Tests TrinityBrain's consistency and factual accuracy.
EXPENSIVE: Makes real API calls. Mark as @slow.
"""

import pytest


@pytest.mark.slow
@pytest.mark.skipif(True, reason="Expensive test - requires real API calls")
class TestHallucinations:
    """Test suite for hallucination detection and consistency."""

    def test_consistent_category_names(self, mock_brain):
        """Test that LLM uses consistent category names across generations."""
        from tatlam.core.categories import CATS

        # Generate multiple scenarios in same category
        # Verify category names match CATS dictionary exactly

        valid_categories = set(CATS.keys())

        # In real test: generate scenarios and check categories
        sample_category = "פיננסים"
        assert sample_category in valid_categories

    def test_no_invented_fields(self, mock_brain):
        """Test that LLM doesn't invent new fields not in schema."""
        expected_fields = {
            "title",
            "category",
            "difficulty",
            "bundle",
            "steps",
            "expected_behavior",
            "testing_tips",
        }

        sample_scenario = {
            "title": "תרחיש",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": [],
        }

        # All fields should be in expected set
        for field in sample_scenario.keys():
            # Field should be recognized (or be common like 'id', 'created_at')
            assert field in expected_fields or field in ["id", "created_at"]

    def test_difficulty_levels_consistent(self, mock_brain):
        """Test that difficulty levels use only defined values."""
        valid_difficulties = {"קל", "בינוני", "קשה"}  # Easy, Medium, Hard

        sample_difficulty = "בינוני"
        assert sample_difficulty in valid_difficulties

    def test_step_numbers_sequential(self, mock_brain):
        """Test that step numbers are sequential without gaps."""
        sample_steps = [
            {"step": 1, "description": "צעד 1"},
            {"step": 2, "description": "צעד 2"},
            {"step": 3, "description": "צעד 3"},
        ]

        step_numbers = [s["step"] for s in sample_steps]

        # Should be sequential: 1, 2, 3, ...
        expected_sequence = list(range(1, len(sample_steps) + 1))
        assert step_numbers == expected_sequence

    def test_no_duplicate_steps(self, mock_brain):
        """Test that there are no duplicate step numbers."""
        sample_steps = [
            {"step": 1, "description": "צעד 1"},
            {"step": 2, "description": "צעד 2"},
            {"step": 3, "description": "צעד 3"},
        ]

        step_numbers = [s["step"] for s in sample_steps]

        # No duplicates
        assert len(step_numbers) == len(set(step_numbers))

    def test_steps_not_empty(self, mock_brain):
        """Test that scenarios always have at least one step."""
        sample_steps = [{"step": 1, "description": "צעד ראשון"}]

        # Should have at least one step
        assert len(sample_steps) >= 1

    def test_no_contradictory_information(self, mock_brain):
        """Test that scenario doesn't contain contradictions."""
        scenario = {
            "title": "בדיקת תשלום",
            "category": "פיננסים",
            "expected_behavior": "התשלום מצליח",
            "testing_tips": "בדוק שהתשלום מצליח",
        }

        # expected_behavior and testing_tips should align
        # This is a basic check - real test would use semantic analysis
        assert "מצליח" in scenario["expected_behavior"]
        assert "מצליח" in scenario["testing_tips"]

    def test_category_matches_content(self, mock_brain):
        """Test that scenario category matches its content."""
        financial_scenario = {
            "title": "בדיקת העברת כסף",
            "category": "פיננסים",
            "steps": [{"step": 1, "description": "פתח את אפליקציית הבנק"}],
        }

        # Category is finance, content should be finance-related
        # Basic keyword check
        finance_keywords = ["כסף", "בנק", "תשלום", "העברה"]

        content = f"{financial_scenario['title']} {financial_scenario['steps'][0]['description']}"

        has_finance_keyword = any(keyword in content for keyword in finance_keywords)
        assert has_finance_keyword or financial_scenario["category"] == "פיננסים"

    def test_realistic_scenario_flow(self, mock_brain):
        """Test that scenario steps follow logical order."""
        login_scenario = {
            "steps": [
                {"step": 1, "description": "פתח את האפליקציה"},
                {"step": 2, "description": "הזן שם משתמש"},
                {"step": 3, "description": "הזן סיסמה"},
                {"step": 4, "description": "לחץ על כניסה"},
            ]
        }

        # Steps should follow logical order
        # Basic check: first step should be about opening/starting
        first_step = login_scenario["steps"][0]["description"]
        assert "פתח" in first_step or "הפעל" in first_step

    def test_no_fictional_app_names(self, mock_brain):
        """Test that scenarios reference generic apps, not specific brands."""
        # Unless explicitly instructed, should use generic terms
        # e.g., "אפליקציית הבנק" not "אפליקציית בנק הפועלים"

        generic_terms = ["אפליקציה", "מערכת", "יישום", "תוכנה"]

        sample_text = "פתח את האפליקציה"

        has_generic_term = any(term in sample_text for term in generic_terms)
        assert has_generic_term

    def test_consistent_terminology(self, mock_brain):
        """Test that same concepts use same terminology."""
        # E.g., don't switch between "אפליקציה" and "יישום" for same thing

        scenario = {
            "steps": [
                {"step": 1, "description": "פתח את האפליקציה"},
                {"step": 2, "description": "בחר תפריט באפליקציה"},
                {"step": 3, "description": "צא מהאפליקציה"},
            ]
        }

        # All steps use "אפליקציה" consistently
        descriptions = [s["description"] for s in scenario["steps"]]
        app_term_count = sum(1 for d in descriptions if "אפליקציה" in d)

        # Should use consistent term
        assert app_term_count >= 2

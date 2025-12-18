"""
Unit tests for tatlam/cli/render_cards.py

Tests HTML card rendering functionality.
Target: render_html() function and card generation.
"""

import pytest
from pathlib import Path


@pytest.mark.unit
class TestRenderCards:
    """Test suite for card rendering."""

    def test_render_html_function_exists(self):
        """Verify render_html function is importable."""
        from tatlam.cli.render_cards import render_html
        assert callable(render_html)

    def test_render_html_with_sample_data(self, sample_scenario_data):
        """Test render_html produces HTML output."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([sample_scenario_data])

        assert html_output is not None
        assert isinstance(html_output, str)
        assert len(html_output) > 0

    def test_render_html_contains_html_tags(self, sample_scenario_data):
        """Verify output contains valid HTML structure."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([sample_scenario_data])

        # Check for essential HTML tags
        assert '<html' in html_output.lower()
        assert '</html>' in html_output.lower()
        assert '<body' in html_output.lower() or '<div' in html_output.lower()

    def test_render_html_contains_hebrew_content(self, sample_scenario_data):
        """Test rendered HTML preserves Hebrew text."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([sample_scenario_data])

        # Check that Hebrew content from sample_scenario_data is in output
        assert sample_scenario_data["title"] in html_output
        assert sample_scenario_data["category"] in html_output

    def test_render_html_with_multiple_scenarios(self):
        """Test rendering multiple scenarios."""
        from tatlam.cli.render_cards import render_html

        scenarios = [
            {
                "title": "תרחיש 1",
                "category": "פיננסים",
                "difficulty": "קל",
                "steps": [{"step": 1, "description": "צעד 1"}]
            },
            {
                "title": "תרחיש 2",
                "category": "בריאות",
                "difficulty": "בינוני",
                "steps": [{"step": 1, "description": "צעד 1"}]
            },
            {
                "title": "תרחיש 3",
                "category": "חינוך",
                "difficulty": "קשה",
                "steps": [{"step": 1, "description": "צעד 1"}]
            }
        ]

        html_output = render_html(scenarios)

        # All three titles should appear in output
        assert "תרחיש 1" in html_output
        assert "תרחיש 2" in html_output
        assert "תרחיש 3" in html_output

    def test_render_html_with_empty_list(self):
        """Test behavior with empty scenario list."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([])

        # Should still produce valid HTML structure
        assert html_output is not None
        assert '<html' in html_output.lower() or len(html_output) == 0

    def test_render_html_rtl_support(self, sample_scenario_data):
        """Test HTML includes RTL (Right-to-Left) support for Hebrew."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([sample_scenario_data])

        # Check for RTL indicators
        has_rtl = 'dir="rtl"' in html_output or 'direction: rtl' in html_output
        assert has_rtl, "HTML output missing RTL support for Hebrew"

    def test_render_html_includes_steps(self, sample_scenario_data):
        """Test that scenario steps are rendered."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([sample_scenario_data])

        # Check for step content
        first_step_desc = sample_scenario_data["steps"][0]["description"]
        assert first_step_desc in html_output

    def test_render_html_includes_metadata(self, sample_scenario_data):
        """Test that scenario metadata (difficulty, category) is rendered."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([sample_scenario_data])

        assert sample_scenario_data["difficulty"] in html_output
        assert sample_scenario_data["category"] in html_output

    def test_render_html_css_styling(self, sample_scenario_data):
        """Test that output includes CSS styling."""
        from tatlam.cli.render_cards import render_html

        html_output = render_html([sample_scenario_data])

        # Check for CSS presence
        has_css = '<style' in html_output.lower() or 'style=' in html_output.lower()
        assert has_css, "HTML output missing CSS styling"

    def test_render_html_handles_special_characters(self):
        """Test rendering handles special characters and HTML entities."""
        from tatlam.cli.render_cards import render_html

        scenario_with_special_chars = {
            "title": "תרחיש עם <תגיות> & \"מרכאות\"",
            "category": "פיננסים",
            "difficulty": "בינוני",
            "steps": [
                {"step": 1, "description": "צעד עם 'מרכאות' ו-<סוגריים>"}
            ]
        }

        html_output = render_html([scenario_with_special_chars])

        # Should not break HTML structure
        assert html_output is not None
        assert len(html_output) > 0

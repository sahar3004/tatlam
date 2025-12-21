"""
Unit tests for tatlam/cli/render_cards.py

Tests HTML card rendering functionality.
Target: render_html() function and card generation.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestJsonToList:
    """Test _json_to_list helper function."""

    def test_returns_list_unchanged(self) -> None:
        """Test list input is returned as-is."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list([1, 2, 3])
        assert result == [1, 2, 3]

    def test_returns_empty_list_for_none(self) -> None:
        """Test None returns empty list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list(None)
        assert result == []

    def test_parses_json_string_to_list(self) -> None:
        """Test JSON string list is parsed."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_wraps_json_string_object_in_list(self) -> None:
        """Test JSON object is wrapped in list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list('{"key": "value"}')
        assert result == [{"key": "value"}]

    def test_wraps_plain_string_in_list(self) -> None:
        """Test plain string is wrapped in list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list("just a string")
        assert result == ["just a string"]

    def test_returns_empty_for_empty_string(self) -> None:
        """Test empty string returns empty list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list("")
        assert result == []

    def test_returns_empty_for_null_string(self) -> None:
        """Test 'null' string returns empty list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list("null")
        assert result == []

    def test_returns_empty_for_none_string(self) -> None:
        """Test 'none' string returns empty list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list("none")
        assert result == []

    def test_returns_empty_for_brackets_string(self) -> None:
        """Test '[]' string returns empty list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list("[]")
        assert result == []

    def test_wraps_int_in_list(self) -> None:
        """Test integer is wrapped in list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list(42)
        assert result == [42]

    def test_wraps_dict_in_list(self) -> None:
        """Test dict is wrapped in list."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list({"key": "value"})
        assert result == [{"key": "value"}]

    def test_invalid_json_wrapped_in_list(self) -> None:
        """Test invalid JSON string is wrapped as string."""
        from tatlam.cli.render_cards import _json_to_list

        result = _json_to_list("{not valid json}")
        assert result == ["{not valid json}"]


@pytest.mark.unit
class TestNoneIfBlank:
    """Test _none_if_blank helper function."""

    def test_returns_none_for_none(self) -> None:
        """Test None input returns None."""
        from tatlam.cli.render_cards import _none_if_blank

        result = _none_if_blank(None)
        assert result is None

    def test_returns_none_for_empty_string(self) -> None:
        """Test empty string returns None."""
        from tatlam.cli.render_cards import _none_if_blank

        result = _none_if_blank("")
        assert result is None

    def test_returns_none_for_whitespace(self) -> None:
        """Test whitespace returns None."""
        from tatlam.cli.render_cards import _none_if_blank

        result = _none_if_blank("   ")
        assert result is None

    def test_returns_stripped_string(self) -> None:
        """Test non-blank string is stripped and returned."""
        from tatlam.cli.render_cards import _none_if_blank

        result = _none_if_blank("  hello  ")
        assert result == "hello"


@pytest.mark.unit
class TestCoerceRowTypes:
    """Test coerce_row_types function."""

    def test_coerces_json_list_fields(self) -> None:
        """Test JSON list fields are coerced."""
        from tatlam.cli.render_cards import coerce_row_types

        row = {"steps": '[{"step": 1}]'}
        result = coerce_row_types(row)
        assert result["steps"] == [{"step": 1}]

    def test_sets_default_title(self) -> None:
        """Test default title is set."""
        from tatlam.cli.render_cards import coerce_row_types

        result = coerce_row_types({})
        assert result["title"] == "ללא כותרת"

    def test_sets_default_category(self) -> None:
        """Test default category is set."""
        from tatlam.cli.render_cards import coerce_row_types

        result = coerce_row_types({})
        assert result["category"] == "לא מסווג"

    def test_normalizes_mask_usage_yes(self) -> None:
        """Test mask_usage normalization to yes."""
        from tatlam.cli.render_cards import coerce_row_types

        for val in ["yes", "true", "y", "כן", "YES", "True"]:
            result = coerce_row_types({"mask_usage": val})
            assert result["mask_usage"] == "כן"

    def test_normalizes_mask_usage_no(self) -> None:
        """Test mask_usage normalization to no."""
        from tatlam.cli.render_cards import coerce_row_types

        for val in ["no", "false", "n", "לא", "NO", "False"]:
            result = coerce_row_types({"mask_usage": val})
            assert result["mask_usage"] == "לא"

    def test_normalizes_mask_usage_other(self) -> None:
        """Test mask_usage normalization for other values."""
        from tatlam.cli.render_cards import coerce_row_types

        result = coerce_row_types({"mask_usage": "maybe"})
        assert result["mask_usage"] is None

    def test_normalizes_mask_usage_none(self) -> None:
        """Test mask_usage normalization for None."""
        from tatlam.cli.render_cards import coerce_row_types

        result = coerce_row_types({"mask_usage": None})
        assert result["mask_usage"] is None

    def test_media_link_blank_to_none(self) -> None:
        """Test blank media_link becomes None."""
        from tatlam.cli.render_cards import coerce_row_types

        result = coerce_row_types({"media_link": "   "})
        assert result["media_link"] is None


@pytest.mark.unit
class TestLoadTemplate:
    """Test load_template function."""

    def test_loads_default_template(self) -> None:
        """Test loading the default template."""
        from tatlam.cli.render_cards import load_template, DEFAULT_TEMPLATE_PATH

        if DEFAULT_TEMPLATE_PATH.exists():
            template = load_template()
            assert template is not None

    def test_loads_custom_template(self) -> None:
        """Test loading a custom template."""
        from tatlam.cli.render_cards import load_template

        with tempfile.NamedTemporaryFile(mode="w", suffix=".j2", delete=False) as f:
            f.write("Hello {{ name }}")
            f.flush()
            template = load_template(f.name)
            assert template is not None
            result = template.render(name="World")
            assert result == "Hello World"
            Path(f.name).unlink()


@pytest.mark.unit
class TestSafeFilename:
    """Test safe_filename function."""

    def test_converts_spaces_to_underscores(self) -> None:
        """Test spaces become underscores."""
        from tatlam.cli.render_cards import safe_filename

        result = safe_filename("hello world")
        assert result == "hello_world"

    def test_removes_special_characters(self) -> None:
        """Test special characters are removed."""
        from tatlam.cli.render_cards import safe_filename

        result = safe_filename("hello@world#test!")
        assert "@" not in result
        assert "#" not in result
        assert "!" not in result

    def test_replaces_slashes(self) -> None:
        """Test slashes become dashes."""
        from tatlam.cli.render_cards import safe_filename

        result = safe_filename("hello/world\\test")
        assert "/" not in result
        assert "\\" not in result

    def test_handles_empty_input(self) -> None:
        """Test empty input returns 'scenario'."""
        from tatlam.cli.render_cards import safe_filename

        result = safe_filename("")
        assert result == "scenario"

    def test_handles_none_input(self) -> None:
        """Test None input returns 'scenario'."""
        from tatlam.cli.render_cards import safe_filename

        result = safe_filename(None)  # type: ignore
        assert result == "scenario"

    def test_preserves_hebrew(self) -> None:
        """Test Hebrew characters are preserved."""
        from tatlam.cli.render_cards import safe_filename

        result = safe_filename("תרחיש בדיקה")
        assert "תרחיש" in result

    def test_collapses_whitespace(self) -> None:
        """Test multiple whitespace collapses."""
        from tatlam.cli.render_cards import safe_filename

        result = safe_filename("hello   world\n\ttest")
        assert "  " not in result


@pytest.mark.unit
class TestUniquePath:
    """Test unique_path function."""

    def test_returns_original_if_not_exists(self) -> None:
        """Test non-existent path returned as-is."""
        from tatlam.cli.render_cards import unique_path

        with tempfile.TemporaryDirectory() as tmpdir:
            result = unique_path(Path(tmpdir), "test.md")
            assert result == Path(tmpdir) / "test.md"

    def test_adds_suffix_if_exists(self) -> None:
        """Test suffix added for existing file."""
        from tatlam.cli.render_cards import unique_path

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "test.md").touch()

            result = unique_path(tmpdir_path, "test.md")
            assert result == tmpdir_path / "test-1.md"

    def test_increments_suffix_for_multiple(self) -> None:
        """Test suffix increments for multiple conflicts."""
        from tatlam.cli.render_cards import unique_path

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            (tmpdir_path / "test.md").touch()
            (tmpdir_path / "test-1.md").touch()

            result = unique_path(tmpdir_path, "test.md")
            assert result == tmpdir_path / "test-2.md"


@pytest.mark.unit
class TestFetch:
    """Test fetch function."""

    @patch("tatlam.cli.render_cards.get_session")
    def test_fetch_no_filter(self, mock_get_session: MagicMock) -> None:
        """Test fetch without filters."""
        from tatlam.cli.render_cards import fetch

        mock_scenario = MagicMock()
        mock_scenario.to_dict.return_value = {"id": 1, "title": "Test"}

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch()
        assert len(result) == 1
        assert result[0]["title"] == "Test"

    @patch("tatlam.cli.render_cards.get_session")
    def test_fetch_by_category(self, mock_get_session: MagicMock) -> None:
        """Test fetch with category filter."""
        from tatlam.cli.render_cards import fetch

        mock_scenario = MagicMock()
        mock_scenario.to_dict.return_value = {"id": 1, "title": "Test"}

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch(category="Test Category")
        assert len(result) == 1

    @patch("tatlam.cli.render_cards.get_session")
    def test_fetch_by_bundle_id(self, mock_get_session: MagicMock) -> None:
        """Test fetch with bundle_id filter."""
        from tatlam.cli.render_cards import fetch

        mock_scenario = MagicMock()
        mock_scenario.to_dict.return_value = {"id": 1, "title": "Test"}

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch(bundle_id="BUNDLE-001")
        assert len(result) == 1

    @patch("tatlam.cli.render_cards.get_session")
    def test_fetch_by_both_filters(self, mock_get_session: MagicMock) -> None:
        """Test fetch with both category and bundle_id filters."""
        from tatlam.cli.render_cards import fetch

        mock_scenario = MagicMock()
        mock_scenario.to_dict.return_value = {"id": 1, "title": "Test"}

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch(category="Cat", bundle_id="BUNDLE-001")
        assert len(result) == 1


@pytest.mark.unit
class TestMain:
    """Test main CLI function."""

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main_basic_export(
        self, mock_load_template: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """Test basic export to directory."""
        from tatlam.cli.render_cards import main

        mock_template = MagicMock()
        mock_template.render.return_value = "# Test\n\nContent"
        mock_load_template.return_value = mock_template

        mock_fetch.return_value = [{"id": 1, "title": "Test Scenario", "category": "Test"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = main(["--out", tmpdir])

            assert result == 0
            files = list(Path(tmpdir).glob("*.md"))
            assert len(files) == 1

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main_with_category_filter(
        self, mock_load_template: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """Test export with category filter."""
        from tatlam.cli.render_cards import main

        mock_template = MagicMock()
        mock_template.render.return_value = "# Test"
        mock_load_template.return_value = mock_template
        mock_fetch.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            main(["--out", tmpdir, "--category", "Test Category"])

            mock_fetch.assert_called_with(category="Test Category", bundle_id=None)

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main_with_bundle_filter(
        self, mock_load_template: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """Test export with bundle filter."""
        from tatlam.cli.render_cards import main

        mock_template = MagicMock()
        mock_template.render.return_value = "# Test"
        mock_load_template.return_value = mock_template
        mock_fetch.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            main(["--out", tmpdir, "--bundle", "BUNDLE-001"])

            mock_fetch.assert_called_with(category=None, bundle_id="BUNDLE-001")

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main_with_limit(
        self, mock_load_template: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """Test export with limit."""
        from tatlam.cli.render_cards import main

        mock_template = MagicMock()
        mock_template.render.return_value = "# Test"
        mock_load_template.return_value = mock_template

        mock_fetch.return_value = [
            {"id": 1, "title": "Test 1"},
            {"id": 2, "title": "Test 2"},
            {"id": 3, "title": "Test 3"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            main(["--out", tmpdir, "--limit", "2"])

            # Should only render 2 files
            assert mock_template.render.call_count == 2

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main_with_prefix_id(
        self, mock_load_template: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """Test export with ID prefix."""
        from tatlam.cli.render_cards import main

        mock_template = MagicMock()
        mock_template.render.return_value = "# Test"
        mock_load_template.return_value = mock_template

        mock_fetch.return_value = [{"id": 42, "title": "Test Scenario"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            main(["--out", tmpdir, "--prefix-id"])

            files = list(Path(tmpdir).glob("*.md"))
            assert len(files) == 1
            assert "42_" in files[0].name

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main_with_subdirs_by_category(
        self, mock_load_template: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """Test export with category subdirectories."""
        from tatlam.cli.render_cards import main

        mock_template = MagicMock()
        mock_template.render.return_value = "# Test"
        mock_load_template.return_value = mock_template

        mock_fetch.return_value = [{"id": 1, "title": "Test", "category": "Category A"}]

        with tempfile.TemporaryDirectory() as tmpdir:
            main(["--out", tmpdir, "--subdirs-by-category"])

            # Should create subdirectory
            subdirs = list(Path(tmpdir).iterdir())
            assert any(d.is_dir() for d in subdirs)

    @patch("tatlam.cli.render_cards.fetch")
    @patch("tatlam.cli.render_cards.load_template")
    def test_main_with_custom_template(
        self, mock_load_template: MagicMock, mock_fetch: MagicMock
    ) -> None:
        """Test export with custom template."""
        from tatlam.cli.render_cards import main

        mock_template = MagicMock()
        mock_template.render.return_value = "# Custom"
        mock_load_template.return_value = mock_template
        mock_fetch.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            main(["--out", tmpdir, "--template", "/custom/template.j2"])

            mock_load_template.assert_called_with("/custom/template.j2")


@pytest.mark.unit
class TestEscapeHtml:
    """Test _escape_html function."""

    def test_escapes_ampersand(self) -> None:
        """Test ampersand is escaped."""
        from tatlam.cli.render_cards import _escape_html

        result = _escape_html("A & B")
        assert "&amp;" in result

    def test_escapes_less_than(self) -> None:
        """Test less-than is escaped."""
        from tatlam.cli.render_cards import _escape_html

        result = _escape_html("<tag>")
        assert "&lt;" in result

    def test_escapes_greater_than(self) -> None:
        """Test greater-than is escaped."""
        from tatlam.cli.render_cards import _escape_html

        result = _escape_html("<tag>")
        assert "&gt;" in result

    def test_escapes_double_quotes(self) -> None:
        """Test double quotes are escaped."""
        from tatlam.cli.render_cards import _escape_html

        result = _escape_html('say "hello"')
        assert "&quot;" in result

    def test_escapes_single_quotes(self) -> None:
        """Test single quotes are escaped."""
        from tatlam.cli.render_cards import _escape_html

        result = _escape_html("it's")
        assert "&#x27;" in result


@pytest.mark.unit
class TestRenderHtmlScenarios:
    """Test render_html with various scenario structures."""

    def test_render_html_with_steps_as_dicts(self) -> None:
        """Test rendering with step dictionaries."""
        from tatlam.cli.render_cards import render_html

        scenarios = [{
            "title": "Test",
            "category": "Test",
            "steps": [{"description": "Step 1"}, {"description": "Step 2"}]
        }]

        html = render_html(scenarios)
        assert "Step 1" in html
        assert "Step 2" in html
        assert "<ol>" in html

    def test_render_html_with_steps_as_strings(self) -> None:
        """Test rendering with step strings."""
        from tatlam.cli.render_cards import render_html

        scenarios = [{
            "title": "Test",
            "category": "Test",
            "steps": ["Do this", "Then that"]
        }]

        html = render_html(scenarios)
        assert "Do this" in html
        assert "Then that" in html

    def test_render_html_with_none_scenario(self) -> None:
        """Test rendering handles None in list."""
        from tatlam.cli.render_cards import render_html

        scenarios = [None]  # type: ignore

        html = render_html(scenarios)
        assert "ללא כותרת" in html


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

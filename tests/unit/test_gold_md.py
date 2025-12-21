"""
Unit tests for tatlam/core/gold_md.py

Tests Gold Markdown parser API.
Target: 100% coverage for parse_md_to_scenario
"""
from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestGoldMdParser:
    """Test suite for gold_md module."""

    def test_module_exports_parse_md_to_scenario(self) -> None:
        """Test that __all__ exports parse_md_to_scenario."""
        from tatlam.core import gold_md

        assert hasattr(gold_md, "__all__")
        assert "parse_md_to_scenario" in gold_md.__all__

    def test_parse_md_to_scenario_is_callable(self) -> None:
        """Test that parse_md_to_scenario is a callable function."""
        from tatlam.core.gold_md import parse_md_to_scenario

        assert callable(parse_md_to_scenario)

    def test_parse_md_to_scenario_delegates_to_implementation(self) -> None:
        """Test that parse_md_to_scenario correctly delegates to implementation."""
        expected_result: dict[str, Any] = {
            "title": "Test Scenario",
            "category": "Security",
            "steps": ["Step 1", "Step 2"],
        }

        mock_impl = MagicMock(return_value=expected_result)
        mock_module = MagicMock()
        mock_module.parse_md_to_scenario = mock_impl

        # Temporarily inject mock module
        original = sys.modules.get("import_gold_md")
        try:
            sys.modules["import_gold_md"] = mock_module

            # Import the function (it will use __import__ internally)
            from tatlam.core import gold_md

            # Clear cache if function was already loaded
            if hasattr(gold_md, "_cached_impl"):
                delattr(gold_md, "_cached_impl")

            # Call the function - it should delegate to our mock
            md_text = "# Test Scenario\n\n## Steps\n- Step 1\n- Step 2"
            result = gold_md.parse_md_to_scenario(md_text)

            # Verify the mock was called correctly
            mock_impl.assert_called_once_with(md_text)
            assert result == expected_result
        finally:
            # Restore original
            if original is not None:
                sys.modules["import_gold_md"] = original
            elif "import_gold_md" in sys.modules:
                del sys.modules["import_gold_md"]

    def test_parse_md_to_scenario_with_hebrew_content(self) -> None:
        """Test parsing Hebrew markdown content."""
        expected_result: dict[str, Any] = {
            "title": "תרחיש בדיקה",
            "category": "אבטחה",
        }

        mock_impl = MagicMock(return_value=expected_result)
        mock_module = MagicMock()
        mock_module.parse_md_to_scenario = mock_impl

        original = sys.modules.get("import_gold_md")
        try:
            sys.modules["import_gold_md"] = mock_module

            from tatlam.core import gold_md

            hebrew_md = "# תרחיש בדיקה\n\n## קטגוריה: אבטחה"
            result = gold_md.parse_md_to_scenario(hebrew_md)

            assert result["title"] == "תרחיש בדיקה"
            mock_impl.assert_called_once_with(hebrew_md)
        finally:
            if original is not None:
                sys.modules["import_gold_md"] = original
            elif "import_gold_md" in sys.modules:
                del sys.modules["import_gold_md"]

    def test_parse_md_to_scenario_with_empty_string(self) -> None:
        """Test parsing empty markdown string."""
        mock_impl = MagicMock(return_value={})
        mock_module = MagicMock()
        mock_module.parse_md_to_scenario = mock_impl

        original = sys.modules.get("import_gold_md")
        try:
            sys.modules["import_gold_md"] = mock_module

            from tatlam.core import gold_md

            result = gold_md.parse_md_to_scenario("")

            assert result == {}
            mock_impl.assert_called_once_with("")
        finally:
            if original is not None:
                sys.modules["import_gold_md"] = original
            elif "import_gold_md" in sys.modules:
                del sys.modules["import_gold_md"]

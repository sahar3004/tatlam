"""
Unit tests for tatlam/cli/export_json.py

Tests JSON export functionality.
Target: 100% coverage for fetch_rows, normalize, main
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestFetchRows:
    """Test suite for fetch_rows function."""

    @patch("tatlam.cli.export_json.get_session")
    def test_fetch_rows_no_filter(self, mock_get_session: MagicMock) -> None:
        """Test fetching all rows without filters."""
        from tatlam.cli.export_json import fetch_rows

        # Setup mock
        mock_scenario1 = MagicMock()
        mock_scenario1.to_dict.return_value = {"id": 1, "title": "Test 1"}
        mock_scenario2 = MagicMock()
        mock_scenario2.to_dict.return_value = {"id": 2, "title": "Test 2"}

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario1, mock_scenario2]
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch_rows()

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    @patch("tatlam.cli.export_json.get_session")
    def test_fetch_rows_by_category(self, mock_get_session: MagicMock) -> None:
        """Test fetching rows filtered by category."""
        from tatlam.cli.export_json import fetch_rows

        mock_scenario = MagicMock()
        mock_scenario.to_dict.return_value = {"id": 1, "title": "Security", "category": "אבטחה"}

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch_rows(category="אבטחה")

        assert len(result) == 1
        assert result[0]["category"] == "אבטחה"

    @patch("tatlam.cli.export_json.get_session")
    def test_fetch_rows_by_bundle_id(self, mock_get_session: MagicMock) -> None:
        """Test fetching rows filtered by bundle_id."""
        from tatlam.cli.export_json import fetch_rows

        mock_scenario = MagicMock()
        mock_scenario.to_dict.return_value = {"id": 1, "title": "Bundle Test", "bundle_id": "BUNDLE-001"}

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch_rows(bundle_id="BUNDLE-001")

        assert len(result) == 1
        assert result[0]["bundle_id"] == "BUNDLE-001"

    @patch("tatlam.cli.export_json.get_session")
    def test_fetch_rows_empty_result(self, mock_get_session: MagicMock) -> None:
        """Test fetching returns empty list when no matches."""
        from tatlam.cli.export_json import fetch_rows

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = fetch_rows(category="nonexistent")

        assert result == []


@pytest.mark.unit
class TestNormalize:
    """Test suite for normalize function."""

    def test_normalize_parses_json_string_steps(self) -> None:
        """Test that JSON string fields are parsed to lists."""
        from tatlam.cli.export_json import normalize

        row: dict[str, Any] = {
            "id": 1,
            "steps": '["step1", "step2"]',
        }

        result = normalize(row)

        assert result["steps"] == ["step1", "step2"]

    def test_normalize_preserves_existing_list(self) -> None:
        """Test that existing lists are preserved."""
        from tatlam.cli.export_json import normalize

        row: dict[str, Any] = {
            "id": 1,
            "steps": ["step1", "step2"],
        }

        result = normalize(row)

        assert result["steps"] == ["step1", "step2"]

    def test_normalize_preserves_existing_dict(self) -> None:
        """Test that existing dicts are preserved."""
        from tatlam.cli.export_json import normalize

        row: dict[str, Any] = {
            "id": 1,
            "steps": {"key": "value"},
        }

        result = normalize(row)

        assert result["steps"] == {"key": "value"}

    def test_normalize_handles_empty_string(self) -> None:
        """Test that empty strings become empty lists."""
        from tatlam.cli.export_json import normalize

        row: dict[str, Any] = {
            "id": 1,
            "steps": "",
        }

        result = normalize(row)

        assert result["steps"] == []

    def test_normalize_handles_none(self) -> None:
        """Test that None becomes empty list."""
        from tatlam.cli.export_json import normalize

        row: dict[str, Any] = {
            "id": 1,
            "steps": None,
        }

        result = normalize(row)

        assert result["steps"] == []

    def test_normalize_handles_invalid_json(self) -> None:
        """Test that invalid JSON strings become empty lists."""
        from tatlam.cli.export_json import normalize

        row: dict[str, Any] = {
            "id": 1,
            "steps": "not valid json {{{",
        }

        result = normalize(row)

        assert result["steps"] == []

    def test_normalize_handles_all_json_fields(self) -> None:
        """Test that all expected JSON fields are normalized."""
        from tatlam.cli.export_json import normalize

        json_fields = [
            "steps",
            "required_response",
            "debrief_points",
            "comms",
            "decision_points",
            "escalation_conditions",
            "lessons_learned",
            "variations",
            "validation",
        ]

        row: dict[str, Any] = {
            "id": 1,
            **{field: '["test"]' for field in json_fields}
        }

        result = normalize(row)

        for field in json_fields:
            assert result[field] == ["test"], f"{field} should be parsed"

    def test_normalize_handles_missing_fields(self) -> None:
        """Test that missing fields default to empty list."""
        from tatlam.cli.export_json import normalize

        row: dict[str, Any] = {"id": 1}

        result = normalize(row)

        assert result.get("steps") == []


@pytest.mark.unit
class TestMain:
    """Test suite for main CLI function."""

    @patch("tatlam.cli.export_json.fetch_rows")
    def test_main_exports_to_file(self, mock_fetch: MagicMock) -> None:
        """Test main function exports data to JSON file."""
        from tatlam.cli.export_json import main

        mock_fetch.return_value = [
            {"id": 1, "title": "Test", "steps": []}
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "output.json"
            result = main(["--out", str(out_path)])

            assert result == 0
            assert out_path.exists()

            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)

            assert len(data) == 1
            assert data[0]["id"] == 1

    @patch("tatlam.cli.export_json.fetch_rows")
    def test_main_with_category_filter(self, mock_fetch: MagicMock) -> None:
        """Test main function with category filter."""
        from tatlam.cli.export_json import main

        mock_fetch.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "output.json"
            result = main(["--category", "אבטחה", "--out", str(out_path)])

            assert result == 0
            mock_fetch.assert_called_once_with("אבטחה", None)

    @patch("tatlam.cli.export_json.fetch_rows")
    def test_main_with_bundle_id_filter(self, mock_fetch: MagicMock) -> None:
        """Test main function with bundle_id filter."""
        from tatlam.cli.export_json import main

        mock_fetch.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "output.json"
            result = main(["--bundle_id", "BUNDLE-001", "--out", str(out_path)])

            assert result == 0
            mock_fetch.assert_called_once_with(None, "BUNDLE-001")

    @patch("tatlam.cli.export_json.fetch_rows")
    def test_main_preserves_hebrew(self, mock_fetch: MagicMock) -> None:
        """Test main function preserves Hebrew text in output."""
        from tatlam.cli.export_json import main

        mock_fetch.return_value = [
            {"id": 1, "title": "תרחיש בדיקה", "steps": []}
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "output.json"
            result = main(["--out", str(out_path)])

            assert result == 0

            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)

            assert data[0]["title"] == "תרחיש בדיקה"

    @patch("tatlam.cli.export_json.fetch_rows")
    def test_main_normalizes_data(self, mock_fetch: MagicMock) -> None:
        """Test main function normalizes JSON fields."""
        from tatlam.cli.export_json import main

        mock_fetch.return_value = [
            {"id": 1, "title": "Test", "steps": '["step1", "step2"]'}
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "output.json"
            result = main(["--out", str(out_path)])

            assert result == 0

            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)

            assert data[0]["steps"] == ["step1", "step2"]


@pytest.mark.unit
class TestModuleExports:
    """Test module-level exports and constants."""

    def test_all_exports_defined(self) -> None:
        """Test that __all__ contains expected exports."""
        from tatlam.cli import export_json

        assert hasattr(export_json, "__all__")
        assert "fetch_rows" in export_json.__all__
        assert "normalize" in export_json.__all__
        assert "main" in export_json.__all__

    def test_module_level_constants(self) -> None:
        """Test that module-level constants are defined."""
        from tatlam.cli import export_json

        assert hasattr(export_json, "DB_PATH")
        assert hasattr(export_json, "TABLE_NAME")

"""
Unit tests for tatlam/cli/dashboard.py

Tests Textual TUI dashboard components.
Target: Coverage for dashboard widgets and main function
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

import pytest


@pytest.mark.unit
class TestLogViewerBasics:
    """Test suite for LogViewer widget basics."""

    def test_log_viewer_class_exists(self) -> None:
        """Test LogViewer class can be imported."""
        from tatlam.cli.dashboard import LogViewer

        assert LogViewer is not None

    def test_log_viewer_inherits_from_static(self) -> None:
        """Test LogViewer inherits from Static widget."""
        from textual.widgets import Static
        from tatlam.cli.dashboard import LogViewer

        assert issubclass(LogViewer, Static)

    def test_log_viewer_stores_path(self) -> None:
        """Test LogViewer stores log path correctly."""
        from tatlam.cli.dashboard import LogViewer

        viewer = LogViewer("/test/path/log.txt")
        assert viewer.log_path == Path("/test/path/log.txt")
        assert viewer.max_lines == 100


@pytest.mark.unit
class TestScenarioTableBasics:
    """Test suite for ScenarioTable widget basics."""

    def test_scenario_table_class_exists(self) -> None:
        """Test ScenarioTable class can be imported."""
        from tatlam.cli.dashboard import ScenarioTable

        assert ScenarioTable is not None

    def test_scenario_table_inherits_from_datatable(self) -> None:
        """Test ScenarioTable inherits from DataTable."""
        from textual.widgets import DataTable
        from tatlam.cli.dashboard import ScenarioTable

        assert issubclass(ScenarioTable, DataTable)

    def test_scenario_table_has_bindings(self) -> None:
        """Test ScenarioTable has key bindings defined."""
        from tatlam.cli.dashboard import ScenarioTable

        assert hasattr(ScenarioTable, "BINDINGS")
        assert len(ScenarioTable.BINDINGS) > 0


@pytest.mark.unit
class TestStatsBarBasics:
    """Test suite for StatsBar widget basics."""

    def test_stats_bar_class_exists(self) -> None:
        """Test StatsBar class can be imported."""
        from tatlam.cli.dashboard import StatsBar

        assert StatsBar is not None

    def test_stats_bar_inherits_from_static(self) -> None:
        """Test StatsBar inherits from Static widget."""
        from textual.widgets import Static
        from tatlam.cli.dashboard import StatsBar

        assert issubclass(StatsBar, Static)


@pytest.mark.unit
class TestTatlamDashboardBasics:
    """Test suite for TatlamDashboard app basics."""

    def test_dashboard_class_exists(self) -> None:
        """Test TatlamDashboard class can be imported."""
        from tatlam.cli.dashboard import TatlamDashboard

        assert TatlamDashboard is not None

    def test_dashboard_inherits_from_app(self) -> None:
        """Test TatlamDashboard inherits from App."""
        from textual.app import App
        from tatlam.cli.dashboard import TatlamDashboard

        assert issubclass(TatlamDashboard, App)

    def test_dashboard_has_bindings(self) -> None:
        """Test TatlamDashboard has key bindings defined."""
        from tatlam.cli.dashboard import TatlamDashboard

        assert hasattr(TatlamDashboard, "BINDINGS")
        assert len(TatlamDashboard.BINDINGS) > 0

    def test_dashboard_has_css(self) -> None:
        """Test TatlamDashboard has CSS styling."""
        from tatlam.cli.dashboard import TatlamDashboard

        assert hasattr(TatlamDashboard, "CSS")
        assert len(TatlamDashboard.CSS) > 0

    def test_dashboard_has_title(self) -> None:
        """Test TatlamDashboard has title and subtitle."""
        from tatlam.cli.dashboard import TatlamDashboard

        assert TatlamDashboard.TITLE == "TATLAM Operations Dashboard"
        assert "Monitor" in TatlamDashboard.SUB_TITLE


@pytest.mark.unit
class TestMainFunction:
    """Test suite for main entry point."""

    @patch("tatlam.cli.dashboard.TatlamDashboard")
    def test_main_creates_and_runs_app(self, mock_app_class: MagicMock) -> None:
        """Test main function creates and runs dashboard."""
        from tatlam.cli.dashboard import main

        mock_app = MagicMock()
        mock_app_class.return_value = mock_app

        main()

        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()

    def test_main_is_callable(self) -> None:
        """Test main function exists and is callable."""
        from tatlam.cli.dashboard import main

        assert callable(main)


@pytest.mark.unit
class TestLogViewerRefresh:
    """Test LogViewer refresh logic."""

    def test_refresh_log_with_existing_file(self) -> None:
        """Test refresh_log reads existing file."""
        from tatlam.cli.dashboard import LogViewer

        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            log_path = f.name

        try:
            viewer = LogViewer(log_path)
            viewer.update = MagicMock()

            viewer.refresh_log()

            viewer.update.assert_called_once()
            call_arg = viewer.update.call_args[0][0]
            assert "Line 1" in call_arg
            assert "Line 2" in call_arg
        finally:
            Path(log_path).unlink(missing_ok=True)

    def test_refresh_log_handles_missing_file(self) -> None:
        """Test refresh_log handles missing file gracefully."""
        from tatlam.cli.dashboard import LogViewer

        viewer = LogViewer("/nonexistent/path/log.txt")
        viewer.update = MagicMock()

        viewer.refresh_log()

        viewer.update.assert_called_once()
        call_arg = viewer.update.call_args[0][0]
        assert "not found" in call_arg.lower()


@pytest.mark.unit
class TestScenarioTableRefresh:
    """Test ScenarioTable refresh logic."""

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_data_loads_scenarios(self, mock_get_session: MagicMock) -> None:
        """Test refresh_data loads scenarios from database."""
        from tatlam.cli.dashboard import ScenarioTable

        mock_scenario = MagicMock()
        mock_scenario.id = 1
        mock_scenario.title = "Test"
        mock_scenario.category = "Cat"
        mock_scenario.threat_level = "HIGH"
        mock_scenario.status = "approved"
        mock_scenario.created_at = "2025-01-01T12:00:00"

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        table = ScenarioTable()
        table.clear = MagicMock()
        table.add_row = MagicMock()

        # Use patch.object to mock the read-only app property
        mock_app = MagicMock()
        with patch.object(type(table), "app", new_callable=lambda: property(lambda self: mock_app)):
            table.refresh_data()

        table.clear.assert_called_once()
        table.add_row.assert_called_once()

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_data_handles_db_error(self, mock_get_session: MagicMock) -> None:
        """Test refresh_data handles database errors."""
        from tatlam.cli.dashboard import ScenarioTable

        mock_get_session.return_value.__enter__.side_effect = Exception("DB Error")

        table = ScenarioTable()
        table.clear = MagicMock()

        # Use patch.object to mock the read-only app property
        mock_app = MagicMock()
        with patch.object(type(table), "app", new_callable=lambda: property(lambda self: mock_app)):
            table.refresh_data()

        mock_app.notify.assert_called_once()


@pytest.mark.unit
class TestStatsBarRefresh:
    """Test StatsBar refresh logic."""

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_stats_displays_counts(self, mock_get_session: MagicMock) -> None:
        """Test refresh_stats displays correct counts."""
        from tatlam.cli.dashboard import StatsBar

        mock_session = MagicMock()
        mock_session.scalar.side_effect = [100, 30, 50, 20]
        mock_get_session.return_value.__enter__.return_value = mock_session

        stats = StatsBar()
        stats.update = MagicMock()

        stats.refresh_stats()

        call_arg = stats.update.call_args[0][0]
        assert "100" in call_arg

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_stats_handles_db_error(self, mock_get_session: MagicMock) -> None:
        """Test refresh_stats handles database errors."""
        from tatlam.cli.dashboard import StatsBar

        mock_get_session.return_value.__enter__.side_effect = Exception("DB Error")

        stats = StatsBar()
        stats.update = MagicMock()

        stats.refresh_stats()

        call_arg = stats.update.call_args[0][0]
        assert "Error" in call_arg


@pytest.mark.unit
class TestLogViewerAdvanced:
    """Advanced tests for LogViewer widget."""

    def test_log_viewer_refresh_handles_exception(self) -> None:
        """Test refresh_log handles file read exceptions."""
        from tatlam.cli.dashboard import LogViewer

        viewer = LogViewer("/some/path.log")
        viewer.update = MagicMock()

        # Mock open to raise exception
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            # First set log_path to exist
            with patch.object(Path, "exists", return_value=True):
                viewer.refresh_log()

        viewer.update.assert_called_once()
        call_arg = viewer.update.call_args[0][0]
        assert "Error" in call_arg or "error" in call_arg.lower()


@pytest.mark.unit
class TestScenarioTableAdvanced:
    """Advanced tests for ScenarioTable widget."""

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_data_truncates_long_title(self, mock_get_session: MagicMock) -> None:
        """Test titles longer than 37 chars are truncated."""
        from tatlam.cli.dashboard import ScenarioTable

        mock_scenario = MagicMock()
        mock_scenario.id = 1
        mock_scenario.title = "This is a very long title that exceeds the maximum length"
        mock_scenario.category = "Category"
        mock_scenario.threat_level = "HIGH"
        mock_scenario.status = "approved"
        mock_scenario.created_at = "2025-01-01T12:00:00"

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        table = ScenarioTable()
        table.clear = MagicMock()
        table.add_row = MagicMock()

        mock_app = MagicMock()
        with patch.object(type(table), "app", new_callable=lambda: property(lambda self: mock_app)):
            table.refresh_data()

        # Verify add_row was called with truncated title
        call_args = table.add_row.call_args[0]
        assert call_args[1].endswith("...")
        assert len(call_args[1]) <= 40  # 37 + "..."

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_data_truncates_long_category(self, mock_get_session: MagicMock) -> None:
        """Test categories longer than 22 chars are truncated."""
        from tatlam.cli.dashboard import ScenarioTable

        mock_scenario = MagicMock()
        mock_scenario.id = 1
        mock_scenario.title = "Test"
        mock_scenario.category = "This is a very long category name here"
        mock_scenario.threat_level = "HIGH"
        mock_scenario.status = "approved"
        mock_scenario.created_at = "2025-01-01T12:00:00"

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        table = ScenarioTable()
        table.clear = MagicMock()
        table.add_row = MagicMock()

        mock_app = MagicMock()
        with patch.object(type(table), "app", new_callable=lambda: property(lambda self: mock_app)):
            table.refresh_data()

        # Verify add_row was called with truncated category
        call_args = table.add_row.call_args[0]
        assert call_args[2].endswith("...")

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_data_handles_invalid_date(self, mock_get_session: MagicMock) -> None:
        """Test refresh_data handles invalid date format."""
        from tatlam.cli.dashboard import ScenarioTable

        mock_scenario = MagicMock()
        mock_scenario.id = 1
        mock_scenario.title = "Test"
        mock_scenario.category = "Category"
        mock_scenario.threat_level = "HIGH"
        mock_scenario.status = "approved"
        mock_scenario.created_at = "not-a-valid-date"

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        table = ScenarioTable()
        table.clear = MagicMock()
        table.add_row = MagicMock()

        mock_app = MagicMock()
        with patch.object(type(table), "app", new_callable=lambda: property(lambda self: mock_app)):
            table.refresh_data()

        # Should still call add_row without crashing
        table.add_row.assert_called_once()

    @patch("tatlam.cli.dashboard.get_session")
    def test_refresh_data_handles_none_category(self, mock_get_session: MagicMock) -> None:
        """Test refresh_data handles None category."""
        from tatlam.cli.dashboard import ScenarioTable

        mock_scenario = MagicMock()
        mock_scenario.id = 1
        mock_scenario.title = "Test"
        mock_scenario.category = None
        mock_scenario.threat_level = None
        mock_scenario.status = None
        mock_scenario.created_at = None

        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = [mock_scenario]
        mock_get_session.return_value.__enter__.return_value = mock_session

        table = ScenarioTable()
        table.clear = MagicMock()
        table.add_row = MagicMock()

        mock_app = MagicMock()
        with patch.object(type(table), "app", new_callable=lambda: property(lambda self: mock_app)):
            table.refresh_data()

        # Verify N/A defaults are used
        call_args = table.add_row.call_args[0]
        assert call_args[2] == "N/A"  # category
        assert call_args[3] == "N/A"  # threat_level
        assert call_args[4] == "pending"  # status


@pytest.mark.unit
class TestTatlamDashboardAdvanced:
    """Advanced tests for TatlamDashboard app."""

    @patch("tatlam.cli.dashboard.get_settings")
    def test_dashboard_init_sets_log_path(self, mock_get_settings: MagicMock) -> None:
        """Test dashboard __init__ sets log path from settings."""
        from tatlam.cli.dashboard import TatlamDashboard

        mock_settings = MagicMock()
        mock_settings.BASE_DIR = Path("/base/dir")
        mock_get_settings.return_value = mock_settings

        with patch.object(Path, "exists", return_value=True):
            dashboard = TatlamDashboard()
            assert dashboard.log_path is not None

    @patch("tatlam.cli.dashboard.get_settings")
    def test_dashboard_init_tries_alt_paths(self, mock_get_settings: MagicMock) -> None:
        """Test dashboard tries alternative log paths."""
        from tatlam.cli.dashboard import TatlamDashboard

        mock_settings = MagicMock()
        mock_settings.BASE_DIR = Path("/nonexistent")
        mock_get_settings.return_value = mock_settings

        # First path doesn't exist, alt paths don't exist either
        with patch.object(Path, "exists", return_value=False):
            dashboard = TatlamDashboard()
            # Should still have a log_path set (just the original one)
            assert dashboard.log_path is not None

    def test_dashboard_action_toggle_dark_exists(self) -> None:
        """Test toggle_dark action method exists."""
        from tatlam.cli.dashboard import TatlamDashboard

        assert hasattr(TatlamDashboard, "action_toggle_dark")
        assert callable(getattr(TatlamDashboard, "action_toggle_dark"))

    def test_dashboard_action_refresh_all_exists(self) -> None:
        """Test refresh_all action method exists."""
        from tatlam.cli.dashboard import TatlamDashboard

        assert hasattr(TatlamDashboard, "action_refresh_all")
        assert callable(getattr(TatlamDashboard, "action_refresh_all"))

    def test_dashboard_compose_exists(self) -> None:
        """Test compose method exists."""
        from tatlam.cli.dashboard import TatlamDashboard

        assert hasattr(TatlamDashboard, "compose")
        assert callable(getattr(TatlamDashboard, "compose"))

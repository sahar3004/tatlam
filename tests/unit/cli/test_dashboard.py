
import pytest
from unittest.mock import MagicMock, patch, mock_open
from tatlam.cli.dashboard import (
    LogViewer,
    ScenarioTable,
    StatsBar,
    TatlamDashboard,
    main
)

try:
    from textual.app import App
    TEXTUAL_INSTALLED = True
except ImportError:
    TEXTUAL_INSTALLED = False

@pytest.mark.skipif(not TEXTUAL_INSTALLED, reason="Textual not installed")
class TestDashboard:
    
    def test_log_viewer_refresh_no_file(self):
        # Test refresh handles missing file
        viewer = LogViewer(log_path="non_existent.log")
        viewer.update = MagicMock()
        viewer.refresh_log()
        viewer.update.assert_called() # Should call update with message

    def test_log_viewer_refresh_success(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("line1\nline2")
        
        viewer = LogViewer(log_path=str(log_file))
        viewer.update = MagicMock()
        viewer.refresh_log()
        # Verify it read lines
        args, _ = viewer.update.call_args
        assert "line1" in args[0]
        assert "line2" in args[0]

    @patch("tatlam.cli.dashboard.get_session")
    def test_stats_bar_refresh(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.scalar.return_value = 10
        
        bar = StatsBar()
        bar.update = MagicMock()
        bar.refresh_stats()
        
        args, _ = bar.update.call_args
        assert "10" in args[0]

    @patch("tatlam.cli.dashboard.get_session")
    def test_scenario_table_refresh(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_sc = MagicMock()
        mock_sc.title = "T"
        mock_sc.category = "C"
        mock_sc.created_at = "2023-01-01T10:00:00"
        
        mock_session.scalars.return_value.all.return_value = [mock_sc]
        
        table = ScenarioTable()
        # Mock textual table methods
        table.clear = MagicMock()
        table.add_row = MagicMock()
        
        # We need to mock 'app' attribute if it calls notify, or run inside app context
        # But refresh_data handles exception safely
        table.refresh_data()
        
        table.add_row.assert_called()

    def test_app_init(self):
        app = TatlamDashboard()
        assert app.log_path is not None

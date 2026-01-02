import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

# Add root to path to find main_ui.py
sys.path.append(os.getcwd())

# Mock streamlit before importing main_ui
sys.modules["streamlit"] = MagicMock()

# Now import main_ui
try:
    import main_ui
    from main_ui import get_db_scenarios
except ImportError:
    # If standard import fails, try importlib or assume it's available via path
    import importlib.util
    spec = importlib.util.spec_from_file_location("main_ui", "main_ui.py")
    main_ui = importlib.util.module_from_spec(spec)
    sys.modules["main_ui"] = main_ui
    spec.loader.exec_module(main_ui)
    get_db_scenarios = main_ui.get_db_scenarios

from tatlam.core.schemas import ScenarioDTO
from tatlam.infra.repo import ScenarioRepository, fetch_all_dto
from tatlam.core.brain import TrinityBrain

class TestDTOFlow:

    @pytest.fixture
    def mock_repo_fetch(self):
        """Mock repo.fetch_all to return dicts as expected by internal implementation."""
        # fetch_all_dto calls fetch_all internally
        with patch('tatlam.infra.repo.fetch_all') as mock:
            mock.return_value = [
                {"id": 1, "title": "Test 1", "status": "pending", "category": "security", "steps": []},
                {"id": 2, "title": "Test 2", "status": "approved", "category": "safety", "steps": []}
            ]
            yield mock

    def test_repo_returns_dtos(self, mock_repo_fetch):
        """Verify fetch_all_dto returns ScenarioDTO objects."""
        result = fetch_all_dto()
        assert len(result) == 2
        assert isinstance(result[0], ScenarioDTO)
        assert result[0].title == "Test 1"
        assert result[0].status == "pending"
        assert isinstance(result[1], ScenarioDTO)

    def test_ui_consumes_dtos(self, mock_repo_fetch):
        """Verify main_ui.get_db_scenarios handles DTOs correctly."""
        # Test filtering "pending"
        pending = get_db_scenarios("pending")
        assert len(pending) == 1
        assert pending[0].title == "Test 1"
        assert isinstance(pending[0], ScenarioDTO)

        # Test filtering "approved"
        approved = get_db_scenarios("approved")
        assert len(approved) == 1
        assert approved[0].title == "Test 2"

        # Test "all"
        all_scenarios = get_db_scenarios("all")
        assert len(all_scenarios) == 2

    def test_brain_generate_batch_returns_dtos(self):
        """Verify brain.generate_batch returns DTOs."""
        brain = TrinityBrain(auto_initialize=False)
        
        # Mock run_scenario_generation
        mock_result = MagicMock()
        mock_result.bundle_id = "bundle_123"
        
        mock_scenario = MagicMock()
        mock_scenario.data = {"title": "Generated 1", "category": "test", "steps": []}
        
        mock_result.approved_scenarios = [mock_scenario]
        mock_result.metrics.to_dict.return_value = {}
        mock_result.errors = []

        with patch("tatlam.graph.workflow.run_scenario_generation", return_value=mock_result):
            result = brain.generate_batch("test", count=1)
            assert "scenarios" in result
            assert len(result["scenarios"]) == 1
            assert isinstance(result["scenarios"][0], ScenarioDTO)
            assert result["scenarios"][0].title == "Generated 1"

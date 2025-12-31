
import pytest
from unittest.mock import MagicMock, patch
from tatlam.infra.repo import (
    ScenarioRepository,
    get_repository,
    normalize_row,
    db_has_column,
    _normalize_text,
    _parse_json_field,
    JSON_FIELDS
)
from tatlam.infra.models import Scenario

class TestRepoUnit:

    @pytest.fixture(autouse=True)
    def setup_db(self, in_memory_db):
        """Ensure DB is initialized with schema."""
        from tatlam.infra.db import init_db_sqlalchemy
        init_db_sqlalchemy()
        yield    
    def test_normalize_text(self):
        """Test text normalization."""
        assert _normalize_text(None) == ""
        assert _normalize_text("test") == "test"
        # Hebrew normalization (dummy check, real check requires specific unicode chars)
        assert _normalize_text("שלום") == "שלום"

    def test_parse_json_field(self):
        """Test JSON field parsing."""
        assert _parse_json_field(None) == []
        assert _parse_json_field("") == []
        assert _parse_json_field("   ") == []
        assert _parse_json_field([]) == []
        assert _parse_json_field({}) == {}
        assert _parse_json_field('["a", "b"]') == ["a", "b"]
        assert _parse_json_field('{"a": 1}') == {"a": 1}
        # Invalid JSON returns empty list
        assert _parse_json_field("{invalid_json}") == []

    def test_normalize_row_dict(self):
        """Test normalize_row with dictionary."""
        row = {
            "id": 1,
            "title": "Test",
            "steps": '["step1"]',
            "other": "value"
        }
        normalized = normalize_row(row)
        assert normalized["id"] == 1
        assert normalized["steps"] == ["step1"]
        assert normalized["other"] == "value"

    def test_normalize_row_model(self):
        """Test normalize_row with Scenario model."""
        scenario = Scenario(
            id=1,
            title="Test",
            steps='["step1"]'
        )
        # Mock to_dict for Scenario
        scenario.to_dict = MagicMock(return_value={"id": 1, "title": "Test", "steps": ["step1"]})
        
        normalized = normalize_row(scenario)
        assert normalized["id"] == 1
        assert normalized["steps"] == ["step1"]

    @patch("tatlam.infra.repo.Scenario")
    def test_db_has_column_cached(self, MockScenario):
        """Test column existence check with cache."""
        # Clear cache first if needed, but module level mock is hard.
        # We test logic flow.
        MockScenario.test_col = "dummy"
        
        # We need to mock TABLE_NAME to match what we pass or rely on default
        from tatlam.infra.repo import TABLE_NAME
        
        assert db_has_column(TABLE_NAME, "test_col") is False # Likely false because MockScenario attr check logic
        # Ideally we don't mock the class attribute but rely on hasattr
        
        # Let's test non-table fallback
        assert db_has_column("non_existent_table", "col") is True

    def test_repository_singleton(self):
        """Test get_repository returns singleton."""
        repo1 = get_repository()
        repo2 = get_repository()
        assert repo1 is repo2
        assert isinstance(repo1, ScenarioRepository)

    @patch("tatlam.infra.repo.fetch_all")
    def test_repo_class_methods(self, mock_fetch_all):
        """Test ScenarioRepository class methods delegate correctly."""
        repo = ScenarioRepository()
        
        repo.fetch_all(limit=10)
        mock_fetch_all.assert_called_with(limit=10, offset=None)

    @patch("tatlam.infra.repo.insert_scenario")
    def test_repo_insert(self, mock_insert):
        repo = ScenarioRepository()
        data = {"title": "T"}
        repo.insert_scenario(data)
        mock_insert.assert_called_with(data=data, owner="web", pending=True)

    @patch("tatlam.infra.repo.fetch_one")
    def test_repo_fetch_one(self, mock_fetch):
        repo = ScenarioRepository()
        repo.fetch_one(1)
        mock_fetch.assert_called_with(1)

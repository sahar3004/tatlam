from unittest.mock import MagicMock, patch
import pytest
from tatlam.graph.nodes.judge import judge_node, _score_with_llm, _build_judge_rubric, IRON_DOME_THRESHOLD
from tatlam.graph.state import SwarmState, ScenarioCandidate, ScenarioStatus
from tatlam.core.validators import DoctrineValidationResult

@pytest.fixture
def mock_validator():
    with patch("tatlam.graph.nodes.judge.validate_scenario_doctrine") as mock:
        mock.return_value = DoctrineValidationResult(is_valid=True, doctrine_score=80.0, errors=[], warnings=[])
        yield mock

@pytest.fixture
def mock_llm_scorer():
    with patch("tatlam.graph.nodes.judge._score_with_llm") as mock:
        mock.return_value = (85.0, "Good")
        yield mock

@pytest.fixture
def mock_writer_client():
    with patch("tatlam.core.llm_factory.create_writer_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield mock, client

@pytest.fixture
def mock_settings():
    with patch("tatlam.graph.nodes.judge.get_settings") as mock:
        settings = MagicMock()
        mock.return_value = settings
        yield settings

class TestJudgeNode:

    def test_build_judge_rubric(self):
        rubric = _build_judge_rubric()
        assert "בטיחות" in rubric
        assert "משקל 30%" in rubric

    def test_score_with_llm_success(self, mock_writer_client, mock_settings):
        _, client = mock_writer_client
        
        # Mock LLM response
        response = MagicMock()
        response.content = [MagicMock(text='{"score": 90, "critique": "Excellent", "audit_log": "Log", "strengths": ["S1"], "weaknesses": [], "repair_instructions": []}')]
        client.messages.create.return_value = response
        
        score, critique = _score_with_llm({}, "rubric")
        assert score == 90.0
        assert "Excellent" in critique
        assert "S1" in critique

    def test_score_with_llm_venue_jaffa(self, mock_writer_client, mock_settings):
        # Test Jaffa detection logic
        _, client = mock_writer_client
        response = MagicMock()
        response.content = [MagicMock(text='{"score": 80}')]
        client.messages.create.return_value = response
        
        scenario = {"location": "Jaffa Station", "category": "General"}
        with patch("tatlam.graph.nodes.judge.get_system_prompt") as mock_prompt:
             _score_with_llm(scenario, "rubric")
             mock_prompt.assert_called()
             assert mock_prompt.call_args[1]["venue"] == "jaffa"

    def test_score_with_llm_client_missing(self, mock_writer_client, mock_settings):
        mock_create, _ = mock_writer_client
        mock_create.return_value = None
        
        score, critique = _score_with_llm({}, "rubric")
        assert score == 70.0 # Default fallback
        assert "לא ניתן" in critique

    def test_score_with_llm_json_error(self, mock_writer_client, mock_settings):
        _, client = mock_writer_client
        response = MagicMock()
        response.content = [MagicMock(text='Invalid JSON')]
        client.messages.create.return_value = response
        
        score, critique = _score_with_llm({}, "rubric")
        assert score == 60.0 # Error fallback
        assert "שגיאה בפרסור" in critique

    def test_judge_node_no_candidates(self):
        state = SwarmState()
        final_state = judge_node(state)
        assert final_state == state

    def test_judge_node_doctrine_invalid(self, mock_validator):
        # Validation fails critically
        mock_validator.return_value = DoctrineValidationResult(is_valid=False, doctrine_score=0.0, errors=["Fatal"], warnings=[])
        
        state = SwarmState()
        c = state.add_candidate({"title": "Bad"})
        c.status = ScenarioStatus.UNIQUE
        
        final_state = judge_node(state)
        
        assert final_state.candidates[0].status == ScenarioStatus.REJECTED
        assert final_state.metrics.total_rejected == 1
        assert "כשל דוקטרינה" in final_state.candidates[0].critique

    def test_judge_node_llm_exception(self, mock_validator, mock_llm_scorer):
        # LLM scorer raises exception (e.g. retry exhaustion)
        mock_llm_scorer.side_effect = Exception("LLM Death")
        
        # Doctrine passed cleanly
        mock_validator.return_value = DoctrineValidationResult(is_valid=True, doctrine_score=80.0, errors=[], warnings=["Check X"])
        
        state = SwarmState()
        c = state.add_candidate({"title": "Risk"})
        c.status = ScenarioStatus.UNIQUE
        
        final_state = judge_node(state)
        
        # Check fallback to doctrine score
        # Final score = 80*0.4 + 80*0.6 = 80.0
        # Use .score property, not .feedback_score
        assert final_state.candidates[0].score == 80.0
        # Check warnings in critique
        assert "Check X" in final_state.candidates[0].critique
        assert "שימוש בציון דוקטרינה בלבד" in final_state.candidates[0].critique

    def test_judge_node_approval_logic(self, mock_validator, mock_llm_scorer):
        # High score
        mock_validator.return_value = DoctrineValidationResult(is_valid=True, doctrine_score=90.0)
        mock_llm_scorer.return_value = (90.0, "Great")
        
        state = SwarmState()
        c = state.add_candidate({"title": "Good"})
        c.status = ScenarioStatus.UNIQUE
        
        final_state = judge_node(state)
        
        assert final_state.candidates[0].status == ScenarioStatus.JUDGE_APPROVED
        assert final_state.metrics.total_approved == 1

    def test_judge_node_rejection_logic(self, mock_validator, mock_llm_scorer):
        # Low score
        mock_validator.return_value = DoctrineValidationResult(is_valid=True, doctrine_score=50.0)
        mock_llm_scorer.return_value = (50.0, "Poor")
        
        state = SwarmState()
        c = state.add_candidate({"title": "Weak"})
        c.status = ScenarioStatus.UNIQUE
        
        final_state = judge_node(state)
        
        assert final_state.candidates[0].status == ScenarioStatus.REJECTED
        assert final_state.metrics.total_rejected == 1

    def test_score_with_llm_repair_instructions(self, mock_writer_client, mock_settings):
        # Test parsing of repair instructions
        _, client = mock_writer_client
        json_resp = (
            '{"score": 75, "critique": "OK", '
            '"repair_instructions": [{"field": "F", "issue": "I", "fix": "Fix"}]}'
        )
        response = MagicMock()
        response.content = [MagicMock(text=json_resp)]
        client.messages.create.return_value = response
        
        score, critique = _score_with_llm({}, "rubric")
        assert "הוראות תיקון לכותב" in critique
        assert "[F]: I → Fix" in critique

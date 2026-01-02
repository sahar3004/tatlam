"""
Tests for tatlam.graph.nodes.judge - Judge Node.
"""

from unittest.mock import patch, MagicMock
import json

from tatlam.graph.state import SwarmState, ScenarioCandidate


class TestJudgeNode:
    """Tests for the judge_node function."""

    def test_judge_node_skips_empty_candidates(self):
        """Judge should skip if no candidates."""
        from tatlam.graph.nodes.judge import judge_node

        state = SwarmState(category="חפץ חשוד", candidates=[])

        result = judge_node(state)
        assert result.approved_scenarios == []

    def test_judge_node_processes_candidates(self):
        """Judge should process all candidates."""
        from tatlam.graph.nodes.judge import judge_node
        import tatlam.graph.nodes.judge as judge_module

        candidates = [
            ScenarioCandidate(data={"title": "תרחיש 1", "category": "חפץ חשוד"}),
            ScenarioCandidate(data={"title": "תרחיש 2", "category": "חפץ חשוד"}),
        ]
        state = SwarmState(category="חפץ חשוד", candidates=candidates)

        # Save original function
        original_score_with_llm = judge_module._score_with_llm

        try:
            # Replace with mock
            judge_module._score_with_llm = lambda scenario, rubric: (85.0, "טוב מאוד")

            result = judge_node(state)
            # Should return a state
            assert result is not None
            assert isinstance(result, SwarmState)
        finally:
            # Restore original
            judge_module._score_with_llm = original_score_with_llm


class TestScoreWithLLM:
    """Tests for the _score_with_llm function."""

    def test_score_with_llm_no_client(self):
        """Should return default score when client unavailable."""
        from tatlam.graph.nodes.judge import _score_with_llm
        from tatlam.core.llm_factory import ConfigurationError

        with patch("tatlam.core.llm_factory.create_writer_client") as mock_create:
            mock_create.side_effect = ConfigurationError("No API key")

            score, critique = _score_with_llm({"title": "test"}, "rubric")
            assert score == 70.0
            assert "לא ניתן" in critique

    def test_score_with_llm_success(self):
        """Should parse LLM response correctly."""
        from tatlam.graph.nodes.judge import _score_with_llm

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "score": 85,
                        "critique": "תרחיש איכותי",
                        "audit_log": "בטיחות: תקין",
                        "strengths": ["מפורט", "ריאליסטי"],
                        "weaknesses": ["חסר פרטים"],
                        "repair_instructions": [],
                    }
                )
            )
        ]
        mock_client.messages.create.return_value = mock_response

        with patch("tatlam.core.llm_factory.create_writer_client", return_value=mock_client):
            with patch("tatlam.graph.nodes.judge.get_system_prompt", return_value="system prompt"):
                score, critique = _score_with_llm(
                    {"title": "test", "category": "חפץ חשוד"}, "rubric"
                )

                assert score == 85.0
                assert "תרחיש איכותי" in critique
                assert "מפורט" in critique  # strengths included
                assert "חסר פרטים" in critique  # weaknesses included

    def test_score_with_llm_invalid_json(self):
        """Should handle invalid JSON response gracefully."""
        from tatlam.graph.nodes.judge import _score_with_llm

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="This is not JSON")]
        mock_client.messages.create.return_value = mock_response

        with patch("tatlam.core.llm_factory.create_writer_client", return_value=mock_client):
            with patch("tatlam.graph.nodes.judge.get_system_prompt", return_value="prompt"):
                score, critique = _score_with_llm({"title": "test"}, "rubric")

                assert score == 60.0
                assert "שגיאה" in critique

    def test_score_with_llm_jaffa_venue_detection(self):
        """Should detect Jaffa venue from location field."""
        from tatlam.graph.nodes.judge import _score_with_llm

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"score": 80, "critique": "ok"}')]
        mock_client.messages.create.return_value = mock_response

        with patch("tatlam.core.llm_factory.create_writer_client", return_value=mock_client):
            with patch("tatlam.graph.nodes.judge.get_system_prompt") as mock_prompt:
                mock_prompt.return_value = "prompt"
                _score_with_llm({"title": "test", "location": "תחנת יפו"}, "rubric")

                # Should call with jaffa venue
                call_args = mock_prompt.call_args
                assert call_args[1].get("venue") == "jaffa"

    def test_score_with_llm_repair_instructions(self):
        """Should include repair instructions in critique."""
        from tatlam.graph.nodes.judge import _score_with_llm

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "score": 65,
                        "critique": "נדרש שיפור",
                        "repair_instructions": [
                            {"field": "description", "issue": "קצר מדי", "fix": "הוסף פרטים"}
                        ],
                    }
                )
            )
        ]
        mock_client.messages.create.return_value = mock_response

        with patch("tatlam.core.llm_factory.create_writer_client", return_value=mock_client):
            with patch("tatlam.graph.nodes.judge.get_system_prompt", return_value="prompt"):
                score, critique = _score_with_llm({"title": "test"}, "rubric")

                assert "הוראות תיקון" in critique
                assert "description" in critique
                assert "קצר מדי" in critique

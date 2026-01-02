import pytest
from unittest.mock import MagicMock, patch
from tatlam.core.brain import TrinityBrain, SimulatorUnavailableError, APICallError
from tatlam.core.utils import strip_markdown_and_parse_json


class TestGapFillers:
    """
    Tests designed to fill coverage gaps identified in Phase 2.
    Focus: Error handling, edge cases, and untested utility functions.
    """

    # ==== Brain.py Coverage Gaps ====

    def test_brain_generate_scenario_stream_auth_error(self):
        """Test error handling for authentication failure in writer stream."""
        mock_writer = MagicMock()
        # Mocking an exception that looks like an auth error
        error_mock = Exception("Authentication failed: 401 Unauthorized")
        mock_writer.messages.stream.side_effect = error_mock

        brain = TrinityBrain(writer_client=mock_writer, auto_initialize=False)

        with pytest.raises(APICallError) as exc:
            list(brain.generate_scenario_stream("test prompt"))

        assert "Writer authentication failed" in str(exc.value)

    def test_brain_audit_scenario_auth_error(self):
        """Test error handling for authentication failure in judge."""
        mock_judge = MagicMock()
        error_mock = Exception("API Key Invalid")
        mock_judge.generate_content.side_effect = error_mock

        brain = TrinityBrain(judge_client=mock_judge, auto_initialize=False)

        with pytest.raises(APICallError) as exc:
            brain.audit_scenario("test scenario")

        assert "Judge authentication failed" in str(exc.value)

    def test_brain_chat_simulation_stream_connection_error(self):
        """Test error handling for connection error in simulator (offline)."""
        from tenacity import RetryError

        mock_sim = MagicMock()
        # Simulate a RetryError after exhausting retries
        last_attempt = MagicMock()
        last_attempt.exception.return_value = ConnectionError("Connection refused")
        error_mock = RetryError(last_attempt)
        mock_sim.generate_content.side_effect = error_mock

        with patch.dict("sys.modules", {"google.generativeai": MagicMock()}):
            import google.generativeai as genai

            genai.GenerationConfig = MagicMock(return_value=MagicMock())
            brain = TrinityBrain(simulator_client=mock_sim, auto_initialize=False)

            with pytest.raises(SimulatorUnavailableError) as exc:
                list(brain.chat_simulation_stream([{"role": "user", "content": "hi"}]))

            assert "offline" in str(exc.value).lower() or "unreachable" in str(exc.value).lower()

    def test_brain_think_structured_json_error(self):
        """Test handling of invalid JSON from simulator in think_structured."""
        mock_sim = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Not Valid JSON"
        mock_sim.chat.completions.create.return_value = mock_response

        brain = TrinityBrain(simulator_client=mock_sim, auto_initialize=False)

        with pytest.raises(APICallError) as exc:
            brain.think_structured("analyze this")

        assert "Invalid JSON response" in str(exc.value)

    def test_brain_think_structured_missing_fields_fallback(self):
        """Test fallback values when simulator returns partial JSON."""
        mock_sim = MagicMock()
        mock_response = MagicMock()
        # Missing decision and reasoning
        mock_response.choices[0].message.content = '{"threat_level": "LOW", "category": "SAFETY"}'
        mock_sim.chat.completions.create.return_value = mock_response

        brain = TrinityBrain(simulator_client=mock_sim, auto_initialize=False)

        result = brain.think_structured("analyze this")

        assert result["threat_level"] == "LOW"
        assert result["decision"] == "המתן להנחיות נוספות"  # Default fallback
        assert result["reasoning"] == "מידע לא מספיק להערכה מלאה"  # Default fallback

    # ==== Batch_logic.py Coverage Gaps ====

    def test_strip_markdown_and_parse_json_variants(self):
        """Test the secure JSON parser with various inputs."""
        # Standard JSON
        assert strip_markdown_and_parse_json('{"key": "value"}') == {"key": "value"}

        # Markdown block with json tag
        assert strip_markdown_and_parse_json('```json\n{"key": "value"}\n```') == {"key": "value"}

        # Markdown block without tag
        assert strip_markdown_and_parse_json('```\n{"key": "value"}\n```') == {"key": "value"}

        # Invalid JSON
        assert strip_markdown_and_parse_json("{key: value}") is None

        # Empty input
        assert strip_markdown_and_parse_json("") is None
        assert strip_markdown_and_parse_json(None) is None

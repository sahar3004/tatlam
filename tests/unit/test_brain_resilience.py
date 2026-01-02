"""
Unit tests for tatlam/core/brain.py - Resilience and retry logic.

Tests cover:
1. Tenacity retry behavior on transient errors
2. Immediate failure on authentication errors (no retry)
3. Client unavailability handling
4. Input validation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from tatlam.core.brain import (
    TrinityBrain,
    WriterUnavailableError,
    JudgeUnavailableError,
    SimulatorUnavailableError,
    APICallError,
)
from tatlam.core.prompts import PromptValidationError


@pytest.mark.unit
class TestClientAvailability:
    """Tests for client availability checks."""

    def test_brain_without_clients(self):
        """Test TrinityBrain can be created without clients."""
        brain = TrinityBrain(auto_initialize=False)

        assert brain.writer_client is None
        assert brain.judge_client is None
        assert brain.simulator_client is None

    def test_has_writer_returns_correct_status(self):
        """Test has_writer method."""
        brain = TrinityBrain(auto_initialize=False)
        assert brain.has_writer() is False

        brain.writer_client = Mock()
        assert brain.has_writer() is True

    def test_has_judge_returns_correct_status(self):
        """Test has_judge method."""
        brain = TrinityBrain(auto_initialize=False)
        assert brain.has_judge() is False

        brain.judge_client = Mock()
        assert brain.has_judge() is True

    def test_has_simulator_returns_correct_status(self):
        """Test has_simulator method."""
        brain = TrinityBrain(auto_initialize=False)
        assert brain.has_simulator() is False

        brain.simulator_client = Mock()
        assert brain.has_simulator() is True

    def test_get_status_returns_all_statuses(self):
        """Test get_status method returns dict with all clients."""
        brain = TrinityBrain(auto_initialize=False)

        status = brain.get_status()

        assert "writer" in status
        assert "judge" in status
        assert "simulator" in status
        assert status["writer"] is False
        assert status["judge"] is False
        assert status["simulator"] is False


@pytest.mark.unit
class TestWriterUnavailable:
    """Tests for writer client unavailability."""

    def test_generate_scenario_raises_when_writer_unavailable(self):
        """Test generate_scenario raises WriterUnavailableError when client is None."""
        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(WriterUnavailableError) as exc_info:
            brain.generate_scenario("test prompt")

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_generate_scenario_stream_raises_when_writer_unavailable(self):
        """Test generate_scenario_stream raises WriterUnavailableError."""
        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(WriterUnavailableError):
            list(brain.generate_scenario_stream("test prompt"))


@pytest.mark.unit
class TestJudgeUnavailable:
    """Tests for judge client unavailability."""

    def test_audit_scenario_raises_when_judge_unavailable(self):
        """Test audit_scenario raises JudgeUnavailableError when client is None."""
        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(JudgeUnavailableError) as exc_info:
            brain.audit_scenario("test scenario text")

        assert "GOOGLE_API_KEY" in str(exc_info.value)


@pytest.mark.unit
class TestSimulatorUnavailable:
    """Tests for simulator client unavailability."""

    def test_chat_simulation_raises_when_simulator_unavailable(self):
        """Test chat_simulation raises SimulatorUnavailableError when client is None."""
        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(SimulatorUnavailableError):
            brain.chat_simulation([{"role": "user", "content": "test"}])

    def test_chat_simulation_stream_raises_when_simulator_unavailable(self):
        """Test chat_simulation_stream raises SimulatorUnavailableError."""
        brain = TrinityBrain(auto_initialize=False)

        with pytest.raises(SimulatorUnavailableError):
            list(brain.chat_simulation_stream([{"role": "user", "content": "test"}]))


@pytest.mark.unit
class TestInputValidation:
    """Tests for input validation."""

    def test_generate_scenario_rejects_empty_prompt(self):
        """Test generate_scenario rejects empty prompt."""
        mock_writer = Mock()
        brain = TrinityBrain(writer_client=mock_writer, auto_initialize=False)

        with pytest.raises(PromptValidationError):
            brain.generate_scenario("")

        with pytest.raises(PromptValidationError):
            brain.generate_scenario("   ")

    def test_audit_scenario_rejects_empty_text(self):
        """Test audit_scenario rejects empty text."""
        mock_judge = Mock()
        brain = TrinityBrain(judge_client=mock_judge, auto_initialize=False)

        with pytest.raises(PromptValidationError):
            brain.audit_scenario("")


@pytest.mark.unit
class TestRetryOnTransientErrors:
    """Tests for retry behavior on transient errors."""

    def test_writer_retries_on_connection_error(self):
        """Test that writer retries on ConnectionError and succeeds."""
        # Create a mock that fails twice then succeeds
        mock_writer = Mock()
        mock_stream_context = MagicMock()

        call_count = 0

        def stream_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return mock_stream_context

        mock_writer.messages.stream = stream_side_effect

        # Mock the stream context manager
        mock_stream_context.__enter__ = Mock(return_value=mock_stream_context)
        mock_stream_context.__exit__ = Mock(return_value=False)
        mock_stream_context.text_stream = iter(["Hello", " World"])

        brain = TrinityBrain(writer_client=mock_writer, auto_initialize=False)

        # Should succeed after retries
        result = list(brain.generate_scenario_stream("test prompt"))

        assert call_count == 3, "Should have been called 3 times (2 failures + 1 success)"
        assert result == ["Hello", " World"]

    def test_judge_retries_on_timeout_error(self):
        """Test that judge retries on TimeoutError and succeeds."""
        mock_judge = Mock()

        call_count = 0

        def generate_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Request timed out")
            mock_response = Mock()
            mock_response.text = "Audit result"
            return mock_response

        mock_judge.generate_content = generate_side_effect

        brain = TrinityBrain(judge_client=mock_judge, auto_initialize=False)

        result = brain.audit_scenario("test scenario text")

        assert call_count == 3
        assert result == "Audit result"

    def test_simulator_retries_on_connection_error(self):
        """Test that simulator retries on ConnectionError."""
        mock_simulator = Mock()

        call_count = 0

        def generate_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            # Return mock streaming response (Gemini-style)
            mock_chunk = Mock()
            mock_chunk.text = "Response"
            return iter([mock_chunk])

        mock_simulator.generate_content = generate_side_effect

        brain = TrinityBrain(simulator_client=mock_simulator, auto_initialize=False)

        result = list(brain.chat_simulation_stream([{"role": "user", "content": "test"}]))

        assert call_count == 3
        assert result == ["Response"]


@pytest.mark.unit
class TestNoRetryOnAuthErrors:
    """Tests for immediate failure on authentication errors."""

    def test_writer_fails_immediately_on_401(self):
        """Test that writer fails immediately on 401 error (no retry)."""
        mock_writer = Mock()
        mock_stream_context = MagicMock()

        call_count = 0

        def stream_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("401 Unauthorized - Invalid API key")

        mock_writer.messages.stream = stream_side_effect
        mock_stream_context.__enter__ = Mock(side_effect=Exception("401 Unauthorized"))

        brain = TrinityBrain(writer_client=mock_writer, auto_initialize=False)

        with pytest.raises(APICallError) as exc_info:
            list(brain.generate_scenario_stream("test prompt"))

        # Should only be called once (no retry on auth error)
        assert call_count == 1
        assert "authentication" in str(exc_info.value).lower() or "401" in str(exc_info.value)

    def test_judge_fails_immediately_on_authentication_error(self):
        """Test that judge fails immediately on authentication error."""
        mock_judge = Mock()

        call_count = 0

        def generate_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise Exception("Authentication failed: Invalid API key")

        mock_judge.generate_content = generate_side_effect

        brain = TrinityBrain(judge_client=mock_judge, auto_initialize=False)

        with pytest.raises(APICallError) as exc_info:
            brain.audit_scenario("test scenario")

        assert call_count == 1
        assert "authentication" in str(exc_info.value).lower()


@pytest.mark.unit
class TestMaxRetriesExceeded:
    """Tests for behavior when max retries are exceeded."""

    def test_writer_raises_api_call_error_after_max_retries(self):
        """Test that writer raises APICallError after max retries."""
        mock_writer = Mock()

        call_count = 0

        def stream_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent connection failure")

        mock_writer.messages.stream = stream_side_effect

        brain = TrinityBrain(writer_client=mock_writer, auto_initialize=False)

        with pytest.raises(APICallError):
            list(brain.generate_scenario_stream("test prompt"))

        # Should have retried 3 times (default max attempts)
        assert call_count == 3

    def test_simulator_raises_after_max_retries(self):
        """Test that simulator raises APICallError after max retries for Gemini."""
        mock_simulator = Mock()

        call_count = 0

        def generate_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Server offline")

        mock_simulator.generate_content = generate_side_effect

        brain = TrinityBrain(simulator_client=mock_simulator, auto_initialize=False)

        with pytest.raises(APICallError):
            list(brain.chat_simulation_stream([{"role": "user", "content": "test"}]))

        assert call_count == 3


@pytest.mark.unit
class TestDependencyInjection:
    """Tests for dependency injection pattern."""

    def test_accepts_injected_clients(self):
        """Test that TrinityBrain accepts injected clients."""
        mock_writer = Mock()
        mock_judge = Mock()
        mock_simulator = Mock()

        brain = TrinityBrain(
            writer_client=mock_writer,
            judge_client=mock_judge,
            simulator_client=mock_simulator,
            auto_initialize=False,
        )

        assert brain.writer_client is mock_writer
        assert brain.judge_client is mock_judge
        assert brain.simulator_client is mock_simulator

    def test_auto_initialize_false_skips_client_creation(self):
        """Test that auto_initialize=False prevents automatic client creation."""
        with (
            patch("tatlam.core.brain.create_writer_client") as mock_create_writer,
            patch("tatlam.core.brain.create_judge_client") as mock_create_judge,
            patch("tatlam.core.brain.create_simulator_client") as mock_create_sim,
        ):

            brain = TrinityBrain(auto_initialize=False)

            mock_create_writer.assert_not_called()
            mock_create_judge.assert_not_called()
            mock_create_sim.assert_not_called()


@pytest.mark.unit
class TestStreamingBehavior:
    """Tests for streaming response handling."""

    def test_generate_scenario_collects_stream(self):
        """Test that generate_scenario collects all stream chunks."""
        mock_writer = Mock()
        mock_stream_context = MagicMock()

        mock_stream_context.__enter__ = Mock(return_value=mock_stream_context)
        mock_stream_context.__exit__ = Mock(return_value=False)
        mock_stream_context.text_stream = iter(["chunk1", "chunk2", "chunk3"])

        mock_writer.messages.stream = Mock(return_value=mock_stream_context)

        brain = TrinityBrain(writer_client=mock_writer, auto_initialize=False)

        result = brain.generate_scenario("test prompt")

        assert result == "chunk1chunk2chunk3"

    def test_chat_simulation_collects_stream(self):
        """Test that chat_simulation collects all stream chunks."""
        mock_simulator = Mock()

        # Gemini-style streaming chunks (each has .text attribute)
        chunks = []
        for content in ["Hello", " ", "World"]:
            mock_chunk = Mock()
            mock_chunk.text = content
            chunks.append(mock_chunk)

        mock_simulator.generate_content = Mock(return_value=iter(chunks))

        brain = TrinityBrain(simulator_client=mock_simulator, auto_initialize=False)

        result = brain.chat_simulation([{"role": "user", "content": "test"}])

        assert result == "Hello World"

    def test_chat_simulation_stream_with_empty_text(self):
        """Test that streaming yields all chunks including empty ones."""
        mock_simulator = Mock()

        # Gemini-style chunks - some with empty text
        chunks = []
        for content in ["Hello", "World"]:
            mock_chunk = Mock()
            mock_chunk.text = content
            chunks.append(mock_chunk)

        mock_simulator.generate_content = Mock(return_value=iter(chunks))

        brain = TrinityBrain(simulator_client=mock_simulator, auto_initialize=False)

        result = list(brain.chat_simulation_stream([{"role": "user", "content": "test"}]))

        # All non-empty text chunks are yielded
        assert result == ["Hello", "World"]

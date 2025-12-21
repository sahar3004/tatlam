"""
Unit tests for tatlam/core/llm_factory.py

Tests LLM client factory functions and protocols.
Target: TrinityClients, factory functions, LLMRouter
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tatlam.core.llm_factory import (
    JudgeClientProtocol,
    LLMRouter,
    SimulatorClientProtocol,
    TrinityClients,
    WriterClientProtocol,
    create_all_clients,
    create_cloud_client,
    create_judge_client,
    create_simulator_client,
    create_writer_client,
)
from tatlam.settings import ConfigurationError


@pytest.mark.unit
class TestTrinityClients:
    """Test suite for TrinityClients container."""

    def test_empty_clients_container(self) -> None:
        """Test creating an empty clients container."""
        clients = TrinityClients()
        assert clients.writer is None
        assert clients.judge is None
        assert clients.simulator is None

    def test_has_writer_false_when_none(self) -> None:
        """Test has_writer returns False when writer is None."""
        clients = TrinityClients()
        assert clients.has_writer() is False

    def test_has_writer_true_when_set(self) -> None:
        """Test has_writer returns True when writer is set."""
        mock_writer = MagicMock()
        clients = TrinityClients(writer=mock_writer)
        assert clients.has_writer() is True

    def test_has_judge_false_when_none(self) -> None:
        """Test has_judge returns False when judge is None."""
        clients = TrinityClients()
        assert clients.has_judge() is False

    def test_has_judge_true_when_set(self) -> None:
        """Test has_judge returns True when judge is set."""
        mock_judge = MagicMock()
        clients = TrinityClients(judge=mock_judge)
        assert clients.has_judge() is True

    def test_has_simulator_false_when_none(self) -> None:
        """Test has_simulator returns False when simulator is None."""
        clients = TrinityClients()
        assert clients.has_simulator() is False

    def test_has_simulator_true_when_set(self) -> None:
        """Test has_simulator returns True when simulator is set."""
        mock_simulator = MagicMock()
        clients = TrinityClients(simulator=mock_simulator)
        assert clients.has_simulator() is True

    def test_all_clients_set(self) -> None:
        """Test container with all clients set."""
        mock_writer = MagicMock()
        mock_judge = MagicMock()
        mock_simulator = MagicMock()
        clients = TrinityClients(
            writer=mock_writer,
            judge=mock_judge,
            simulator=mock_simulator,
        )
        assert clients.has_writer() is True
        assert clients.has_judge() is True
        assert clients.has_simulator() is True


@pytest.mark.unit
class TestWriterClientProtocol:
    """Test suite for WriterClientProtocol."""

    def test_protocol_requires_messages_property(self) -> None:
        """Test that protocol requires messages property."""

        class ValidWriterClient:
            @property
            def messages(self) -> Any:
                return MagicMock()

        client = ValidWriterClient()
        assert isinstance(client, WriterClientProtocol)

    def test_protocol_fails_without_messages(self) -> None:
        """Test that class without messages property is not valid."""

        class InvalidWriterClient:
            pass

        client = InvalidWriterClient()
        assert not isinstance(client, WriterClientProtocol)


@pytest.mark.unit
class TestJudgeClientProtocol:
    """Test suite for JudgeClientProtocol."""

    def test_protocol_requires_generate_content(self) -> None:
        """Test that protocol requires generate_content method."""

        class ValidJudgeClient:
            def generate_content(self, prompt: str) -> Any:
                return MagicMock()

        client = ValidJudgeClient()
        assert isinstance(client, JudgeClientProtocol)

    def test_protocol_fails_without_generate_content(self) -> None:
        """Test that class without generate_content is not valid."""

        class InvalidJudgeClient:
            pass

        client = InvalidJudgeClient()
        assert not isinstance(client, JudgeClientProtocol)


@pytest.mark.unit
class TestSimulatorClientProtocol:
    """Test suite for SimulatorClientProtocol."""

    def test_protocol_requires_chat_property(self) -> None:
        """Test that protocol requires chat property."""

        class ValidSimulatorClient:
            @property
            def chat(self) -> Any:
                return MagicMock()

        client = ValidSimulatorClient()
        assert isinstance(client, SimulatorClientProtocol)

    def test_protocol_fails_without_chat(self) -> None:
        """Test that class without chat property is not valid."""

        class InvalidSimulatorClient:
            pass

        client = InvalidSimulatorClient()
        assert not isinstance(client, SimulatorClientProtocol)


@pytest.mark.unit
class TestCreateWriterClient:
    """Test suite for create_writer_client factory function."""

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("anthropic.Anthropic")
    def test_creates_client_with_api_key(
        self, mock_anthropic: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test creating client with explicit API key."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"

        result = create_writer_client(api_key="explicit-key")

        mock_anthropic.assert_called_once_with(api_key="explicit-key")
        assert result == mock_client

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("anthropic.Anthropic")
    def test_uses_settings_api_key_when_not_provided(
        self, mock_anthropic: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test using API key from settings when not explicitly provided."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_settings.return_value.ANTHROPIC_API_KEY = "settings-key"

        result = create_writer_client()

        mock_anthropic.assert_called_once_with(api_key="settings-key")
        assert result == mock_client

    @patch("tatlam.core.llm_factory.get_settings")
    def test_returns_none_when_no_api_key(self, mock_settings: MagicMock) -> None:
        """Test returning None when API key is not configured."""
        mock_settings.return_value.ANTHROPIC_API_KEY = ""

        result = create_writer_client()

        assert result is None

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("anthropic.Anthropic")
    def test_raises_configuration_error_on_failure(
        self, mock_anthropic: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test raising ConfigurationError when client initialization fails."""
        mock_anthropic.side_effect = Exception("Connection failed")
        mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"

        with pytest.raises(ConfigurationError) as exc_info:
            create_writer_client()

        assert "Failed to initialize Anthropic client" in str(exc_info.value)


@pytest.mark.unit
class TestCreateJudgeClient:
    """Test suite for create_judge_client factory function."""

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("google.generativeai.configure")
    @patch("google.generativeai.GenerativeModel")
    def test_creates_client_with_api_key(
        self,
        mock_model: MagicMock,
        mock_configure: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test creating client with explicit API key."""
        mock_client = MagicMock()
        mock_model.return_value = mock_client
        mock_settings.return_value.GOOGLE_API_KEY = "test-key"
        mock_settings.return_value.JUDGE_MODEL_NAME = "gemini-pro"

        result = create_judge_client(api_key="explicit-key")

        mock_configure.assert_called_once_with(api_key="explicit-key")
        mock_model.assert_called_once_with("gemini-pro")
        assert result == mock_client

    @patch("tatlam.core.llm_factory.get_settings")
    def test_returns_none_when_no_api_key(self, mock_settings: MagicMock) -> None:
        """Test returning None when API key is not configured."""
        mock_settings.return_value.GOOGLE_API_KEY = ""

        result = create_judge_client()

        assert result is None


@pytest.mark.unit
class TestCreateSimulatorClient:
    """Test suite for create_simulator_client factory function."""

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("openai.OpenAI")
    def test_creates_client_with_url_and_key(
        self, mock_openai: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test creating client with explicit URL and API key."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_settings.return_value.LOCAL_BASE_URL = "http://localhost:11434"
        mock_settings.return_value.LOCAL_API_KEY = "local-key"

        result = create_simulator_client(
            base_url="http://custom:8000", api_key="custom-key"
        )

        mock_openai.assert_called_once_with(
            base_url="http://custom:8000", api_key="custom-key"
        )
        assert result == mock_client

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("openai.OpenAI")
    def test_uses_settings_when_not_provided(
        self, mock_openai: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test using settings values when not explicitly provided."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_settings.return_value.LOCAL_BASE_URL = "http://default:11434"
        mock_settings.return_value.LOCAL_API_KEY = "default-key"

        result = create_simulator_client()

        mock_openai.assert_called_once_with(
            base_url="http://default:11434", api_key="default-key"
        )
        assert result == mock_client


@pytest.mark.unit
class TestCreateCloudClient:
    """Test suite for create_cloud_client factory function."""

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("openai.OpenAI")
    def test_creates_client_with_api_key(
        self, mock_openai: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test creating cloud client with API key."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_settings.return_value.OPENAI_API_KEY = "openai-key"
        mock_settings.return_value.OPENAI_BASE_URL = "https://api.openai.com"

        result = create_cloud_client()

        assert result == mock_client

    @patch("tatlam.core.llm_factory.get_settings")
    def test_returns_none_when_no_api_key(self, mock_settings: MagicMock) -> None:
        """Test returning None when OPENAI_API_KEY is not configured."""
        mock_settings.return_value.OPENAI_API_KEY = ""
        mock_settings.return_value.OPENAI_BASE_URL = "https://api.openai.com"

        result = create_cloud_client()

        assert result is None


@pytest.mark.unit
class TestCreateAllClients:
    """Test suite for create_all_clients factory function."""

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_creates_all_clients(
        self,
        mock_simulator: MagicMock,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
    ) -> None:
        """Test creating all clients successfully."""
        mock_writer.return_value = MagicMock()
        mock_judge.return_value = MagicMock()
        mock_simulator.return_value = MagicMock()

        result = create_all_clients()

        assert isinstance(result, TrinityClients)
        assert result.has_writer() is True
        assert result.has_judge() is True
        assert result.has_simulator() is True

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_handles_partial_failures(
        self,
        mock_simulator: MagicMock,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
    ) -> None:
        """Test that partial failures don't prevent other clients from initializing."""
        mock_writer.side_effect = ConfigurationError("Writer failed")
        mock_judge.return_value = MagicMock()
        mock_simulator.return_value = MagicMock()

        result = create_all_clients()

        assert result.has_writer() is False
        assert result.has_judge() is True
        assert result.has_simulator() is True

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_fail_on_missing_raises_error(
        self,
        mock_simulator: MagicMock,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
    ) -> None:
        """Test that fail_on_missing=True raises on first failure."""
        mock_writer.side_effect = ConfigurationError("Writer failed")

        with pytest.raises(ConfigurationError):
            create_all_clients(fail_on_missing=True)

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_passes_custom_keys(
        self,
        mock_simulator: MagicMock,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
    ) -> None:
        """Test that custom keys are passed to factory functions."""
        mock_writer.return_value = MagicMock()
        mock_judge.return_value = MagicMock()
        mock_simulator.return_value = MagicMock()

        create_all_clients(
            writer_key="custom-writer",
            judge_key="custom-judge",
            simulator_url="http://custom:8000",
            simulator_key="custom-sim",
        )

        mock_writer.assert_called_once_with("custom-writer")
        mock_judge.assert_called_once_with("custom-judge")
        mock_simulator.assert_called_once_with(
            "http://custom:8000", "custom-sim"
        )


@pytest.mark.unit
class TestLLMRouter:
    """Test suite for LLMRouter with Gemini fallback."""

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_initializes_with_available_clients(
        self,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
        mock_simulator: MagicMock,
    ) -> None:
        """Test router initializes with all available clients."""
        mock_local = MagicMock()
        mock_anthropic = MagicMock()
        mock_gemini = MagicMock()

        mock_simulator.return_value = mock_local
        mock_writer.return_value = mock_anthropic
        mock_judge.return_value = mock_gemini

        router = LLMRouter()

        assert router.local_client == mock_local
        assert router.anthropic_client == mock_anthropic
        assert router.gemini_client == mock_gemini

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_handles_initialization_failures_gracefully(
        self,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
        mock_simulator: MagicMock,
    ) -> None:
        """Test router handles client initialization failures gracefully."""
        mock_simulator.side_effect = ConfigurationError("Local failed")
        mock_writer.side_effect = ConfigurationError("Writer failed")
        mock_judge.return_value = MagicMock()

        router = LLMRouter()

        assert router.local_client is None
        assert router.anthropic_client is None
        assert router.gemini_client is not None

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_chat_complete_with_local_client(
        self,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
        mock_simulator: MagicMock,
    ) -> None:
        """Test chat_complete uses local client when available."""
        mock_local = MagicMock()
        mock_response = MagicMock()
        mock_local.chat.completions.create.return_value = mock_response
        mock_simulator.return_value = mock_local
        mock_writer.return_value = None
        mock_judge.return_value = None

        router = LLMRouter()
        messages = [{"role": "user", "content": "Hello"}]

        result = router.chat_complete(messages, model="local")

        mock_local.chat.completions.create.assert_called_once()
        assert result == mock_response

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_chat_complete_falls_back_to_gemini(
        self,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
        mock_simulator: MagicMock,
    ) -> None:
        """Test chat_complete falls back to Gemini when primary fails."""
        mock_local = MagicMock()
        mock_local.chat.completions.create.side_effect = Exception("Local unreachable")

        mock_gemini = MagicMock()
        mock_gemini_response = MagicMock()
        mock_gemini.generate_content.return_value = mock_gemini_response

        mock_simulator.return_value = mock_local
        mock_writer.return_value = None
        mock_judge.return_value = mock_gemini

        router = LLMRouter()
        messages = [{"role": "user", "content": "Hello"}]

        result = router.chat_complete(messages, model="local")

        mock_gemini.generate_content.assert_called_once()
        assert result == mock_gemini_response

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_chat_complete_raises_when_all_fail(
        self,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
        mock_simulator: MagicMock,
    ) -> None:
        """Test chat_complete raises ConfigurationError when all providers fail."""
        mock_local = MagicMock()
        mock_local.chat.completions.create.side_effect = Exception("Local failed")

        mock_gemini = MagicMock()
        mock_gemini.generate_content.side_effect = Exception("Gemini failed")

        mock_simulator.return_value = mock_local
        mock_writer.return_value = None
        mock_judge.return_value = mock_gemini

        router = LLMRouter()
        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(ConfigurationError) as exc_info:
            router.chat_complete(messages, model="local")

        assert "All LLM providers failed" in str(exc_info.value)

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_chat_complete_anthropic_format(
        self,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
        mock_simulator: MagicMock,
    ) -> None:
        """Test chat_complete converts to Anthropic format."""
        mock_anthropic = MagicMock()
        mock_response = MagicMock()
        mock_anthropic.messages.create.return_value = mock_response

        mock_simulator.return_value = None
        mock_writer.return_value = mock_anthropic
        mock_judge.return_value = None

        router = LLMRouter()
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]

        result = router.chat_complete(messages, model="anthropic")

        mock_anthropic.messages.create.assert_called_once()
        call_args = mock_anthropic.messages.create.call_args
        assert call_args.kwargs["system"] == "You are helpful"
        assert result == mock_response

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_chat_complete_no_gemini_fallback_raises(
        self,
        mock_judge: MagicMock,
        mock_writer: MagicMock,
        mock_simulator: MagicMock,
    ) -> None:
        """Test that missing Gemini fallback raises ConfigurationError."""
        mock_local = MagicMock()
        mock_local.chat.completions.create.side_effect = Exception("Local failed")

        mock_simulator.return_value = mock_local
        mock_writer.return_value = None
        mock_judge.return_value = None  # No Gemini

        router = LLMRouter()
        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(ConfigurationError) as exc_info:
            router.chat_complete(messages, model="local")

        assert "Gemini fallback not configured" in str(exc_info.value)

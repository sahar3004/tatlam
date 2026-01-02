import pytest
from unittest.mock import MagicMock, patch
from tatlam.core.llm_factory import create_all_clients, LLMRouter, ConfigurationError


class TestLLMFactoryExtra:

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_create_all_clients_success(self, mock_sim, mock_judge, mock_writer):
        clients = create_all_clients()
        assert clients.writer is not None
        assert clients.judge is not None
        assert clients.simulator is not None

        # Check has_* methods
        clients.writer = "exists"
        assert clients.has_writer()
        clients.judge = None
        assert not clients.has_judge()

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_create_all_clients_partial_failure(self, mock_sim, mock_judge, mock_writer):
        mock_writer.side_effect = ConfigurationError("fail")

        # Should not raise by default
        clients = create_all_clients(fail_on_missing=False)
        assert clients.writer is None

        # Should raise if requested
        mock_writer.side_effect = ConfigurationError("fail")
        with pytest.raises(ConfigurationError):
            create_all_clients(fail_on_missing=True)


class TestLLMRouter:

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_router_init(self, mock_sim, mock_judge, mock_writer):
        mock_sim.return_value = "local"
        mock_writer.return_value = "anthropic"
        mock_judge.return_value = "gemini"

        router = LLMRouter()
        assert router.local_client == "local"

    def test_router_chat_complete_local(self):
        router = LLMRouter()
        router.local_client = MagicMock()
        router.local_client.chat.completions.create.return_value = "success"

        res = router.chat_complete([], model="local")
        assert res == "success"

    def test_router_chat_complete_anthropic(self):
        router = LLMRouter()
        router.anthropic_client = MagicMock()
        router.anthropic_client.messages.create.return_value = "success"

        res = router.chat_complete([{"role": "user", "content": "hi"}], model="anthropic")
        assert res == "success"

    def test_router_fallback(self):
        router = LLMRouter()
        router.local_client = MagicMock()
        router.local_client.chat.completions.create.side_effect = Exception("fail")

        router.gemini_client = MagicMock()
        router.gemini_client.generate_content.return_value = "fallback"

        res = router.chat_complete([], model="local")
        assert res == "fallback"

    def test_router_all_fail(self):
        router = LLMRouter()
        router.local_client = MagicMock()
        router.local_client.chat.completions.create.side_effect = Exception("fail")
        router.gemini_client = MagicMock()
        router.gemini_client.generate_content.side_effect = Exception("fail too")

        with pytest.raises(ConfigurationError):
            router.chat_complete([], model="local")

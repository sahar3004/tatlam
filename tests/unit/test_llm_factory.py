from unittest.mock import patch
from tatlam.core.llm_factory import (
    create_writer_client,
    create_judge_client,
    create_simulator_client,
    client_local,
    client_cloud,
)


class TestLLMFactory:

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_writer_client_success(self, mock_settings):
        mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
        with patch("anthropic.Anthropic") as mock_anthropic:
            client = create_writer_client()
            assert client is not None
            mock_anthropic.assert_called_with(api_key="test-key")

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_writer_client_missing_key(self, mock_settings):
        # Empty key, configured via pydantic
        mock_settings.return_value.ANTHROPIC_API_KEY = ""
        mock_settings.return_value.USE_MOCK_LLM = False  # Ensure not mock

        # Factory returns None log warning
        client = create_writer_client()
        assert client is None

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_judge_client_success(self, mock_settings):
        mock_settings.return_value.GOOGLE_API_KEY = "test-key"
        with patch("google.generativeai.GenerativeModel") as mock_model:
            with patch("google.generativeai.configure") as mock_conf:
                client = create_judge_client()
                assert client is not None
                mock_conf.assert_called_with(api_key="test-key")

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_judge_client_missing_key(self, mock_settings):
        mock_settings.return_value.GOOGLE_API_KEY = ""
        # Returns None
        client = create_judge_client()
        assert client is None

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_simulator_client_success(self, mock_settings):
        mock_settings.return_value.GOOGLE_API_KEY = "test-key"
        mock_settings.return_value.SIMULATOR_MODEL_NAME = "gemini-3-flash-preview"
        with patch("google.generativeai.GenerativeModel") as mock_model:
            with patch("google.generativeai.configure") as mock_conf:
                client = create_simulator_client()
                assert client is not None
                mock_conf.assert_called_with(api_key="test-key")

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_simulator_client_missing_key(self, mock_settings):
        mock_settings.return_value.GOOGLE_API_KEY = ""
        # Returns None when no key
        client = create_simulator_client()
        assert client is None

    def test_client_local(self):
        # Legacy function coverage
        with patch("tatlam.core.llm_factory.create_simulator_client") as mock_create:
            mock_create.return_value = "client"
            assert client_local() == "client"

    def test_client_cloud(self):
        # Legacy function coverage
        with patch("tatlam.core.llm_factory.create_cloud_client") as mock_create:
            mock_create.return_value = "client"
            assert client_cloud() == "client"

        # Original fail was assertion mismatch because it returned MagicMock instead of "client" string?
        # Because we mocked create_writer_client in original file but client_cloud calls create_cloud_client.
        # Fixed patches above.

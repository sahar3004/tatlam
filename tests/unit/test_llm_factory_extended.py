from unittest.mock import MagicMock, patch
import pytest
from tatlam.core.llm_factory import (
    AnthropicJudgeAdapter,
    create_judge_client,
    create_all_clients,
    create_cloud_client,
    LLMRouter,
    ConfigurationError,
    create_writer_client,
    create_simulator_client
)

class TestLLMFactoryExtended:

    def test_anthropic_judge_adapter(self):
        """Test that adapter matches Google interface."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response
        
        adapter = AnthropicJudgeAdapter(mock_client, "claude-3-opus")
        result = adapter.generate_content("prompt")
        
        assert result.text == "Response"
        mock_client.messages.create.assert_called_once()
        args = mock_client.messages.create.call_args[1]
        assert args["model"] == "claude-3-opus"
        assert args["messages"][0]["content"] == "prompt"
        
        # Test error propagation
        mock_client.messages.create.side_effect = Exception("Anthropic Error")
        with pytest.raises(Exception, match="Anthropic Error"):
            adapter.generate_content("prompt")

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("tatlam.core.llm_factory.create_writer_client")
    def test_create_judge_client_anthropic_fallback(self, mock_create_writer, mock_settings):
        """Test Judge creation falling back to Anthropic."""
        mock_settings.return_value.JUDGE_MODEL_PROVIDER = "anthropic"
        mock_settings.return_value.JUDGE_MODEL_NAME = "claude-opus"
        mock_settings.return_value.ANTHROPIC_API_KEY = "test-key"
        
        mock_anthro = MagicMock()
        mock_create_writer.return_value = mock_anthro
        
        client = create_judge_client()
        assert isinstance(client, AnthropicJudgeAdapter)
        assert client.client == mock_anthro
        
        # Fail to create anthropic -> fallback to google
        mock_create_writer.side_effect = Exception("Fail")
        mock_settings.return_value.GOOGLE_API_KEY = "google-key"
        
        with patch("google.generativeai.configure") as mock_conf:
            with patch("google.generativeai.GenerativeModel") as mock_model:
                client2 = create_judge_client()
                assert client2 == mock_model.return_value

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_create_all_clients(self, mock_sim, mock_judge, mock_writer):
        """Test mass client creation."""
        mock_writer.return_value = "writer"
        mock_judge.return_value = "judge"
        mock_sim.return_value = "sim"
        
        clients = create_all_clients()
        assert clients.writer == "writer"
        assert clients.judge == "judge"
        assert clients.simulator == "sim"
        assert clients.has_writer()
        assert clients.has_judge()
        assert clients.has_simulator()
        
        # Test failure handling
        mock_writer.side_effect = ConfigurationError("Bad Writer")
        
        # Non-strict
        clients2 = create_all_clients(fail_on_missing=False)
        assert clients2.writer is None
        assert clients2.judge == "judge"
        
        # Strict
        with pytest.raises(ConfigurationError, match="Bad Writer"):
            create_all_clients(fail_on_missing=True)

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_cloud_client(self, mock_settings):
        """Test OpenAI cloud client creation."""
        mock_settings.return_value.OPENAI_API_KEY = "sk-test"
        mock_settings.return_value.OPENAI_BASE_URL = "https://api.openai.com/v1"
        
        with patch("openai.OpenAI") as mock_openai:
            client = create_cloud_client()
            assert client is not None
            mock_openai.assert_called_with(api_key="sk-test", base_url="https://api.openai.com/v1")
            
        # Exception
        with patch("openai.OpenAI", side_effect=Exception("Net Error")):
            with pytest.raises(ConfigurationError):
                create_cloud_client()
                
        # Missing key
        mock_settings.return_value.OPENAI_API_KEY = None
        assert create_cloud_client() is None

    @patch("tatlam.core.llm_factory.create_writer_client")
    def test_create_writer_client_exception(self, mock_create):
        # We need to test the exception block in the function itself, not mock the function
        pass

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_writer_client_error(self, mock_settings):
        # Actual test for exception block in create_writer_client
        mock_settings.return_value.ANTHROPIC_API_KEY = "key"
        with patch("anthropic.Anthropic", side_effect=Exception("Init Fail")):
            with pytest.raises(ConfigurationError, match="Init Fail"):
                create_writer_client()
                
    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_judge_client_error(self, mock_settings):
        mock_settings.return_value.JUDGE_MODEL_PROVIDER = "google"
        mock_settings.return_value.GOOGLE_API_KEY = "key"
        with patch("google.generativeai.configure", side_effect=Exception("Init Fail")):
            with pytest.raises(ConfigurationError, match="Init Fail"):
                create_judge_client()

    @patch("tatlam.core.llm_factory.get_settings")
    def test_create_simulator_client_error(self, mock_settings):
        mock_settings.return_value.GOOGLE_API_KEY = "key"
        with patch("google.generativeai.configure", side_effect=Exception("Init Fail")):
            with pytest.raises(ConfigurationError, match="Init Fail"):
                create_simulator_client()

    # --- Router Tests ---

    @patch("tatlam.core.llm_factory.create_simulator_client")
    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    def test_llm_router_init(self, mock_judge, mock_writer, mock_sim):
        mock_sim.return_value = "local"
        mock_writer.return_value = "anthropic"
        mock_judge.return_value = "gemini"
        
        router = LLMRouter()
        assert router.local_client == "local"
        assert router.anthropic_client == "anthropic"
        assert router.gemini_client == "gemini"
        
        # Test partial fail
        mock_sim.side_effect = Exception("Local Down")
        mock_writer.side_effect = Exception("Anthropic Down")
        
        router2 = LLMRouter()
        assert router2.local_client is None
        assert router2.anthropic_client is None
        assert router2.gemini_client == "gemini"
        
        # Test all fail logs warning (no assert for log unless we capture logs, but ensures no crash)
        mock_judge.side_effect = Exception("Gemini Down")
        router3 = LLMRouter()
        assert router3.gemini_client is None

    def test_llm_router_chat_complete(self):
        """Test routing logic."""
        router = LLMRouter()
        # Manually inject mocks
        router.local_client = MagicMock()
        router.anthropic_client = MagicMock()
        router.gemini_client = MagicMock()
        
        messages = [{"role": "user", "content": "Hi"}]
        
        # 1. Local success
        router.chat_complete(messages, model="local")
        router.local_client.chat.completions.create.assert_called_once()
        
        # 2. Anthropic success
        # Need system message handling check
        msgs_sys = [{"role": "system", "content": "Sys"}, {"role": "user", "content": "U"}]
        router.chat_complete(msgs_sys, model="anthropic")
        router.anthropic_client.messages.create.assert_called_once()
        args = router.anthropic_client.messages.create.call_args[1]
        assert args["system"] == "Sys"
        assert len(args["messages"]) == 1 # Only user
        
        # 3. Fallback to Gemini
        router.local_client.chat.completions.create.side_effect = Exception("Fail")
        router.gemini_client.generate_content.return_value = "Gemini Resp"
        
        resp = router.chat_complete(messages, model="local")
        assert resp == "Gemini Resp"
        router.gemini_client.generate_content.assert_called_once()
        
        # 4. Total Failure
        router.gemini_client.generate_content.side_effect = Exception("Gemini Fail")
        with pytest.raises(ConfigurationError, match="All LLM providers failed"):
            router.chat_complete(messages, model="local")
            
    def test_llm_router_chat_complete_edge_cases(self):
        """Test edge cases in router."""
        router = LLMRouter()
        router.gemini_client = MagicMock()
        
        # 1. Model="anthropic" requested but client missing -> Fallback
        router.anthropic_client = None
        # We need to ensure fallback works
        router.gemini_client.generate_content.return_value = "Fallback"
        
        # This hits the 'elif model == "anthropic" and ...' False branch
        # And goes to 'except Exception' block? No, it just bypasses the block and goes to fallback logic below.
        # Wait, the code structure:
        # try:
        #    if ...
        #    elif ...
        # except: ...
        # Fallback check...
        
        # If if/elif doesn't match, it falls through to fallback check.
        resp = router.chat_complete([{"role": "user", "content": "hi"}], model="anthropic")
        assert resp == "Fallback"
        
        # 2. Anthropic with no system message
        router.anthropic_client = MagicMock()
        router.anthropic_client.messages.create.return_value = "AnthroResp"
        
        # Should work safely
        router.chat_complete([{"role": "user", "content": "hi"}], model="anthropic")
        router.anthropic_client.messages.create.assert_called()
        args = router.anthropic_client.messages.create.call_args[1]
        assert args["system"] == ""

    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_client_local_failure(self, mock_create):
        # Test client_local when simulator creation returns None
        mock_create.return_value = None
        from tatlam.core.llm_factory import client_local
        with pytest.raises(ConfigurationError):
            client_local()

    @patch("tatlam.core.llm_factory.create_cloud_client")
    def test_client_cloud_failure(self, mock_create):
         # Test client_cloud when creation returns None
         mock_create.return_value = None
         from tatlam.core.llm_factory import client_cloud
         with pytest.raises(ConfigurationError):
             client_cloud()

    @patch("tatlam.core.llm_factory.create_writer_client")
    @patch("tatlam.core.llm_factory.create_judge_client")
    @patch("tatlam.core.llm_factory.create_simulator_client")
    def test_create_all_clients_partial_failures(self, mock_sim, mock_judge, mock_writer):
        """Test create_all_clients with judge/sim failures."""
        mock_writer.return_value = "writer"
        
        # Judge fails
        mock_judge.side_effect = ConfigurationError("Judge Fail")
        
        # Sim fails
        mock_sim.side_effect = ConfigurationError("Sim Fail")
        
        # Non-strict - should succeed partially
        clients = create_all_clients(fail_on_missing=False)
        assert clients.writer == "writer"
        assert clients.judge is None
        assert clients.simulator is None
        
        # Strict - should fail on Judge (first fail)
        mock_judge.side_effect = ConfigurationError("Judge Fail") 
        mock_sim.side_effect = None # Reset
        
        with pytest.raises(ConfigurationError, match="Judge Fail"):
            create_all_clients(fail_on_missing=True)
            
        # Strict - fail on Sim
        mock_judge.side_effect = None
        mock_judge.return_value = "judge"
        mock_sim.side_effect = ConfigurationError("Sim Fail")
        
        with pytest.raises(ConfigurationError, match="Sim Fail"):
            create_all_clients(fail_on_missing=True)

    @patch("tatlam.core.llm_factory.get_settings")
    @patch("tatlam.core.llm_factory.create_writer_client")
    def test_create_judge_client_anthropic_no_key(self, mock_create_writer, mock_settings):
        """Test judge anthropic fallback when key is missing."""
        mock_settings.return_value.JUDGE_MODEL_PROVIDER = "anthropic"
        # create_writer_client returns None if key missing
        mock_create_writer.return_value = None
        mock_settings.return_value.GOOGLE_API_KEY = "google-key"
        
        with patch("google.generativeai.configure"):
             with patch("google.generativeai.GenerativeModel") as mock_model:
                 # Should skip anthropic and go to google
                 client = create_judge_client()
                 assert client == mock_model.return_value



import pytest
from unittest.mock import MagicMock, patch
from tatlam.core.local_llm import LocalQwenProvider

class TestLocalLLM:
    
    @patch("tatlam.core.local_llm.Path.exists")
    @patch("tatlam.core.local_llm.Llama")
    def test_init_local_qwen(self, MockLlama, MockExists):
        MockExists.return_value = True
        provider = LocalQwenProvider(model_path="/path/to/model", n_ctx=2048)
        assert provider.model_path == "/path/to/model"
        MockLlama.assert_called_with(
            model_path="/path/to/model",
            n_ctx=2048,
            n_threads=8, # default
            n_gpu_layers=-1, # default
            verbose=False
        )

    @patch("tatlam.core.local_llm.Path.exists")
    def test_generate(self, MockExists):
        MockExists.return_value = True
        with patch("tatlam.core.local_llm.Llama") as MockLlama:
            mock_instance = MockLlama.return_value
            mock_instance.create_completion.return_value = {
                "choices": [{"text": "generated text"}]
            }
            
            provider = LocalQwenProvider(model_path="path")
            result = provider.generate("prompt")
            assert result == "generated text"
            mock_instance.create_completion.assert_called()

    @patch("tatlam.core.local_llm.Path.exists")
    def test_create_chat_completion(self, MockExists):
        MockExists.return_value = True
        with patch("tatlam.core.local_llm.Llama") as MockLlama:
            mock_instance = MockLlama.return_value
            mock_instance.create_chat_completion.return_value = {
                "choices": [{"message": {"content": "response"}}]
            }
            
            provider = LocalQwenProvider(model_path="path")
            result = provider.create_chat_completion([{"role": "user", "content": "hi"}])
            assert result["choices"][0]["message"]["content"] == "response"

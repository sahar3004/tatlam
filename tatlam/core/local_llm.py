import time
import sys
from pathlib import Path
from typing import Any, Iterator, List, Dict, Union
try:
    from llama_cpp import Llama
except ImportError:
    raise ImportError("llama-cpp-python is not installed. Please install it with Metal support.")

class LocalQwenProvider:
    """
    Local LLM provider utilizing Qwen2.5-32B via llama.cpp with Metal acceleration.
    """
    def __init__(self, 
                 model_path: str = "/Users/sahar.miterani/models/Qwen2.5-32B-Instruct-Q5_K_M.gguf",
                 n_ctx: int = 8192,
                 n_gpu_layers: int = -1,
                 verbose: bool = False):
        
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
            
        print(f"🔄 Loading Local LLM: {self.model_path.name}")
        print(f"   Context: {n_ctx}, GPU Layers: {n_gpu_layers} (Metal)")
        
        self.llm = Llama(
            model_path=str(self.model_path),
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=verbose,
            n_batch=512, # Optimized for M-series
            logits_all=True
        )
        print("✅ Local LLM Loaded")

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """
        Generate text completion for the given prompt.
        """
        start_t = time.time()
        
        # Qwen2.5 instruct format
        formatted_prompt = (
            "<|im_start|>system\nYou are a helpful assistant.\n<|im_end|>\n"
            f"<|im_start|>user\n{prompt}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        
        output = self.llm(
            formatted_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=["<|im_end|>"],
            echo=False
        )
        
        response_text = output["choices"][0]["text"]
        
        # Simple metrics logging
        elapsed = time.time() - start_t
        usage = output.get('usage', {})
        completion_tokens = usage.get('completion_tokens', 0)
        tps = completion_tokens / elapsed if elapsed > 0 else 0
        
        print(f"⚡ Gen: {completion_tokens} tokens in {elapsed:.2f}s ({tps:.2f} t/s)")
        
        return response_text

    def create_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        """
        OpenAI-compatible chat completion method using llama-cpp-python's built-in handler.
        """
        return self.llm.create_chat_completion(messages=messages, **kwargs)


# ==== Adapter for Trinity Architecture ====

class _DictToObj:
    """Helper to convert dict keys to attributes for OpenAI compatibility."""
    def __init__(self, d):
        for k, v in d.items():
            if isinstance(v, (list, tuple)):
                setattr(self, k, [_DictToObj(x) if isinstance(x, dict) else x for x in v])
            else:
                setattr(self, k, _DictToObj(v) if isinstance(v, dict) else v)

    def __getattr__(self, name):
        # Return None for missing attributes to mimic optional fields in Pydantic models
        return None

class LocalLLMAdapter:
    """
    Adapter to make LocalQwenProvider compatible with SimulatorClientProtocol (OpenAI-like).
    Exposes client.chat.completions.create()
    """
    def __init__(self, provider: LocalQwenProvider):
        self.provider = provider
        self.chat = self.ChatNamespace(provider)

    class ChatNamespace:
        def __init__(self, provider):
            self.completions = self.CompletionsNamespace(provider)

        class CompletionsNamespace:
            def __init__(self, provider):
                self.provider = provider

            def create(self, messages: List[Dict[str, str]], **kwargs) -> Any:
                # Delegate to the provider's OpenAI-compatible method
                response = self.provider.create_chat_completion(messages, **kwargs)
                
                # If streaming, we need to wrap chunks to allow dot access
                if kwargs.get("stream"):
                    return ( _DictToObj(chunk) for chunk in response )
                
                # If not streaming, wrap the full response
                return _DictToObj(response)


if __name__ == "__main__":
    # Simple manual test if run directly
    try:
        provider = LocalQwenProvider(verbose=True)
        print("\nTest Response:")
        print(provider.generate("Hello, who are you?"))
    except Exception as e:
        print(f"Failed to run: {e}")

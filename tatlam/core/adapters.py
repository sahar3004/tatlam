"""
tatlam/core/adapters.py - Adapters for Cross-Provider Compatibility and Fallback

This module implements the Adapter pattern to make different LLM providers
(Local, Anthropic, Google) interchangeable within the Trinity architecture.
It also provides Fallback wrappers to ensure system resilience.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Protocol

from tatlam.core.llm_factory import WriterClientProtocol, JudgeClientProtocol, SimulatorClientProtocol
from tatlam.core.local_llm import LocalQwenProvider

logger = logging.getLogger(__name__)

# ==== Helper Classes ====

class _DictToObj:
    """Helper to convert dict keys to attributes for OpenAI compatibility."""
    def __init__(self, d):
        for k, v in d.items():
            if isinstance(v, (list, tuple)):
                setattr(self, k, [_DictToObj(x) if isinstance(x, dict) else x for x in v])
            else:
                setattr(self, k, _DictToObj(v) if isinstance(v, dict) else v)

    def __getattr__(self, name):
        return None

# ==== Local Adapters ====

class LocalAsWriterAdapter:
    """
    Adapts LocalQwenProvider to look like an Anthropic client (Writer).
    Implements: client.messages.stream(...)
    """
    def __init__(self, provider: LocalQwenProvider):
        self.provider = provider
        self.messages = self.Messages(provider)

    class Messages:
        def __init__(self, provider):
            self.provider = provider

        def stream(self, messages: List[Dict[str, str]], system: str = "", max_tokens: int = 4096, **kwargs) -> Any:
            """
            Simulate Anthropic's messages.stream API.
            Note: Anthropic separates 'system' from 'messages'.
            """
            # Merge system prompt into messages for Local/OpenAI format
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            # Use the provider's OpenAI-compatible completion
            # We need to yield chunks that look like Anthropic events
            # But TrinityBrain just iterates over them and expects `text`?
            # Let's check TrinityBrain.generate_scenario_stream:
            #   with _call_api() as stream:
            #       for text in stream.text_stream:
            #           yield text
            
            # The anthropic stream object has a .text_stream iterator.
            # We need to return an object that has .text_stream
            
            return _AnthropicStreamSimulation(self.provider, full_messages, max_tokens, **kwargs)

class _AnthropicStreamSimulation:
    def __init__(self, provider, messages, max_tokens, **kwargs):
        self.provider = provider
        self.messages = messages
        self.max_tokens = max_tokens
        self.kwargs = kwargs
        self._generator = self._gen()

    @property
    def text_stream(self):
        return self._generator

    def _gen(self):
        # LocalQwenProvider doesn't support streaming in `generate` currently,
        # but `create_chat_completion` might if underlying llama supports it.
        # Our `LocalQwenProvider` wraps `Llama` which supports streaming.
        # Let's try to use create_chat_completion with stream=True
        
        response = self.provider.create_chat_completion(
            messages=self.messages,
            max_tokens=self.max_tokens,
            stream=True,
            **self.kwargs
        )
        
        for chunk in response:
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content")
            if content:
                yield content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class LocalAsJudgeAdapter:
    """
    Adapts LocalQwenProvider to look like a Google GenAI client (Judge).
    Implements: client.generate_content(...)
    """
    def __init__(self, provider: LocalQwenProvider):
        self.provider = provider

    def generate_content(self, prompt: str) -> Any:
        """
        Simulate Google's generate_content API.
        """
        # Google uses a single prompt string. We wrap it in user message.
        response_text = self.provider.generate(prompt)
        
        # Return an object with .text attribute
        return type("GenAIResponse", (), {"text": response_text})


class LocalAsSimulatorAdapter:
    """
    Adapts LocalQwenProvider to look like an OpenAI client (Simulator).
    Already implemented as LocalLLMAdapter in local_llm.py, but simplified here.
    """
    def __init__(self, provider: LocalQwenProvider):
        self.provider = provider
        self.chat = self.Chat(provider)

    class Chat:
        def __init__(self, provider):
            self.completions = self.Completions(provider)

        class Completions:
            def __init__(self, provider):
                self.provider = provider

            def create(self, messages: List[Dict[str, str]], **kwargs) -> Any:
                response = self.provider.create_chat_completion(messages=messages, **kwargs)
                if kwargs.get("stream"):
                    return (_DictToObj(chunk) for chunk in response)
                return _DictToObj(response)


# ==== Fallback Adapters ====

class WriterFallbackAdapter:
    """
    Wraps a primary Writer client and a fallback Writer client.
    """
    def __init__(self, primary: Any, fallback: Any):
        self.primary = primary
        self.fallback = fallback
        self.messages = self.FallbackMessages(primary, fallback)

    class FallbackMessages:
        def __init__(self, primary, fallback):
            self.primary = primary
            self.fallback = fallback

        def stream(self, *args, **kwargs):
            try:
                return self.primary.messages.stream(*args, **kwargs)
            except Exception as e:
                logger.warning(f"⚠️ Primary Writer failed: {e}. Switching to Fallback.")
                return self.fallback.messages.stream(*args, **kwargs)


class JudgeFallbackAdapter:
    """
    Wraps a primary Judge client and a fallback Judge client.
    """
    def __init__(self, primary: Any, fallback: Any):
        self.primary = primary
        self.fallback = fallback

    def generate_content(self, prompt: str) -> Any:
        try:
            return self.primary.generate_content(prompt)
        except Exception as e:
            logger.warning(f"⚠️ Primary Judge failed: {e}. Switching to Fallback.")
            return self.fallback.generate_content(prompt)


class SimulatorFallbackAdapter:
    """
    Wraps a primary Simulator client and a fallback Simulator client.
    """
    def __init__(self, primary: Any, fallback: Any):
        self.primary = primary
        self.fallback = fallback
        self.chat = self.FallbackChat(primary, fallback)

    class FallbackChat:
        def __init__(self, primary, fallback):
            self.primary = primary
            self.fallback = fallback
            self.completions = self.FallbackCompletions(primary, fallback)

        class FallbackCompletions:
            def __init__(self, primary, fallback):
                self.primary = primary
                self.fallback = fallback

            def create(self, *args, **kwargs):
                try:
                    return self.primary.chat.completions.create(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"⚠️ Primary Simulator failed: {e}. Switching to Fallback.")
                    return self.fallback.chat.completions.create(*args, **kwargs)

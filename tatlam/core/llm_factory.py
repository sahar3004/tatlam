"""
tatlam/core/llm_factory.py - LLM Client Factory with Dependency Injection Support

This module provides factory functions for creating AI clients used in the Trinity architecture.
It supports both production use (real clients) and testing (mock injection).

Trinity Architecture:
- Writer: Claude (Anthropic) - Generates scenarios
- Judge: Gemini (Google) - Audits and evaluates
- Simulator: Gemini Flash (Google) - Chat simulations

Usage:
    # Production - creates real clients
    writer = create_writer_client()
    judge = create_judge_client()
    simulator = create_simulator_client()

    # Testing - inject mocks
    brain = TrinityBrain(
        writer_client=mock_anthropic,
        judge_client=mock_genai,
        simulator_client=mock_openai,
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from tatlam.settings import ConfigurationError, get_settings

if TYPE_CHECKING:
    import anthropic
    import google.generativeai as genai
    from openai import OpenAI

logger = logging.getLogger(__name__)


# ==== Protocol Definitions for Type Safety ====


@runtime_checkable
class WriterClientProtocol(Protocol):
    """Protocol for Writer (Anthropic-like) clients."""

    @property
    def messages(self) -> Any:
        """Access to messages API."""
        ...


@runtime_checkable
class JudgeClientProtocol(Protocol):
    """Protocol for Judge (Gemini-like) clients."""

    def generate_content(self, prompt: str) -> Any:
        """Generate content from prompt."""
        ...


@runtime_checkable
class SimulatorClientProtocol(Protocol):
    """Protocol for Simulator (Gemini-like) clients."""

    def generate_content(self, prompt: str, **kwargs: Any) -> Any:
        """Generate content from prompt with optional streaming."""
        ...


# ==== Client Container ====



class AnthropicJudgeAdapter:
    """
    Adapter to make Anthropic client look like a Google GenerativeModel.
    
    This allows the Judge node (designed for Gemini) to use Claude
    without rewriting the core logic in brain.py.
    """
    
    def __init__(self, client: Any, model_name: str):
        self.client = client
        self.model_name = model_name

    def generate_content(self, prompt: str) -> Any:
        """
        Mimic Google's generate_content using Anthropic's messages API.
        
        Args:
            prompt: The full prompt string (system + user)
            
        Returns:
            Object with .text attribute, matching Google's response object
        """
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text if response.content else ""
        except Exception as e:
            raise e

        # Return object with .text attribute
        class Response:
            def __init__(self, text: str):
                self.text = text
                
        return Response(content)


@dataclass
class TrinityClients:
    """Container for all Trinity AI clients."""

    writer: WriterClientProtocol | None = None
    judge: JudgeClientProtocol | None = None
    simulator: SimulatorClientProtocol | None = None

    def has_writer(self) -> bool:
        """Check if writer client is available."""
        return self.writer is not None

    def has_judge(self) -> bool:
        """Check if judge client is available."""
        return self.judge is not None

    def has_simulator(self) -> bool:
        """Check if simulator client is available."""
        return self.simulator is not None


# ==== Factory Functions ====


def create_writer_client(api_key: str | None = None) -> "anthropic.Anthropic | None":
    """
    Create an Anthropic client for the Writer role.

    Args:
        api_key: Optional API key override. If not provided, uses settings.

    Returns:
        Anthropic client or None if not configured.

    Raises:
        ConfigurationError: If api_key is explicitly passed but empty.
    """
    import anthropic

    settings = get_settings()
    key = api_key if api_key is not None else settings.ANTHROPIC_API_KEY

    if not key:
        logger.warning("ANTHROPIC_API_KEY not set. Writer (Claude) will be unavailable.")
        return None

    try:
        client = anthropic.Anthropic(api_key=key)
        logger.debug("Anthropic client initialized successfully")
        return client
    except Exception as e:
        logger.error("Failed to initialize Anthropic client: %s", e)
        raise ConfigurationError(f"Failed to initialize Anthropic client: {e}") from e


def create_judge_client(api_key: str | None = None) -> "genai.GenerativeModel | None":
    """
    Create a Google Generative AI client for the Judge role.

    Args:
        api_key: Optional API key override. If not provided, uses settings.

    Returns:
        GenerativeModel or None if not configured.

    Raises:
        ConfigurationError: If initialization fails with a valid key.
    """
    import google.generativeai as genai

    settings = get_settings()
    
    # Check if we should use Anthropic instead
    if settings.JUDGE_MODEL_PROVIDER == "anthropic":
        logger.debug("Judge configured to use Anthropic adapter")
        try:
            anthropic_client = create_writer_client(api_key=settings.ANTHROPIC_API_KEY)
            if anthropic_client:
                return AnthropicJudgeAdapter(anthropic_client, settings.JUDGE_MODEL_NAME) # type: ignore
        except Exception as e:
             logger.warning("Failed to create Anthropic adapter for Judge: %s. Falling back to Google.", e)

    # Fallback/Default to Google
    key = api_key if api_key is not None else settings.GOOGLE_API_KEY

    if not key:
        logger.warning("GOOGLE_API_KEY not set. Judge (Gemini) will be unavailable.")
        return None

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(settings.JUDGE_MODEL_NAME)
        logger.debug("Google GenAI client initialized successfully with model: %s",
                     settings.JUDGE_MODEL_NAME)
        return model
    except Exception as e:
        logger.error("Failed to initialize Google client: %s", e)
        raise ConfigurationError(f"Failed to initialize Google client: {e}") from e


def create_simulator_client(
    api_key: str | None = None,
) -> "genai.GenerativeModel | None":
    """
    Create a Google Generative AI client for the Simulator role (Gemini Flash).

    Args:
        api_key: Optional API key override. If not provided, uses settings.

    Returns:
        GenerativeModel or None if not configured.

    Raises:
        ConfigurationError: If initialization fails with a valid key.
    """
    import google.generativeai as genai

    settings = get_settings()
    key = api_key if api_key is not None else settings.GOOGLE_API_KEY

    if not key:
        logger.warning("GOOGLE_API_KEY not set. Simulator (Gemini Flash) will be unavailable.")
        return None

    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(settings.SIMULATOR_MODEL_NAME)
        logger.debug("Gemini Simulator client initialized with model: %s",
                     settings.SIMULATOR_MODEL_NAME)
        return model
    except Exception as e:
        logger.error("Failed to initialize Gemini Simulator client: %s", e)
        raise ConfigurationError(f"Failed to initialize Gemini Simulator client: {e}") from e


def create_cloud_client(
    base_url: str | None = None,
    api_key: str | None = None,
) -> "OpenAI | None":
    """
    Create an OpenAI client for cloud API (embeddings, batch processing).

    Args:
        base_url: Optional base URL override. If not provided, uses settings.
        api_key: Optional API key override. If not provided, uses settings.

    Returns:
        OpenAI client or None if not configured.
    """
    from openai import OpenAI

    settings = get_settings()
    url = base_url if base_url is not None else settings.OPENAI_BASE_URL
    key = api_key if api_key is not None else settings.OPENAI_API_KEY

    if not key:
        logger.warning("OPENAI_API_KEY not set. Cloud client will be unavailable.")
        return None

    try:
        client = OpenAI(base_url=url, api_key=key)
        logger.debug("OpenAI cloud client initialized at: %s", url)
        return client
    except Exception as e:
        logger.error("Failed to initialize OpenAI cloud client: %s", e)
        raise ConfigurationError(f"Failed to initialize OpenAI cloud client: {e}") from e


def create_all_clients(
    *,
    writer_key: str | None = None,
    judge_key: str | None = None,
    simulator_key: str | None = None,
    fail_on_missing: bool = False,
) -> TrinityClients:
    """
    Create all Trinity clients in one call.

    This is the recommended way to initialize all clients for production use.

    Args:
        writer_key: Optional Anthropic API key override.
        judge_key: Optional Google API key override for Judge.
        simulator_key: Optional Google API key override for Simulator.
        fail_on_missing: If True, raise ConfigurationError when any client fails.

    Returns:
        TrinityClients container with available clients.

    Raises:
        ConfigurationError: If fail_on_missing=True and any client initialization fails.
    """
    clients = TrinityClients()
    errors: list[str] = []

    # Writer (Anthropic)
    try:
        clients.writer = create_writer_client(writer_key)
    except ConfigurationError as e:
        errors.append(f"Writer: {e}")
        if fail_on_missing:
            raise

    # Judge (Google Gemini)
    try:
        clients.judge = create_judge_client(judge_key)
    except ConfigurationError as e:
        errors.append(f"Judge: {e}")
        if fail_on_missing:
            raise

    # Simulator (Google Gemini Flash)
    try:
        clients.simulator = create_simulator_client(simulator_key)
    except ConfigurationError as e:
        errors.append(f"Simulator: {e}")
        if fail_on_missing:
            raise

    if errors:
        logger.warning("Some clients failed to initialize: %s", "; ".join(errors))

    return clients


# ==== Legacy Compatibility Functions ====
# These match the interface from config.py


def client_local() -> "OpenAI":
    """
    Return an OpenAI client configured for the local LLM server.

    Legacy compatibility function. Prefer create_simulator_client() for new code.

    Raises:
        ConfigurationError: If client initialization fails.
    """
    client = create_simulator_client()
    if client is None:
        raise ConfigurationError("Failed to create local client")
    return client


def client_cloud() -> "OpenAI":
    """
    Return an OpenAI client configured for the cloud API.

    Legacy compatibility function. Prefer create_cloud_client() for new code.

    Raises:
        ConfigurationError: If client initialization fails or OPENAI_API_KEY is missing.
    """
    client = create_cloud_client()
    if client is None:
        raise ConfigurationError(
            "Failed to create cloud client. Ensure OPENAI_API_KEY is set."
        )
    return client


# ==== LLM Router with Gemini Fallback (Phase 2 - Resilience) ====


class LLMRouter:
    """Resilient LLM router with automatic Gemini fallback.

    Phase 2 Addition: Provides automatic fallback from primary LLM
    (local or Anthropic) to Google Gemini when the primary is unavailable.

    Usage:
        router = LLMRouter()
        response = router.chat_complete(
            messages=[{"role": "user", "content": "Hello"}],
            model="local"  # or "anthropic"
        )
    """

    def __init__(self):
        """Initialize router with all available clients."""
        self.local_client = None
        self.anthropic_client = None
        self.gemini_client = None

        # Try to initialize all clients
        try:
            self.local_client = create_simulator_client()
        except (ConfigurationError, Exception) as e:
            logger.debug("Local LLM not available: %s", e)

        try:
            self.anthropic_client = create_writer_client()
        except (ConfigurationError, Exception) as e:
            logger.debug("Anthropic not available: %s", e)

        try:
            self.gemini_client = create_judge_client()
        except (ConfigurationError, Exception) as e:
            logger.debug("Gemini not available: %s", e)

        if not any([self.local_client, self.anthropic_client, self.gemini_client]):
            logger.warning("LLMRouter: No LLM providers available!")

    def chat_complete(
        self,
        messages: list[dict[str, str]],
        model: str = "local",
        **kwargs: Any,
    ) -> Any:
        """
        Execute chat completion with automatic Gemini fallback.

        Args:
            messages: Chat messages in OpenAI format
            model: Primary model to try ("local", "anthropic", "gemini")
            **kwargs: Additional parameters for the API call

        Returns:
            API response from primary or fallback provider

        Raises:
            ConfigurationError: If all providers fail
        """
        # Try primary provider
        primary_error = None
        try:
            if model == "local" and self.local_client:
                return self.local_client.chat.completions.create(
                    messages=messages, **kwargs
                )
            elif model == "anthropic" and self.anthropic_client:
                # Convert to Anthropic format
                system_msg = next(
                    (m["content"] for m in messages if m["role"] == "system"), None
                )
                user_messages = [m for m in messages if m["role"] != "system"]
                return self.anthropic_client.messages.create(
                    model=kwargs.get("model", "claude-sonnet-4-5-20250929"),
                    max_tokens=kwargs.get("max_tokens", 4096),
                    system=system_msg or "",
                    messages=user_messages,
                )
        except Exception as e:
            primary_error = e
            logger.warning(
                "Primary LLM (%s) unreachable: %s. Switching to Gemini fallback.",
                model,
                e,
            )

        # Fallback to Gemini
        if self.gemini_client:
            try:
                logger.info("🔄 Routing to Gemini fallback")
                # Convert messages to Gemini format (concatenate with role prefixes)
                prompt = "\n\n".join(
                    f"{m['role'].upper()}: {m['content']}" for m in messages
                )
                response = self.gemini_client.generate_content(prompt)
                return response
            except Exception as e:
                logger.error("Gemini fallback also failed: %s", e)
                raise ConfigurationError(
                    f"All LLM providers failed. Primary: {primary_error}, Fallback: {e}"
                ) from e

        # No fallback available
        raise ConfigurationError(
            f"Primary LLM ({model}) failed and Gemini fallback not configured. "
            f"Error: {primary_error}"
        )


__all__ = [
    # Protocols
    "WriterClientProtocol",
    "JudgeClientProtocol",
    "SimulatorClientProtocol",
    # Container
    "TrinityClients",
    # Factory functions
    "create_writer_client",
    "create_judge_client",
    "create_simulator_client",
    "create_cloud_client",
    "create_all_clients",
    # Legacy compatibility
    "client_local",
    "client_cloud",
    # Router (Phase 2)
    "LLMRouter",
    # Exceptions
    "ConfigurationError",
]

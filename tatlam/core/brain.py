"""
tatlam/core/brain.py - Trinity Brain: AI-Powered Scenario Engine

The Trinity Brain coordinates three AI models for scenario generation and simulation:
- Writer (Claude): Generates scenarios with streaming
- Judge (Gemini): Audits and evaluates scenarios
- Simulator (Local Llama): Handles chat simulations with streaming

This module uses dependency injection for AI clients, making it testable
and configurable. It includes resilience features via tenacity for retry logic.

Usage:
    # Production (auto-initializes clients)
    brain = TrinityBrain()

    # Testing (inject mocks)
    brain = TrinityBrain(
        writer_client=mock_anthropic,
        judge_client=mock_genai,
        simulator_client=mock_openai,
        auto_initialize=False,
    )
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Generator

from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from tatlam.core.doctrine import get_system_prompt
from tatlam.core.llm_factory import (
    JudgeClientProtocol,
    SimulatorClientProtocol,
    WriterClientProtocol,
    create_judge_client,
    create_simulator_client,
    create_writer_client,
)
from tatlam.core.prompts import (
    PromptValidationError,
    get_prompt_manager,
)
from tatlam.settings import ConfigurationError, get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ==== Custom Exceptions ====


class WriterUnavailableError(RuntimeError):
    """Raised when the Writer (Claude) client is not available."""
    pass


class JudgeUnavailableError(RuntimeError):
    """Raised when the Judge (Gemini) client is not available."""
    pass


class SimulatorUnavailableError(RuntimeError):
    """Raised when the Simulator (Local LLM) client is not available or offline."""
    pass


class APICallError(RuntimeError):
    """Raised when an API call fails after all retries."""
    pass


# ==== Retry Configuration ====

# Retryable exceptions - network/rate limit issues
_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
)

# Standard retry strategy: exponential backoff with jitter
_RETRY_STRATEGY = {
    "wait": wait_random_exponential(min=1, max=60),
    "stop": stop_after_attempt(3),
    "retry": retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    "reraise": True,
}


def _is_retryable_anthropic_error(exc: Exception) -> bool:
    """Check if an Anthropic exception should be retried."""
    # Import here to avoid hard dependency
    try:
        from anthropic import (
            APIConnectionError,
            APIStatusError,
            RateLimitError,
        )
        # Retry on rate limits and connection errors
        if isinstance(exc, (RateLimitError, APIConnectionError)):
            return True
        # Retry on 5xx server errors
        if isinstance(exc, APIStatusError) and exc.status_code >= 500:
            return True
    except ImportError:
        pass
    return False


def _is_retryable_openai_error(exc: Exception) -> bool:
    """Check if an OpenAI exception should be retried."""
    try:
        from openai import (
            APIConnectionError,
            APIStatusError,
            RateLimitError,
        )
        if isinstance(exc, (RateLimitError, APIConnectionError)):
            return True
        if isinstance(exc, APIStatusError) and exc.status_code >= 500:
            return True
    except ImportError:
        pass
    return False


def _is_retryable_google_error(exc: Exception) -> bool:
    """Check if a Google GenAI exception should be retried."""
    # Google's errors are less structured, check by message
    error_str = str(exc).lower()
    return any(kw in error_str for kw in ["rate limit", "quota", "timeout", "503", "500"])


# ==== TrinityBrain Class ====


class TrinityBrain:
    """
    The Trinity Brain: coordinates three AI models for scenario generation and simulation.

    - Writer (Claude): Generates scenarios with streaming
    - Judge (Gemini): Audits and evaluates scenarios
    - Simulator (Local Llama): Handles chat simulations with streaming

    Attributes:
        writer_client: Anthropic client for scenario generation
        judge_client: Google GenerativeModel for scenario auditing
        simulator_client: OpenAI-compatible client for chat simulation
    """

    def __init__(
        self,
        *,
        writer_client: WriterClientProtocol | None = None,
        judge_client: JudgeClientProtocol | None = None,
        simulator_client: SimulatorClientProtocol | None = None,
        auto_initialize: bool = True,
    ) -> None:
        """
        Initialize the Trinity Brain with optional dependency injection.

        Args:
            writer_client: Pre-configured Anthropic client. If None and
                auto_initialize=True, creates one using settings.
            judge_client: Pre-configured Google GenerativeModel. If None and
                auto_initialize=True, creates one using settings.
            simulator_client: Pre-configured OpenAI client. If None and
                auto_initialize=True, creates one using settings.
            auto_initialize: If True (default), automatically initialize missing
                clients from settings. Set to False for testing with explicit mocks.

        Note:
            Missing API keys result in None clients with warnings logged.
            Methods that require unavailable clients will raise specific errors.
        """
        self._settings = get_settings()
        self._prompts = get_prompt_manager()

        # Initialize clients via dependency injection or factory
        self.writer_client: WriterClientProtocol | None = writer_client
        self.judge_client: JudgeClientProtocol | None = judge_client
        self.simulator_client: SimulatorClientProtocol | None = simulator_client

        if auto_initialize:
            self._auto_initialize_clients()

        logger.info(
            "TrinityBrain initialized: writer=%s, judge=%s, simulator=%s",
            "ready" if self.writer_client else "unavailable",
            "ready" if self.judge_client else "unavailable",
            "ready" if self.simulator_client else "unavailable",
        )

    def _auto_initialize_clients(self) -> None:
        """Initialize any missing clients from settings."""
        if self.writer_client is None:
            try:
                self.writer_client = create_writer_client()
            except ConfigurationError:
                logger.warning("Writer client initialization failed")

        if self.judge_client is None:
            try:
                self.judge_client = create_judge_client()
            except ConfigurationError:
                logger.warning("Judge client initialization failed")

        if self.simulator_client is None:
            try:
                self.simulator_client = create_simulator_client()
            except ConfigurationError:
                logger.warning("Simulator client initialization failed")

    def _require_writer(self) -> WriterClientProtocol:
        """Get writer client or raise if unavailable."""
        if self.writer_client is None:
            raise WriterUnavailableError(
                "Writer (Anthropic) client not initialized. Check ANTHROPIC_API_KEY."
            )
        return self.writer_client

    def _require_judge(self) -> JudgeClientProtocol:
        """Get judge client or raise if unavailable."""
        if self.judge_client is None:
            raise JudgeUnavailableError(
                "Judge (Gemini) client not initialized. Check GOOGLE_API_KEY."
            )
        return self.judge_client

    def _require_simulator(self) -> SimulatorClientProtocol:
        """Get simulator client or raise if unavailable."""
        if self.simulator_client is None:
            raise SimulatorUnavailableError(
                "Simulator (Local) client not initialized. Check LOCAL_BASE_URL."
            )
        return self.simulator_client

    def generate_scenario_stream(
        self,
        prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.8,
    ) -> Generator[str, None, None]:
        """
        Generate a scenario using the Writer (Claude) with real-time streaming.

        This method streams text as it's generated, allowing users to see the
        scenario being written in real-time instead of waiting 30+ seconds.

        Args:
            prompt: The prompt describing what scenario to generate
            max_tokens: Maximum tokens to generate (default: 4096)
            temperature: Creativity level 0-1 (default: 0.8)

        Yields:
            Text chunks as they are generated in real-time

        Raises:
            WriterUnavailableError: If writer client is not initialized
            PromptValidationError: If prompt is empty
            APICallError: If API call fails after retries
        """
        # Validate input
        if not prompt or not prompt.strip():
            raise PromptValidationError("Prompt cannot be empty")

        client = self._require_writer()
        system_prompt = get_system_prompt("writer")

        @retry(**_RETRY_STRATEGY)
        def _call_api() -> Any:
            return client.messages.stream(
                model=self._settings.WRITER_MODEL_NAME,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

        try:
            with _call_api() as stream:
                for text in stream.text_stream:
                    yield text
        except RetryError as e:
            logger.error("Writer API call failed after retries: %s", e.last_attempt.exception())
            raise APICallError(f"Writer API call failed: {e.last_attempt.exception()}") from e
        except Exception as e:
            # Check if this is a non-retryable auth error
            error_str = str(e).lower()
            if "authentication" in error_str or "401" in error_str or "invalid api key" in error_str:
                logger.error("Writer authentication failed: %s", e)
                raise APICallError(f"Writer authentication failed: {e}") from e

            # Check if retryable
            if _is_retryable_anthropic_error(e):
                logger.warning("Writer API error (would retry): %s", e)

            logger.error("Failed to generate scenario stream: %s", e)
            raise APICallError(f"Failed to generate scenario stream: {e}") from e

    def audit_scenario(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Audit and evaluate a scenario using the Judge (Gemini).

        Provides professional quality control and validation of security scenarios.

        Args:
            text: The scenario text to audit (in markdown format)
            metadata: Optional metadata dict with title, category, etc.

        Returns:
            Detailed audit results with ratings and recommendations

        Raises:
            JudgeUnavailableError: If judge client is not initialized
            PromptValidationError: If text is empty
            APICallError: If API call fails after retries
        """
        # Validate input
        if not text or not text.strip():
            raise PromptValidationError("Scenario text cannot be empty")

        client = self._require_judge()

        # Use the PromptManager to format the audit prompt securely
        audit_prompt = self._prompts.format_audit_prompt(
            scenario_text=text,
            scenario_metadata=metadata,
            validate_injection=True,  # Enable injection detection
        )

        # Prepend the judge system prompt
        base_prompt = get_system_prompt("judge")
        full_prompt = f"{base_prompt}\n\n{audit_prompt}"

        @retry(**_RETRY_STRATEGY)
        def _call_api() -> str:
            response = client.generate_content(full_prompt)
            return response.text

        try:
            return _call_api()
        except RetryError as e:
            logger.error("Judge API call failed after retries: %s", e.last_attempt.exception())
            raise APICallError(f"Judge API call failed: {e.last_attempt.exception()}") from e
        except Exception as e:
            # Check for auth errors (don't retry)
            error_str = str(e).lower()
            if "authentication" in error_str or "401" in error_str or "api key" in error_str:
                logger.error("Judge authentication failed: %s", e)
                raise APICallError(f"Judge authentication failed: {e}") from e

            # Check if retryable
            if _is_retryable_google_error(e):
                logger.warning("Judge API error (would retry): %s", e)

            logger.error("Failed to audit scenario: %s", e)
            raise APICallError(f"Failed to audit scenario: {e}") from e

    def chat_simulation_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
        timeout: float = 30.0,
    ) -> Generator[str, None, None]:
        """
        Run a chat simulation using the Simulator (Local Llama) with streaming.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Response creativity 0-1 (default: 0.4 for focused responses)
            timeout: Request timeout in seconds (default: 30.0)

        Yields:
            Text chunks as they are generated

        Raises:
            SimulatorUnavailableError: If simulator client is not initialized or offline
            APICallError: If API call fails after retries
        """
        client = self._require_simulator()

        # Inject System Doctrine if missing
        current_messages = list(messages)
        system_msg = {"role": "system", "content": get_system_prompt("simulator")}

        if not current_messages:
            current_messages = [system_msg]
        elif current_messages[0].get("role") != "system":
            current_messages.insert(0, system_msg)
        # else: system prompt already exists, keep user's version

        @retry(**_RETRY_STRATEGY)
        def _call_api() -> Any:
            return client.chat.completions.create(
                model=self._settings.LOCAL_MODEL_NAME,
                messages=current_messages,
                stream=True,
                temperature=temperature,
                top_p=0.9,
                frequency_penalty=0.2,
            )

        try:
            stream = _call_api()
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except RetryError as e:
            logger.error("Simulator API call failed after retries: %s", e.last_attempt.exception())
            # For local simulator, raise specific error for UI to show "offline" badge
            raise SimulatorUnavailableError(
                f"Simulator offline or unreachable: {e.last_attempt.exception()}"
            ) from e
        except ConnectionError as e:
            # Immediate failure for connection errors (no retry)
            logger.error("Simulator connection failed: %s", e)
            raise SimulatorUnavailableError(f"Simulator offline: {e}") from e
        except Exception as e:
            # Check for connection errors that indicate offline server
            error_str = str(e).lower()
            if any(kw in error_str for kw in ["connection refused", "connect error", "no route"]):
                logger.error("Simulator is offline: %s", e)
                raise SimulatorUnavailableError(f"Simulator offline: {e}") from e

            logger.error("Failed to run chat simulation: %s", e)
            raise APICallError(f"Failed to run chat simulation: {e}") from e

    # ==== Non-Streaming Methods (with retry) ====

    def generate_scenario(
        self,
        prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.8,
    ) -> str:
        """
        Generate a scenario using the Writer (Claude) without streaming.

        This is a convenience method that collects all streamed output into a string.
        Use generate_scenario_stream() for real-time output.

        Args:
            prompt: The prompt describing what scenario to generate
            max_tokens: Maximum tokens to generate (default: 4096)
            temperature: Creativity level 0-1 (default: 0.8)

        Returns:
            Complete generated scenario text

        Raises:
            WriterUnavailableError: If writer client is not initialized
            PromptValidationError: If prompt is empty
            APICallError: If API call fails after retries
        """
        chunks: list[str] = []
        for chunk in self.generate_scenario_stream(
            prompt, max_tokens=max_tokens, temperature=temperature
        ):
            chunks.append(chunk)
        return "".join(chunks)

    def chat_simulation(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.4,
    ) -> str:
        """
        Run a chat simulation without streaming.

        This is a convenience method that collects all streamed output into a string.
        Use chat_simulation_stream() for real-time output.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Response creativity 0-1 (default: 0.4)

        Returns:
            Complete simulation response text

        Raises:
            SimulatorUnavailableError: If simulator client is not initialized or offline
            APICallError: If API call fails after retries
        """
        chunks: list[str] = []
        for chunk in self.chat_simulation_stream(messages, temperature=temperature):
            chunks.append(chunk)
        return "".join(chunks)

    # ==== Status Methods ====

    def has_writer(self) -> bool:
        """Check if writer client is available."""
        return self.writer_client is not None

    def has_judge(self) -> bool:
        """Check if judge client is available."""
        return self.judge_client is not None

    def has_simulator(self) -> bool:
        """Check if simulator client is available."""
        return self.simulator_client is not None

    def get_status(self) -> dict[str, bool]:
        """Get status of all clients."""
        return {
            "writer": self.has_writer(),
            "judge": self.has_judge(),
            "simulator": self.has_simulator(),
        }


# ==== Module Exports ====

__all__ = [
    "TrinityBrain",
    "WriterUnavailableError",
    "JudgeUnavailableError",
    "SimulatorUnavailableError",
    "APICallError",
]

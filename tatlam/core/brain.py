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

import json
import logging
from collections.abc import Generator
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypedDict

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
from tatlam.core.schemas import ScenarioDTO
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


# ==== Response Types ====


class BrainResponseMetadata(TypedDict, total=False):
    """Metadata about a brain response."""

    model: str
    tokens_used: int
    finish_reason: str
    duration_ms: float


class BrainResponse(TypedDict):
    """Standardized response structure from TrinityBrain methods.

    This TypedDict enforces a consistent response format across all
    brain operations, making the API predictable and type-safe.

    Fields:
        content: The main response content (generated text, audit result, etc.)
        metadata: Additional information about the response
        timestamp: ISO 8601 timestamp of when the response was generated

    Usage:
        response = brain.think("Generate a security scenario")
        print(response["content"])
        print(response["timestamp"])
    """

    content: str
    metadata: BrainResponseMetadata
    timestamp: str


# ==== JSON Schema for Deterministic Output ====

# JSON Schema for Trinity Doctrine decision/analysis responses
# This schema enforces structured output for tactical decision-making
# with reasoning, council consensus, and doctrinal references
BRAIN_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "role": {
            "type": "string",
            "enum": ["BRAIN", "ADJUDICATOR"],
            "description": "Agent role in the Trinity system",
        },
        "threat_level": {
            "type": "string",
            "enum": [
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                "נמוכה",
                "בינונית",
                "גבוהה",
                "גבוהה מאוד",
            ],
            "description": "Threat level assessment (supports both English and Hebrew)",
        },
        "category": {
            "type": "string",
            "enum": ["SECURITY", "SAFETY", "MEDICAL", "SERVICE"],
            "description": "Incident category classification",
        },
        "identified_vector": {
            "type": "string",
            "enum": ["FOOT", "VEHICLE", "AERIAL", "NONE"],
            "description": "Attack vector if identified",
        },
        "decision": {
            "type": "string",
            "description": "Short description of the recommended action",
        },
        "reasoning": {
            "type": "string",
            "description": "Doctrine-based explanation for the decision",
        },
        "council_consensus": {
            "type": "string",
            "description": "Summary of the 3-expert internal debate (Nimrod Shelo, Eli Navarro, Yarden Levi)",
        },
        "references": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of legal/doctrinal sources used (e.g., authority frameworks, SOPs)",
        },
        "doctrine_violation": {
            "type": "boolean",
            "description": "Whether the scenario involves a doctrine violation",
        },
        "score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Quality/compliance score (0-100)",
        },
        "action_plan": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Step-by-step action plan",
        },
        "content": {
            "type": "string",
            "description": "Full text response if needed (backward compatibility)",
        },
    },
    "required": ["threat_level", "category", "decision", "reasoning"],
    "additionalProperties": True,  # Allow flexibility for additional context
}

# JSON Schema for Scenario Bundle Generation (matches system_prompt_he.txt)
# This is the primary schema for generating training scenarios
SCENARIO_BUNDLE_SCHEMA = {
    "type": "object",
    "properties": {
        "bundle_id": {"type": "string", "description": "Unique identifier for this bundle"},
        "scenarios": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "external_id": {"type": "string"},
                    "title": {"type": "string"},
                    "category": {"type": "string"},
                    "threat_level": {
                        "type": "string",
                        "enum": ["נמוכה", "בינונית", "גבוהה", "גבוהה מאוד"],
                    },
                    "likelihood": {"type": "string", "enum": ["נמוכה", "בינונית", "גבוהה"]},
                    "complexity": {"type": "string", "enum": ["נמוכה", "בינונית", "גבוהה"]},
                    "location": {"type": "string"},
                    "background": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "required_response": {"type": "array", "items": {"type": "string"}},
                    "debrief_points": {"type": "array", "items": {"type": "string"}},
                    "operational_background": {"type": "string"},
                    "media_link": {"type": ["string", "null"]},
                    "mask_usage": {"type": ["string", "null"], "enum": ["כן", "לא", None]},
                    "authority_notes": {"type": "string"},
                    "cctv_usage": {"type": "string"},
                    "comms": {"type": "array", "items": {"type": "string"}},
                    "decision_points": {"type": "array", "items": {"type": "string"}},
                    "escalation_conditions": {"type": "array", "items": {"type": "string"}},
                    "end_state_success": {"type": "string"},
                    "end_state_failure": {"type": "string"},
                    "lessons_learned": {"type": "array", "items": {"type": "string"}},
                    "variations": {"type": "array", "items": {"type": "string"}},
                    "validation": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "json_valid",
                                "unique_title",
                                "no_fabrication",
                                "ethical_balance_ok",
                            ],
                        },
                    },
                },
                "required": [
                    "title",
                    "category",
                    "threat_level",
                    "likelihood",
                    "complexity",
                    "location",
                    "background",
                    "steps",
                    "required_response",
                ],
            },
        },
    },
    "required": ["bundle_id", "scenarios"],
    "additionalProperties": False,
}

# Legacy schema for backward compatibility (simple 3-field structure)
BRAIN_SCHEMA = BRAIN_DECISION_SCHEMA  # Alias for backward compatibility


def create_brain_response(
    content: str,
    *,
    model: str = "",
    tokens_used: int = 0,
    finish_reason: str = "",
    duration_ms: float = 0.0,
) -> BrainResponse:
    """Factory function to create a BrainResponse with current timestamp.

    Parameters
    ----------
    content : str
        The main response content.
    model : str, optional
        The model used to generate the response.
    tokens_used : int, optional
        Number of tokens used in generation.
    finish_reason : str, optional
        Reason for response completion (e.g., "stop", "max_tokens").
    duration_ms : float, optional
        Response generation time in milliseconds.

    Returns
    -------
    BrainResponse
        A fully typed response dictionary.
    """
    metadata: BrainResponseMetadata = {}
    if model:
        metadata["model"] = model
    if tokens_used:
        metadata["tokens_used"] = tokens_used
    if finish_reason:
        metadata["finish_reason"] = finish_reason
    if duration_ms:
        metadata["duration_ms"] = duration_ms

    return BrainResponse(
        content=content,
        metadata=metadata,
        timestamp=datetime.now().isoformat(),
    )


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
        venue: str = "allenby",  # New parameter context
    ) -> Generator[str, None, None]:
        """
        Generate a scenario using the Writer (Claude) with real-time streaming.

        This method streams text as it's generated, allowing users to see the
        scenario being written in real-time instead of waiting 30+ seconds.

        Args:
            prompt: The prompt describing what scenario to generate
            max_tokens: Maximum tokens to generate (default: 4096)
            temperature: Creativity level 0-1 (default: 0.8)
            venue: 'allenby' (underground) or 'jaffa' (surface) context.

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
        system_prompt = get_system_prompt("writer", venue=venue)

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
            if (
                "authentication" in error_str
                or "401" in error_str
                or "invalid api key" in error_str
            ):
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
        Run a chat simulation using the Simulator (Gemini Flash) with streaming.

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

        # Build system prompt
        system_prompt = get_system_prompt("simulator")

        # Convert OpenAI-style messages to Gemini prompt format
        # Gemini doesn't have separate system/user/assistant, so we combine them
        prompt_parts = [system_prompt, "\n\n"]

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                # Skip system messages as we already added the doctrine
                continue
            elif role == "user":
                prompt_parts.append(f"מאבטח: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"יריב/אזרח: {content}\n")

        full_prompt = "".join(prompt_parts)

        # Configure generation settings
        import google.generativeai as genai

        generation_config = genai.GenerationConfig(
            temperature=temperature,
            top_p=0.9,
        )

        @retry(**_RETRY_STRATEGY)
        def _call_api() -> Any:
            return client.generate_content(
                full_prompt,
                generation_config=generation_config,
                stream=True,
            )

        try:
            stream = _call_api()
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except RetryError as e:
            logger.error("Simulator API call failed after retries: %s", e.last_attempt.exception())
            raise SimulatorUnavailableError(
                f"Simulator offline or unreachable: {e.last_attempt.exception()}"
            ) from e
        except Exception as e:
            # Check for common Gemini errors
            error_str = str(e).lower()
            if "api key" in error_str or "401" in error_str:
                logger.error("Simulator authentication failed: %s", e)
                raise SimulatorUnavailableError(f"Simulator auth failed: {e}") from e

            if _is_retryable_google_error(e):
                logger.warning("Simulator API error (would retry): %s", e)

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

    # ==== Graph-Based Batch Generation ====

    def generate_batch(
        self,
        category: str,
        count: int = 5,
        score_threshold: float = 70.0,
    ) -> dict[str, Any]:
        """
        Generate a batch of scenarios using the LangGraph multi-agent system.

        This method replaces the monolithic run_batch.py with a modular,
        observable workflow that includes:
        - Quality loops with repair cycles
        - Early deduplication
        - Doctrine-based scoring

        Args:
            category: The scenario category (e.g., "חפץ חשוד ומטען")
            count: Number of scenarios to generate
            score_threshold: Minimum score to approve (0-100)

        Returns:
            Dict with:
                - bundle_id: Unique bundle identifier
                - scenarios: List of approved scenario dicts
                - metrics: Generation statistics

        Example:
            brain = TrinityBrain()
            result = brain.generate_batch("חפץ חשוד ומטען", count=5)
            print(f"Generated {len(result['scenarios'])} scenarios")
        """
        from tatlam.graph.workflow import run_scenario_generation

        logger.info("TrinityBrain.generate_batch: category=%s, count=%d", category, count)

        final_state = run_scenario_generation(
            category=category,
            target_count=count,
            score_threshold=score_threshold,
        )

        return {
            "bundle_id": final_state.bundle_id,
            "scenarios": [ScenarioDTO(**c.data) for c in final_state.approved_scenarios],
            "metrics": final_state.metrics.to_dict(),
            "errors": final_state.errors,
        }

    async def generate_batch_async(
        self,
        category: str,
        count: int = 5,
        score_threshold: float = 70.0,
    ) -> dict[str, Any]:
        """
        Async version of generate_batch.

        Args:
            category: The scenario category
            count: Number of scenarios to generate
            score_threshold: Minimum score to approve

        Returns:
            Dict with bundle_id, scenarios, metrics, errors
        """
        from tatlam.graph.workflow import run_scenario_generation_async

        logger.info("TrinityBrain.generate_batch_async: category=%s, count=%d", category, count)

        final_state = await run_scenario_generation_async(
            category=category,
            target_count=count,
            score_threshold=score_threshold,
        )

        return {
            "bundle_id": final_state.bundle_id,
            "scenarios": [ScenarioDTO(**c.data) for c in final_state.approved_scenarios],
            "metrics": final_state.metrics.to_dict(),
            "errors": final_state.errors,
        }

    def think(
        self,
        prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.8,
    ) -> BrainResponse:
        """
        Generate a response using the Writer (Claude) and return as BrainResponse.

        This is the primary entry point for AI-powered generation, returning
        a type-safe BrainResponse with content, metadata, and timestamp.

        Args:
            prompt: The prompt describing what to generate
            max_tokens: Maximum tokens to generate (default: 4096)
            temperature: Creativity level 0-1 (default: 0.8)

        Returns:
            BrainResponse with content, metadata, and timestamp

        Raises:
            WriterUnavailableError: If writer client is not initialized
            PromptValidationError: If prompt is empty
            APICallError: If API call fails after retries

        Example:
            response = brain.think("Generate a security scenario")
            print(response["content"])  # The generated text
            print(response["metadata"]["model"])  # Model used
            print(response["timestamp"])  # ISO timestamp
        """
        import time

        start_time = time.perf_counter()

        # Generate the content
        content = self.generate_scenario(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000

        return create_brain_response(
            content=content,
            model=self._settings.WRITER_MODEL_NAME,
            finish_reason="stop",
            duration_ms=duration_ms,
        )

    def think_structured(
        self,
        prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response using the Simulator (Local LLM) with Trinity Doctrine schema.

        This method enforces the BRAIN_DECISION_SCHEMA to eliminate parsing errors caused by flaky
        prompt engineering. It uses response_format to guarantee valid JSON output with threat
        assessment, decision reasoning, and doctrinal references.

        Args:
            prompt: The prompt describing what to analyze or generate
            max_tokens: Maximum tokens to generate (default: 4096)
            temperature: Creativity level 0-1 (default: 0.7 for focused output)

        Returns:
            Dict with required keys:
                - threat_level (str): "נמוכה" | "בינונית" | "גבוהה" | "גבוהה מאוד"
                - category (str): "SECURITY" | "SAFETY" | "MEDICAL" | "SERVICE"
                - decision (str): Short action description
                - reasoning (str): Doctrine-based explanation

            Optional keys:
                - role (str): "BRAIN" | "ADJUDICATOR"
                - identified_vector (str): "FOOT" | "VEHICLE" | "AERIAL" | "NONE"
                - council_consensus (str): Summary of 3-expert debate
                - references (list[str]): Legal/doctrinal sources
                - doctrine_violation (bool): Whether doctrine was violated
                - score (int): Quality score 0-100
                - action_plan (list[str]): Step-by-step actions

        Raises:
            SimulatorUnavailableError: If simulator client is not initialized
            PromptValidationError: If prompt is empty
            APICallError: If API call fails after retries
            json.JSONDecodeError: If response is not valid JSON (should never happen with schema)

        Example:
            result = brain.think_structured("נתח: חפץ חשוד בתחנה")
            print(result["threat_level"])  # "גבוהה"
            print(result["category"])  # "SECURITY"
            print(result["decision"])  # "בידוד ופינוי מיידי"
            print(result["reasoning"])  # "לפי נוהל חפץ חשוד..."
            print(result.get("council_consensus", ""))  # Council debate summary

        Note:
            This method is recommended over think() when you need guaranteed structured output
            with reasoning and doctrinal references. It uses the local LLM (simulator) with
            OpenAI-compatible response_format and BRAIN_DECISION_SCHEMA.
        """
        # Validate input
        if not prompt or not prompt.strip():
            raise PromptValidationError("Prompt cannot be empty")

        client = self._require_simulator()
        system_prompt = get_system_prompt("writer")

        # Enhance the prompt to request JSON output with Trinity Doctrine structure
        enhanced_prompt = f"""{prompt}

החזר את התשובה בפורמט JSON עם השדות הבאים (חובה):
- threat_level: רמת האיום (נמוכה/בינונית/גבוהה/גבוהה מאוד)
- category: קטגוריית האבטחה (SECURITY/SAFETY/MEDICAL/SERVICE)
- decision: תיאור קצר של הפעולה המומלצת
- reasoning: הסבר מבוסס דוקטרינה

שדות נוספים (רצויים):
- role: תפקיד בקואליציה (BRAIN/ADJUDICATOR)
- identified_vector: וקטור התקפה (FOOT/VEHICLE/AERIAL/NONE)
- council_consensus: סיכום הדיון הפנימי של 3 המומחים
- references: רשימת מקורות חוקיים/דוקטרינליים
- action_plan: רשימת צעדים

דוגמה למבנה:
{{
  "role": "BRAIN",
  "threat_level": "גבוהה",
  "category": "SECURITY",
  "identified_vector": "FOOT",
  "decision": "בידוד ופינוי מיידי",
  "reasoning": "לפי נוהל חפץ חשוד - בידוד רדיוס 100 מטר",
  "council_consensus": "נמרוד שלו: סמכות עיכוב מוצדקת; אלי נבארו: מזעור סיכון ציבור; ירדן לוי: הבהרת הוראות",
  "references": ["נוהל חפץ חשוד", "סמכויות עיכוב"],
  "action_plan": ["בידוד", "דיווח למוקד", "פינוי קהל", "המתנה לחבלן"]
}}"""

        @retry(**_RETRY_STRATEGY)
        def _call_api() -> Any:
            return client.chat.completions.create(
                model=self._settings.LOCAL_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": enhanced_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                response_format={"type": "json_object", "schema": BRAIN_SCHEMA},
            )

        try:
            response = _call_api()
            content = response.choices[0].message.content or "{}"

            # Parse JSON response
            result = json.loads(content)

            # Validate required fields per BRAIN_DECISION_SCHEMA
            required_fields = ["threat_level", "category", "decision", "reasoning"]
            missing_fields = [f for f in required_fields if f not in result]

            if missing_fields:
                logger.warning(
                    "Response missing required fields: %s. Got keys: %s",
                    missing_fields,
                    result.keys(),
                )
                # Fallback to ensure required fields exist
                result.setdefault("threat_level", "בינונית")
                result.setdefault("category", "SECURITY")
                result.setdefault("decision", "המתן להנחיות נוספות")
                result.setdefault("reasoning", "מידע לא מספיק להערכה מלאה")

            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response: %s", e)
            raise APICallError(f"Invalid JSON response from simulator: {e}") from e
        except RetryError as e:
            logger.error("Simulator API call failed after retries: %s", e.last_attempt.exception())
            raise APICallError(f"Simulator API call failed: {e.last_attempt.exception()}") from e
        except Exception as e:
            # Check for auth errors (don't retry)
            error_str = str(e).lower()
            if "authentication" in error_str or "401" in error_str:
                logger.error("Simulator authentication failed: %s", e)
                raise APICallError(f"Simulator authentication failed: {e}") from e

            logger.error("Failed to generate structured response: %s", e)
            raise APICallError(f"Failed to generate structured response: {e}") from e


# ==== Standalone Doctrine Validation ====


def validate_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    """
    וולידציה של תרחיש מול הדוקטרינה.

    Args:
        scenario: מילון תרחיש (מ-parse_md_to_scenario או ממקור אחר)

    Returns:
        מילון עם:
        - is_valid: bool
        - doctrine_score: int (0-100)
        - errors: list[str]
        - warnings: list[str]

    Example:
        >>> result = validate_scenario({"title": "...", "category": "...", ...})
        >>> print(f"Score: {result['doctrine_score']}")
    """
    from tatlam.core.validators import validate_scenario_doctrine

    validation_result = validate_scenario_doctrine(scenario)

    return {
        "is_valid": validation_result.is_valid,
        "doctrine_score": validation_result.doctrine_score,
        "errors": validation_result.errors,
        "warnings": validation_result.warnings,
    }


# ==== Module Exports ====

__all__ = [
    # Main class
    "TrinityBrain",
    # Response types
    "BrainResponse",
    "BrainResponseMetadata",
    "create_brain_response",
    # JSON Schemas
    "BRAIN_SCHEMA",  # Alias for BRAIN_DECISION_SCHEMA
    "BRAIN_DECISION_SCHEMA",  # Decision/analysis with reasoning
    "SCENARIO_BUNDLE_SCHEMA",  # Scenario generation (matches system_prompt_he.txt)
    # Validation
    "validate_scenario",
    # Exceptions
    "WriterUnavailableError",
    "JudgeUnavailableError",
    "SimulatorUnavailableError",
    "APICallError",
]

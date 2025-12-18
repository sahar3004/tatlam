import config_trinity
import anthropic
import google.generativeai as genai
from openai import OpenAI
from typing import Generator


class TrinityBrain:
    """
    The Trinity Brain: coordinates three AI models for scenario generation and simulation.
    - Writer (Claude): Generates scenarios with streaming
    - Judge (Gemini): Audits and evaluates scenarios
    - Simulator (Local Llama): Handles chat simulations with streaming
    """

    def __init__(self):
        """Initialize the three AI clients with error handling."""
        # 1. The Writer (Claude via Anthropic)
        self.writer_client = None
        try:
            if config_trinity.ANTHROPIC_API_KEY:
                self.writer_client = anthropic.Anthropic(
                    api_key=config_trinity.ANTHROPIC_API_KEY
                )
            else:
                print("⚠️  Warning: ANTHROPIC_API_KEY not set. Writer (Claude) will be unavailable.")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize Anthropic client: {e}")

        # 2. The Judge (Gemini via Google)
        self.judge_client = None
        try:
            if config_trinity.GOOGLE_API_KEY:
                genai.configure(api_key=config_trinity.GOOGLE_API_KEY)
                self.judge_client = genai.GenerativeModel(config_trinity.JUDGE_MODEL_NAME)
            else:
                print("⚠️  Warning: GOOGLE_API_KEY not set. Judge (Gemini) will be unavailable.")
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize Google client: {e}")

        # 3. The Simulator (Local Llama via OpenAI-compatible API)
        self.simulator_client = None
        try:
            self.simulator_client = OpenAI(
                base_url=config_trinity.LOCAL_BASE_URL,
                api_key=config_trinity.LOCAL_API_KEY
            )
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize local OpenAI client: {e}")

    def generate_scenario_stream(self, prompt: str) -> Generator[str, None, None]:
        """
        Generate a scenario using the Writer (Claude) with streaming.

        Args:
            prompt: The prompt describing what scenario to generate

        Yields:
            Text chunks as they are generated

        Raises:
            RuntimeError: If writer client is not initialized
        """
        if not self.writer_client:
            raise RuntimeError("Writer (Anthropic) client not initialized. Check ANTHROPIC_API_KEY.")

        try:
            with self.writer_client.messages.stream(
                model=config_trinity.WRITER_MODEL_NAME,
                max_tokens=4096,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise RuntimeError(f"Failed to generate scenario: {e}")

    def audit_scenario(self, text: str) -> str:
        """
        Audit and evaluate a scenario using the Judge (Gemini).

        Args:
            text: The scenario text to audit

        Returns:
            Audit results and feedback

        Raises:
            RuntimeError: If judge client is not initialized
        """
        if not self.judge_client:
            raise RuntimeError("Judge (Gemini) client not initialized. Check GOOGLE_API_KEY.")

        try:
            response = self.judge_client.generate_content(
                f"Please audit and evaluate the following scenario:\n\n{text}"
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Failed to audit scenario: {e}")

    def chat_simulation_stream(self, messages: list[dict]) -> Generator[str, None, None]:
        """
        Run a chat simulation using the Simulator (Local Llama) with streaming.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Yields:
            Text chunks as they are generated

        Raises:
            RuntimeError: If simulator client is not initialized
        """
        if not self.simulator_client:
            raise RuntimeError("Simulator (Local) client not initialized. Check LOCAL_BASE_URL.")

        try:
            stream = self.simulator_client.chat.completions.create(
                model=config_trinity.LOCAL_MODEL_NAME,
                messages=messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"Failed to run chat simulation: {e}")

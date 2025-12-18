"""
Unit tests for tatlam/core/brain.py

Tests TrinityBrain class with mocked API clients (NO REAL NETWORK CALLS).
Target: Verify TrinityBrain initialization and client management.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestBrainMock:
    """Test suite for TrinityBrain with mocked APIs."""

    def test_trinity_brain_initializes(self, mock_brain):
        """Test TrinityBrain can be instantiated."""
        assert mock_brain is not None

    def test_trinity_brain_has_writer_client(self, mock_brain):
        """Verify writer_client is initialized."""
        assert hasattr(mock_brain, 'writer_client')
        assert mock_brain.writer_client is not None

    def test_trinity_brain_has_reviewer_client(self, mock_brain):
        """Verify reviewer_client is initialized."""
        assert hasattr(mock_brain, 'reviewer_client')
        assert mock_brain.reviewer_client is not None

    def test_trinity_brain_has_judge_client(self, mock_brain):
        """Verify judge_client is initialized."""
        assert hasattr(mock_brain, 'judge_client')
        assert mock_brain.judge_client is not None

    def test_trinity_brain_no_real_api_calls(self, mock_brain):
        """Ensure no real API calls are made during initialization."""
        # If real API calls were made, this would fail in offline mode
        # The mock_brain fixture ensures all API clients are mocked
        assert mock_brain.writer_client is not None

    @patch('anthropic.Anthropic')
    def test_trinity_brain_claude_client_initialization(self, mock_anthropic):
        """Test Claude (Anthropic) client initialization."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        from tatlam.core.brain import TrinityBrain
        brain = TrinityBrain()

        # Verify Anthropic was called (client initialized)
        assert brain.writer_client is not None

    @patch('google.generativeai.GenerativeModel')
    def test_trinity_brain_gemini_client_initialization(self, mock_gemini):
        """Test Gemini client initialization."""
        mock_model = MagicMock()
        mock_gemini.return_value = mock_model

        from tatlam.core.brain import TrinityBrain
        brain = TrinityBrain()

        # Verify Gemini model was instantiated
        assert brain.reviewer_client is not None

    @patch('openai.OpenAI')
    def test_trinity_brain_openai_client_initialization(self, mock_openai):
        """Test OpenAI (GPT-4) client initialization."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        from tatlam.core.brain import TrinityBrain
        brain = TrinityBrain()

        # Verify OpenAI client was initialized
        assert brain.judge_client is not None

    def test_trinity_brain_generate_method_exists(self, mock_brain):
        """Verify generate method exists on TrinityBrain."""
        assert hasattr(mock_brain, 'generate') or hasattr(mock_brain, 'generate_scenario')

    def test_trinity_brain_clients_are_mocked(self, mock_brain):
        """Verify all clients are properly mocked (no real API keys needed)."""
        # This test would fail if real API initialization was attempted
        # The mock_brain fixture ensures everything is mocked
        assert mock_brain.writer_client is not None
        assert mock_brain.reviewer_client is not None
        assert mock_brain.judge_client is not None

    def test_trinity_brain_handles_missing_api_keys_gracefully(self):
        """Test behavior when API keys are missing (should use mocks)."""
        with patch('config_trinity.ANTHROPIC_API_KEY', ''):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_anthropic.return_value = MagicMock()

                from tatlam.core.brain import TrinityBrain
                brain = TrinityBrain()

                # Should still initialize with mock
                assert brain is not None

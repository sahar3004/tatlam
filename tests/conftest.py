"""
Global pytest fixtures for TATLAM test suite.

This module provides:
- in_memory_db: Isolated SQLite database for integration tests
- mock_brain: Mocked TrinityBrain for unit tests (no real API calls)
"""

import pytest
import sqlite3
import tempfile
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path


@pytest.fixture
def in_memory_db(monkeypatch):
    """
    Provides an isolated in-memory SQLite database for testing.

    - Creates a temporary database
    - Monkeypatches settings.DB_PATH via cache clear
    - Initializes schema via init_db()
    - Yields connection for tests
    - Cleans up automatically
    """
    from tatlam.settings import get_settings

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False)
    temp_db_path = temp_db.name
    temp_db.close()

    # Clear settings cache and monkeypatch environment
    get_settings.cache_clear()
    monkeypatch.setenv('DB_PATH', temp_db_path)

    # Re-fetch settings to pick up new DB_PATH
    settings = get_settings()

    # Provide connection to tests
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row

    yield conn

    # Cleanup
    conn.close()
    Path(temp_db_path).unlink(missing_ok=True)
    get_settings.cache_clear()


@pytest.fixture
def mock_brain():
    """
    Provides a mocked TrinityBrain instance that doesn't make real API calls.

    Returns:
        TrinityBrain with all API clients mocked to return safe responses
    """
    with patch('anthropic.Anthropic') as mock_anthropic, \
         patch('google.generativeai.GenerativeModel') as mock_gemini, \
         patch('openai.OpenAI') as mock_openai:

        # Mock Anthropic (Claude)
        mock_claude_response = MagicMock()
        mock_claude_response.content = [MagicMock(text="Mocked Claude Response")]
        mock_anthropic.return_value.messages.create.return_value = mock_claude_response

        # Mock Gemini
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = "Mocked Gemini Response"
        mock_gemini_instance = mock_gemini.return_value
        mock_gemini_instance.generate_content.return_value = mock_gemini_response

        # Mock OpenAI (GPT-4)
        mock_openai_response = MagicMock()
        mock_openai_response.choices = [MagicMock(message=MagicMock(content="Mocked GPT-4 Response"))]
        mock_openai.return_value.chat.completions.create.return_value = mock_openai_response

        # Import and instantiate TrinityBrain with mocked clients
        from tatlam.core.brain import TrinityBrain
        brain = TrinityBrain()

        yield brain


@pytest.fixture
def sample_scenario_data():
    """
    Provides a valid scenario dictionary for testing.
    """
    return {
        "title": "בדיקת תרחיש לדוגמה",
        "category": "פיננסים",
        "difficulty": "בינוני",
        "bundle": "חבילה 1",
        "steps": [
            {"step": 1, "description": "פתח את האפליקציה"},
            {"step": 2, "description": "בחר אפשרות תשלום"}
        ],
        "expected_behavior": "המשתמש יכול להשלים תשלום",
        "testing_tips": "בדוק טיפול בשגיאות"
    }


@pytest.fixture
def sample_json_schema():
    """
    Provides the expected JSON schema for scenario validation.
    """
    return {
        "type": "object",
        "required": ["title", "category", "difficulty", "steps"],
        "properties": {
            "title": {"type": "string"},
            "category": {"type": "string"},
            "difficulty": {"type": "string"},
            "bundle": {"type": "string"},
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["step", "description"],
                    "properties": {
                        "step": {"type": "number"},
                        "description": {"type": "string"}
                    }
                }
            },
            "expected_behavior": {"type": "string"},
            "testing_tips": {"type": "string"}
        }
    }


# Pytest configuration
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (real API calls, expensive operations)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (database access)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast, isolated)"
    )

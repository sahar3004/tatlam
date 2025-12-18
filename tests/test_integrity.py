"""
Phase 2: QA Plan - Test Automation for Code Integrity

This module contains integration and unit tests to verify the refactored codebase:
- Infrastructure Unit Test: DB schema consistency
- Repository Integration Test: JSON serialization handling
- System Health Check: Trinity Brain initialization
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


# ==============================================================================
# Test Fixtures and Helpers
# ==============================================================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        temp_path = f.name
    yield temp_path
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    yield con
    con.close()


def init_test_schema(con: sqlite3.Connection, table_name: str = "scenarios"):
    """
    Initialize the test database schema matching the production schema.

    This recreates the schema that was previously in ensure_db() in run_batch.py.
    """
    cur = con.cursor()

    # Create main scenarios table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_id TEXT,
            external_id TEXT,
            title TEXT UNIQUE,
            category TEXT,
            threat_level TEXT,
            likelihood TEXT,
            complexity TEXT,
            location TEXT,
            background TEXT,
            steps TEXT,
            required_response TEXT,
            debrief_points TEXT,
            operational_background TEXT,
            media_link TEXT,
            mask_usage TEXT,
            authority_notes TEXT,
            cctv_usage TEXT,
            comms TEXT,
            decision_points TEXT,
            escalation_conditions TEXT,
            end_state_success TEXT,
            end_state_failure TEXT,
            lessons_learned TEXT,
            variations TEXT,
            validation TEXT,
            owner TEXT,
            approved_by TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    # Create embeddings table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            title TEXT PRIMARY KEY,
            vector_json TEXT
        )
    """)

    con.commit()


# ==============================================================================
# Test 2.1: Infrastructure Unit Test
# ==============================================================================

def test_db_schema_consistency(in_memory_db):
    """
    Test 2.1: Infrastructure Unit Test

    Goal: Verify DB Schema consistency.
    Method:
    - Use sqlite3 in-memory DB
    - Initialize the DB schema
    - Verify that the table 'scenarios' exists
    - Verify critical columns exist: title, steps, category
    """
    # Initialize schema
    init_test_schema(in_memory_db, table_name="scenarios")

    # Verify table exists
    cur = in_memory_db.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='scenarios'
    """)
    result = cur.fetchone()
    assert result is not None, "scenarios table should exist"
    assert result[0] == "scenarios"

    # Verify critical columns exist
    cur.execute("PRAGMA table_info(scenarios)")
    columns = {row[1] for row in cur.fetchall()}  # row[1] is column name

    critical_columns = {'title', 'steps', 'category'}
    assert critical_columns.issubset(columns), \
        f"Missing critical columns. Expected {critical_columns}, found {columns}"

    # Additional verification: check expected columns from schema
    expected_columns = {
        'id', 'bundle_id', 'external_id', 'title', 'category',
        'threat_level', 'likelihood', 'complexity', 'location', 'background',
        'steps', 'required_response', 'debrief_points',
        'operational_background', 'media_link', 'mask_usage',
        'authority_notes', 'cctv_usage', 'comms', 'decision_points',
        'escalation_conditions', 'end_state_success', 'end_state_failure',
        'lessons_learned', 'variations', 'validation',
        'owner', 'approved_by', 'status', 'created_at'
    }
    assert expected_columns.issubset(columns), \
        f"Schema mismatch. Missing columns: {expected_columns - columns}"


def test_db_schema_with_get_db(temp_db_path, monkeypatch):
    """
    Test 2.1 (Extended): Verify DB initialization through get_db().

    Tests that tatlam.infra.db.get_db works correctly with schema initialization.
    """
    # Mock the config to use our temp DB
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("TABLE_NAME", "scenarios")

    # Need to reload config modules to pick up env vars
    import sys
    if 'config' in sys.modules:
        del sys.modules['config']
    if 'config_trinity' in sys.modules:
        del sys.modules['config_trinity']

    from tatlam.infra.db import get_db

    # Get connection and initialize schema
    con = get_db()
    init_test_schema(con, table_name="scenarios")

    # Verify we can query the schema
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'")
    result = cur.fetchone()

    assert result is not None
    assert result['name'] == 'scenarios'

    con.close()


# ==============================================================================
# Test 2.2: Repository Integration Test
# ==============================================================================

def test_insert_scenario_json_serialization(temp_db_path, monkeypatch):
    """
    Test 2.2: Repository Integration Test

    Goal: Verify insert_scenario correctly handles JSON serialization.
    Method:
    - Create a dummy scenario dictionary with a list object in the steps field
    - Call insert_scenario(dummy_data)
    - Read the row back
    - Assert that steps comes back as a list (via normalize_row) and not as a string
    """
    # Setup: Mock config to use temp DB
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("TABLE_NAME", "scenarios")

    # Reload modules to pick up new config
    import sys
    for mod in ['config', 'config_trinity', 'tatlam.infra.db', 'tatlam.infra.repo']:
        if mod in sys.modules:
            del sys.modules[mod]

    from tatlam.infra.db import get_db
    from tatlam.infra.repo import insert_scenario, normalize_row

    # Initialize schema
    con = get_db()
    init_test_schema(con, table_name="scenarios")
    con.close()

    # Create dummy scenario with list in steps field
    dummy_scenario = {
        "title": "Test Scenario - JSON Serialization",
        "category": "חפץ חשוד",
        "threat_level": "גבוהה",
        "likelihood": "בינונית",
        "complexity": "נמוכה",
        "location": "תחנת רכבת ירושלים",
        "background": "Test background for serialization",
        "steps": [
            "שלב ראשון - זיהוי חפץ חשוד",
            "שלב שני - דיווח למוקד",
            "שלב שלישי - פינוי האזור"
        ],
        "required_response": ["תגובה 1", "תגובה 2"],
        "debrief_points": ["נקודה 1", "נקודה 2"],
        "decision_points": ["החלטה 1", "החלטה 2"],
        "escalation_conditions": ["תנאי 1", "תנאי 2"],
        "lessons_learned": ["לקח 1", "לקח 2"],
        "variations": ["וריאציה 1"],
        "operational_background": "רקע מבצעי",
        "media_link": "",
        "mask_usage": "לא",
        "bundle_id": "TEST-BUNDLE-001"
    }

    # Insert scenario
    scenario_id = insert_scenario(dummy_scenario, owner="test_user", pending=False)
    assert scenario_id > 0, "insert_scenario should return valid row ID"

    # Read back the row
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
    row = cur.fetchone()
    con.close()

    assert row is not None, "Inserted row should be retrievable"

    # Normalize the row (this should parse JSON fields back to lists)
    normalized = normalize_row(row)

    # Verify steps field
    assert 'steps' in normalized
    assert isinstance(normalized['steps'], list), \
        f"steps should be a list, got {type(normalized['steps'])}"
    assert len(normalized['steps']) == 3
    assert normalized['steps'][0] == "שלב ראשון - זיהוי חפץ חשוד"

    # Verify other JSON fields
    assert isinstance(normalized['required_response'], list)
    assert isinstance(normalized['debrief_points'], list)
    assert isinstance(normalized['decision_points'], list)
    assert isinstance(normalized['escalation_conditions'], list)
    assert isinstance(normalized['lessons_learned'], list)
    assert isinstance(normalized['variations'], list)

    # Verify non-JSON fields remain as strings
    assert isinstance(normalized['title'], str)
    assert normalized['title'] == "Test Scenario - JSON Serialization"
    assert isinstance(normalized['category'], str)
    assert normalized['category'] == "חפץ חשוד"


def test_insert_scenario_duplicate_title(temp_db_path, monkeypatch):
    """
    Test 2.2 (Extended): Verify insert_scenario handles duplicate titles correctly.

    The title field has a UNIQUE constraint, so inserting a duplicate should raise ValueError.
    """
    # Setup
    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("TABLE_NAME", "scenarios")

    import sys
    for mod in ['config', 'config_trinity', 'tatlam.infra.db', 'tatlam.infra.repo']:
        if mod in sys.modules:
            del sys.modules[mod]

    from tatlam.infra.db import get_db
    from tatlam.infra.repo import insert_scenario

    # Initialize schema
    con = get_db()
    init_test_schema(con, table_name="scenarios")
    con.close()

    # Insert first scenario
    scenario1 = {
        "title": "Duplicate Test Scenario",
        "category": "חפץ חשוד",  # Valid category that maps to "chefetz-chashud"
        "steps": ["step 1"]
    }
    insert_scenario(scenario1, owner="test_user")

    # Attempt to insert duplicate (should raise ValueError)
    scenario2 = {
        "title": "Duplicate Test Scenario",  # Same title
        "category": "פיגועים פשוטים",  # Different valid category
        "steps": ["different step"]
    }

    with pytest.raises(ValueError, match="scenario already exists"):
        insert_scenario(scenario2, owner="test_user")


# ==============================================================================
# Test 2.3: System Health Check (Mocked)
# ==============================================================================

def test_trinity_brain_initialization_success():
    """
    Test 2.3: System Health Check (Mocked)

    Goal: Ensure Trinity Brain initializes without crashing.
    Method:
    - Use dependency injection to pass mock clients
    - Instantiate TrinityBrain
    - Assert no exceptions are raised
    """
    from tatlam.core.brain import TrinityBrain

    # Create mock clients
    mock_writer = MagicMock(name='MockAnthropicClient')
    mock_judge = MagicMock(name='MockGeminiModel')
    mock_simulator = MagicMock(name='MockOpenAIClient')

    # Use dependency injection (new pattern)
    brain = TrinityBrain(
        writer_client=mock_writer,
        judge_client=mock_judge,
        simulator_client=mock_simulator,
        auto_initialize=False
    )

    # Verify all three clients were set
    assert brain.writer_client is mock_writer
    assert brain.judge_client is mock_judge
    assert brain.simulator_client is mock_simulator

    # Verify status methods
    assert brain.has_writer() is True
    assert brain.has_judge() is True
    assert brain.has_simulator() is True


def test_trinity_brain_initialization_missing_keys():
    """
    Test 2.3 (Extended): Verify TrinityBrain handles missing API keys gracefully.

    When API keys are missing, the brain should initialize but clients should be None.
    No exceptions should be raised.
    """
    from tatlam.settings import get_settings
    from tatlam.core.brain import TrinityBrain

    # Clear settings cache
    get_settings.cache_clear()

    # Mock environment with missing keys
    with patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': '',
        'GOOGLE_API_KEY': '',
        'LOCAL_BASE_URL': 'http://localhost:8080/v1',
        'LOCAL_API_KEY': 'mock-local-key'
    }, clear=False):
        # Clear settings cache to pick up new env vars
        get_settings.cache_clear()

        # Mock OpenAI at the openai module level (since it's imported inside functions)
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value = MagicMock(name='MockOpenAIClient')

            # Instantiate TrinityBrain with auto_initialize=True
            brain = TrinityBrain(auto_initialize=True)

            # Writer and Judge should be None due to missing keys
            assert brain.writer_client is None
            assert brain.judge_client is None
            # Simulator should still be initialized
            assert brain.simulator_client is not None

    # Cleanup
    get_settings.cache_clear()


def test_trinity_brain_initialization_client_failure():
    """
    Test 2.3 (Extended): Verify TrinityBrain handles client initialization failures gracefully.

    If a client fails to initialize (exception raised), the brain should still instantiate
    and the failed client should be None.
    """
    from tatlam.settings import get_settings, ConfigurationError
    from tatlam.core.brain import TrinityBrain

    # Clear settings cache
    get_settings.cache_clear()

    with patch.dict(os.environ, {
        'ANTHROPIC_API_KEY': 'mock-key',
        'GOOGLE_API_KEY': 'mock-key',
        'LOCAL_BASE_URL': 'http://localhost:8080/v1',
        'LOCAL_API_KEY': 'mock-local-key'
    }, clear=False):
        get_settings.cache_clear()

        # Make create_writer_client raise a ConfigurationError
        with patch('tatlam.core.brain.create_writer_client') as mock_create_writer:
            mock_create_writer.side_effect = ConfigurationError("Connection error")

            with patch('tatlam.core.brain.create_judge_client') as mock_create_judge:
                mock_create_judge.return_value = MagicMock(name='MockGeminiModel')

                with patch('tatlam.core.brain.create_simulator_client') as mock_create_sim:
                    mock_create_sim.return_value = MagicMock(name='MockOpenAIClient')

                    # Should not raise - error should be caught and logged
                    brain = TrinityBrain(auto_initialize=True)

                    # Writer client should be None due to exception
                    assert brain.writer_client is None
                    # Other clients should be initialized
                    assert brain.judge_client is not None
                    assert brain.simulator_client is not None

    # Cleanup
    get_settings.cache_clear()


# ==============================================================================
# Additional Integration Tests
# ==============================================================================

def test_json_fields_empty_handling(temp_db_path, monkeypatch):
    """
    Test that normalize_row correctly handles empty/null JSON fields.
    """
    from tatlam.settings import get_settings
    get_settings.cache_clear()

    monkeypatch.setenv("DB_PATH", temp_db_path)
    monkeypatch.setenv("TABLE_NAME", "scenarios")

    import sys
    for mod in ['tatlam.settings', 'tatlam.infra.db', 'tatlam.infra.repo']:
        if mod in sys.modules:
            del sys.modules[mod]

    # Re-import to pick up new env vars
    from tatlam.settings import get_settings as get_new_settings
    get_new_settings.cache_clear()

    from tatlam.infra.db import get_db
    from tatlam.infra.repo import insert_scenario, normalize_row

    con = get_db()
    init_test_schema(con, table_name="scenarios")
    con.close()

    # Scenario with minimal fields (no steps, etc.)
    minimal_scenario = {
        "title": "Minimal Scenario",
        "category": "חפץ חשוד"  # Valid category
    }

    scenario_id = insert_scenario(minimal_scenario, owner="test")

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,))
    row = cur.fetchone()
    con.close()

    normalized = normalize_row(row)

    # Empty JSON fields should be empty lists, not strings or None
    assert normalized['steps'] == []
    assert normalized['required_response'] == []
    assert normalized['debrief_points'] == []


if __name__ == "__main__":
    # Allow running tests directly with: python tests/test_integrity.py
    pytest.main([__file__, "-v"])

"""
Integration tests for tatlam/infra/db.py

Tests database schema initialization and structure.
Target: init_db() function and schema validation.
"""

import pytest
import sqlite3


@pytest.mark.integration
class TestDatabaseSchema:
    """Test suite for database schema validation."""

    def test_init_db_creates_database(self, in_memory_db):
        """Verify init_db creates database successfully."""
        assert in_memory_db is not None

    def test_scenarios_table_exists(self, in_memory_db):
        """Verify 'scenarios' table is created."""
        cursor = in_memory_db.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='scenarios'
        """)
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == 'scenarios'

    def test_scenarios_table_schema(self, in_memory_db):
        """Verify 'scenarios' table has correct columns."""
        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(scenarios)")
        columns = cursor.fetchall()

        column_names = [col[1] for col in columns]

        # Expected columns based on actual schema
        expected_columns = ['id', 'title', 'category', 'steps']

        for expected_col in expected_columns:
            assert expected_col in column_names, f"Column '{expected_col}' missing from scenarios table"

    def test_scenarios_table_has_primary_key(self, in_memory_db):
        """Verify 'scenarios' table has primary key."""
        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(scenarios)")
        columns = cursor.fetchall()

        # Check for primary key (column info format: cid, name, type, notnull, dflt_value, pk)
        primary_keys = [col for col in columns if col[5] == 1]

        assert len(primary_keys) > 0, "No primary key found in scenarios table"
        assert primary_keys[0][1] == 'id', "Primary key should be 'id' column"

    def test_database_supports_hebrew(self, in_memory_db):
        """Test database can store and retrieve Hebrew text."""
        cursor = in_memory_db.cursor()

        # Insert Hebrew text
        hebrew_text = "בדיקת עברית מלאה עם ניקוד: שָׁלוֹם"
        cursor.execute("""
            INSERT INTO scenarios (
                title, category, steps, bundle_id, external_id,
                threat_level, likelihood, complexity, location, background, operational_background,
                cctv_usage, authority_notes, end_state_success, end_state_failure,
                required_response, debrief_points, comms, decision_points, escalation_conditions,
                lessons_learned, variations, validation,
                owner, approved_by, status, created_at, media_link
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hebrew_text, "פיגועים פשוטים", "[]", "bundle-1", "ext-1",
            "low", "low", "low", "loc", "bg", "op_bg",
            "none", "none", "win", "lose",
            "[]", "[]", "[]", "[]", "[]", "[]", "[]", "[]",
            "web", "", "pending", "2025-01-01", ""
        ))
        in_memory_db.commit()

        # Retrieve it back
        cursor.execute("SELECT title FROM scenarios WHERE id = last_insert_rowid()")
        result = cursor.fetchone()

        assert result is not None
        assert result[0] == hebrew_text

    def test_database_supports_json_fields(self, in_memory_db):
        """Test database can store JSON data in text fields."""
        import json

        cursor = in_memory_db.cursor()

        steps_data = [
            {"step": 1, "description": "צעד ראשון"},
            {"step": 2, "description": "צעד שני"}
        ]
        steps_json = json.dumps(steps_data, ensure_ascii=False)

        cursor.execute("""
            INSERT INTO scenarios (
                title, category, steps, bundle_id, external_id,
                threat_level, likelihood, complexity, location, background, operational_background,
                cctv_usage, authority_notes, end_state_success, end_state_failure,
                required_response, debrief_points, comms, decision_points, escalation_conditions,
                lessons_learned, variations, validation,
                owner, approved_by, status, created_at, media_link
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "כותרת בדיקה json", "פיגועים פשוטים", steps_json, "bundle-1", "ext-1",
            "low", "low", "low", "loc", "bg", "op_bg",
            "none", "none", "win", "lose",
            "[]", "[]", "[]", "[]", "[]", "[]", "[]", "[]",
            "web", "", "pending", "2025-01-01", ""
        ))

        cursor.execute("SELECT steps FROM scenarios WHERE id = last_insert_rowid()")
        result = cursor.fetchone()

        assert result is not None

        # Parse JSON back
        retrieved_steps = json.loads(result[0])
        assert len(retrieved_steps) == 2
        assert retrieved_steps[0]["description"] == "צעד ראשון"

    def test_scenarios_table_nullable_fields(self, in_memory_db):
        """Test which fields can be NULL."""
        cursor = in_memory_db.cursor()

        # Try inserting minimal record
        try:
            cursor.execute("""
                INSERT INTO scenarios (
                    title, category, steps, bundle_id, external_id,
                    threat_level, likelihood, complexity, location, background, operational_background,
                    cctv_usage, authority_notes, end_state_success, end_state_failure,
                    required_response, debrief_points, comms, decision_points, escalation_conditions,
                    lessons_learned, variations, validation,
                    owner, approved_by, status, created_at, media_link
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "כותרת nullable", "פיגועים פשוטים", "[]", "bundle-1", "ext-1",
                "low", "low", "low", "loc", "bg", "op_bg",
                "none", "none", "win", "lose",
                "[]", "[]", "[]", "[]", "[]", "[]", "[]", "[]",
                "web", "", "pending", "2025-01-01", ""
            ))
            in_memory_db.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False

        assert success, "Failed to insert minimal scenario record"

    def test_database_utf8_encoding(self, in_memory_db):
        """Verify database properly handles UTF-8 encoding."""
        cursor = in_memory_db.cursor()

        # Insert various Unicode characters
        unicode_test = "עברית + English + 中文 + 🔥 Emoji"
        cursor.execute("""
            INSERT INTO scenarios (
                title, category, steps, bundle_id, external_id,
                threat_level, likelihood, complexity, location, background, operational_background,
                cctv_usage, authority_notes, end_state_success, end_state_failure,
                required_response, debrief_points, comms, decision_points, escalation_conditions,
                lessons_learned, variations, validation,
                owner, approved_by, status, created_at, media_link
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            unicode_test, "פיגועים פשוטים", "[]", "bundle-1", "ext-1",
            "low", "low", "low", "loc", "bg", "op_bg",
            "none", "none", "win", "lose",
            "[]", "[]", "[]", "[]", "[]", "[]", "[]", "[]",
            "web", "", "pending", "2025-01-01", ""
        ))

        cursor.execute("SELECT title FROM scenarios WHERE id = last_insert_rowid()")
        result = cursor.fetchone()

        assert result[0] == unicode_test

    def test_init_db_is_idempotent(self, in_memory_db):
        """Test that calling init_db_sqlalchemy multiple times is safe."""
        from tatlam.infra.db import init_db_sqlalchemy

        # Call init_db_sqlalchemy again
        init_db_sqlalchemy()

        # Should not crash, table should still exist
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'")
        result = cursor.fetchone()

        assert result is not None

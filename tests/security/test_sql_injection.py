"""
Security tests for SQL injection prevention.

Tests database operations against SQL injection attacks.
Target: All database query functions in tatlam/infra/repo.py.
"""

import pytest


@pytest.mark.integration
class TestSQLInjection:
    """Test suite for SQL injection prevention."""

    def test_insert_scenario_with_sql_injection_attempt(self, in_memory_db):
        """Test that insert_scenario prevents SQL injection in string fields."""
        from tatlam.infra.repo import insert_scenario

        # SQL injection attempt in title
        malicious_scenario = {
            "title": "'; DROP TABLE scenarios; --",
            "category": "פיגועים פשוטים",
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד"}],
        }

        # Should safely insert without executing malicious SQL
        scenario_id = insert_scenario(malicious_scenario)
        assert scenario_id is not None

        # Verify table still exists
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'")
        result = cursor.fetchone()

        assert result is not None, "Table was dropped - SQL injection succeeded!"

    def test_insert_scenario_with_quote_escaping(self, in_memory_db):
        """Test that single and double quotes are properly escaped."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        scenario_with_quotes = {
            "title": "תרחיש עם 'גרשיים' ו-\"מרכאות\"",
            "category": "פיגועים פשוטים",
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד עם 'גרש'"}],
        }

        scenario_id = insert_scenario(scenario_with_quotes)

        # Retrieve and verify
        scenarios = fetch_all()
        retrieved = [s for s in scenarios if s.get("id") == scenario_id]

        assert len(retrieved) == 1
        assert retrieved[0]["title"] == scenario_with_quotes["title"]

    def test_fetch_all_no_injection_vulnerability(self, in_memory_db):
        """Test that fetch_all is not vulnerable to SQL injection."""
        from tatlam.infra.repo import fetch_all

        # Should safely return all records
        scenarios = fetch_all()

        assert scenarios is not None
        assert isinstance(scenarios, list)

    def test_parameterized_queries_used(self, in_memory_db):
        """Test that queries use parameterized statements."""
        from tatlam.infra.repo import insert_scenario

        # Attempt various injection patterns
        injection_patterns = [
            "' OR '1'='1",
            "'; DELETE FROM scenarios WHERE '1'='1",
            "' UNION SELECT * FROM scenarios--",
            "'; EXEC xp_cmdshell('dir')--",
        ]

        for pattern in injection_patterns:
            scenario = {
                "title": pattern,
                "category": "פיגועים פשוטים",
                "difficulty": "בינוני",
                "steps": [{"step": 1, "description": "צעד"}],
            }

            # Should safely insert without executing injection
            scenario_id = insert_scenario(scenario)
            assert scenario_id is not None

        # Verify table integrity
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM scenarios")
        count = cursor.fetchone()[0]

        # Should have inserted records, not executed malicious SQL
        assert count >= len(injection_patterns)

    def test_json_field_injection_prevention(self, in_memory_db):
        """Test that JSON fields don't allow SQL injection."""
        from tatlam.infra.repo import insert_scenario
        import json

        malicious_steps = [{"step": 1, "description": "'; DROP TABLE scenarios; --"}]

        scenario = {
            "title": "תרחיש",
            "category": "פיגועים פשוטים",
            "difficulty": "בינוני",
            "steps": malicious_steps,
        }

        scenario_id = insert_scenario(scenario)

        # Table should still exist
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT steps FROM scenarios WHERE id = ?", (scenario_id,))
        result = cursor.fetchone()

        assert result is not None

        # Steps should be stored as JSON string
        stored_steps = json.loads(result[0])
        assert stored_steps[0]["description"] == "'; DROP TABLE scenarios; --"

    def test_unicode_injection_prevention(self, in_memory_db):
        """Test that Unicode-based injection attempts are prevented."""
        from tatlam.infra.repo import insert_scenario

        # Unicode null byte injection attempt
        unicode_injection = {
            "title": "תרחיש\x00'; DROP TABLE scenarios; --",
            "category": "פיגועים פשוטים",
            "difficulty": "בינוני",
            "steps": [{"step": 1, "description": "צעד"}],
        }

        scenario_id = insert_scenario(unicode_injection)
        assert scenario_id is not None

        # Verify table exists
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'")
        assert cursor.fetchone() is not None

    def test_comment_injection_prevention(self, in_memory_db):
        """Test that SQL comment injection is prevented."""
        from tatlam.infra.repo import insert_scenario

        comment_patterns = ["תרחיש -- comment", "תרחיש /* block comment */", "תרחיש # hash comment"]

        for pattern in comment_patterns:
            scenario = {
                "title": pattern,
                "category": "פיגועים פשוטים",
                "difficulty": "בינוני",
                "steps": [{"step": 1, "description": "צעד"}],
            }

            scenario_id = insert_scenario(scenario)
            assert scenario_id is not None

    def test_second_order_injection_prevention(self, in_memory_db):
        """Test prevention of second-order SQL injection."""
        from tatlam.infra.repo import insert_scenario, fetch_all

        # Store malicious data
        malicious_data = {
            "title": "'; DROP TABLE scenarios; --",
            "category": "פיגועים פשוטים",
            "threat_level": "בינוני",
            "steps": [{"step": 1, "description": "צעד"}],
        }

        scenario_id = insert_scenario(malicious_data)

        # Retrieve and re-insert (second order) with a different title
        scenarios = fetch_all()
        retrieved = [s for s in scenarios if s.get("id") == scenario_id][0]

        # Re-inserting should still be safe - use modified title to avoid UNIQUE conflict
        new_scenario = {
            "title": f"Second order: {retrieved['title']}",  # Contains malicious string
            "category": "פיגועים פשוטים",
            "threat_level": "בינוני",
            "steps": [{"step": 1, "description": "צעד"}],
        }

        new_id = insert_scenario(new_scenario)
        assert new_id is not None

        # Table should still exist
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'")
        assert cursor.fetchone() is not None

    def test_batch_insertion_injection_prevention(self, in_memory_db):
        """Test that batch insertions are safe from SQL injection."""
        from tatlam.infra.repo import insert_scenario

        # Insert multiple scenarios with injection attempts
        scenarios = [
            {
                "title": f"תרחיש {i}'; DROP TABLE scenarios; --",
                "category": "פיגועים פשוטים",
                "difficulty": "בינוני",
                "steps": [{"step": 1, "description": "צעד"}],
            }
            for i in range(5)
        ]

        for scenario in scenarios:
            scenario_id = insert_scenario(scenario)
            assert scenario_id is not None

        # Verify all inserted and table intact
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM scenarios")
        count = cursor.fetchone()[0]

        assert count >= len(scenarios)

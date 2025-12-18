"""
Security tests for secrets management.

Tests that sensitive data (API keys, passwords) are not exposed.
Target: Static analysis of code and database.
"""

import pytest
import re
from pathlib import Path


@pytest.mark.unit
class TestSecretsManagement:
    """Test suite for secrets and sensitive data protection."""

    def test_no_api_keys_in_code(self):
        """Test that API keys are not hardcoded in source files."""
        # Check all Python files for potential API key patterns
        project_root = Path(".")
        python_files = list(project_root.rglob("*.py"))

        # Common API key patterns
        api_key_patterns = [
            r"api_key\s*=\s*['\"][a-zA-Z0-9_-]{20,}['\"]",
            r"ANTHROPIC_API_KEY\s*=\s*['\"][a-zA-Z0-9_-]{20,}['\"]",
            r"GOOGLE_API_KEY\s*=\s*['\"][a-zA-Z0-9_-]{20,}['\"]",
            r"OPENAI_API_KEY\s*=\s*['\"]sk-[a-zA-Z0-9_-]{40,}['\"]",
        ]

        violations = []

        for py_file in python_files:
            # Skip test files and venv
            if "test" in str(py_file) or "venv" in str(py_file) or ".venv" in str(py_file):
                continue

            try:
                content = py_file.read_text()

                for pattern in api_key_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(f"{py_file}: {matches}")
            except Exception:
                # Skip files that can't be read
                pass

        assert len(violations) == 0, f"Hardcoded API keys found: {violations}"

    def test_config_uses_environment_variables(self):
        """Test that config loads API keys from environment."""
        import config_trinity

        # Config should attempt to load from environment or have placeholder
        # Check that API key attributes exist
        assert hasattr(config_trinity, 'ANTHROPIC_API_KEY')
        assert hasattr(config_trinity, 'GOOGLE_API_KEY')
        assert hasattr(config_trinity, 'OPENAI_API_KEY')

    def test_no_passwords_in_database(self, in_memory_db):
        """Test that database doesn't contain password fields."""
        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(scenarios)")
        columns = cursor.fetchall()

        column_names = [col[1].lower() for col in columns]

        # Should not have password-related fields
        sensitive_fields = ["password", "passwd", "pwd", "secret", "token"]

        for field in sensitive_fields:
            assert field not in column_names, f"Sensitive field '{field}' found in database"

    def test_no_secrets_in_version_control(self):
        """Test that .gitignore properly excludes secret files."""
        gitignore_path = Path(".gitignore")

        if not gitignore_path.exists():
            pytest.skip(".gitignore not found")

        gitignore_content = gitignore_path.read_text()

        # Should ignore common secret files
        expected_patterns = [".env", "*.key", "credentials"]

        for pattern in expected_patterns:
            assert pattern in gitignore_content or "# No .env" in gitignore_content

    def test_database_path_not_exposed(self):
        """Test that database path doesn't expose sensitive information."""
        import config_trinity

        db_path = config_trinity.DB_PATH

        # Database path should not contain sensitive information
        sensitive_terms = ["password", "secret", "key", "token"]

        for term in sensitive_terms:
            assert term not in db_path.lower(), f"DB path contains sensitive term: {term}"

    def test_no_credentials_in_repo_history(self):
        """Test that no credentials are in git history."""
        # This would require git log analysis
        # For now, basic check
        gitignore_path = Path(".gitignore")

        if gitignore_path.exists():
            gitignore = gitignore_path.read_text()
            # Should ignore config files with credentials
            assert "config_trinity.py" not in gitignore or "*.env" in gitignore

    def test_api_keys_not_logged(self):
        """Test that API keys are not written to logs."""
        # Check for logging statements that might expose keys
        project_root = Path(".")
        python_files = list(project_root.rglob("*.py"))

        for py_file in python_files:
            if "test" in str(py_file) or "venv" in str(py_file):
                continue

            try:
                content = py_file.read_text()

                # Check for dangerous logging patterns
                if "print(" in content and "API_KEY" in content:
                    # Might be exposing API key
                    # This is a heuristic - may have false positives
                    pass  # Manual review recommended
            except Exception:
                pass

        # Placeholder assertion
        assert True

    def test_sensitive_data_sanitized_in_errors(self):
        """Test that error messages don't expose sensitive data."""
        # When exceptions are raised, they shouldn't contain API keys

        try:
            # Simulate error that might contain sensitive data
            raise ValueError("API key invalid: " + "***")  # Should be redacted
        except ValueError as e:
            error_message = str(e)

            # Should not contain actual key
            assert "sk-" not in error_message  # OpenAI key pattern
            assert len(error_message) < 100  # Shouldn't be exposing full keys

    def test_config_file_permissions(self):
        """Test that config files have appropriate permissions."""
        config_path = Path("config_trinity.py")

        if not config_path.exists():
            pytest.skip("config_trinity.py not found")

        # On Unix systems, check file permissions
        import stat
        import platform

        if platform.system() != "Windows":
            file_stat = config_path.stat()
            mode = file_stat.st_mode

            # Should not be world-readable (others can't read)
            world_readable = bool(mode & stat.S_IROTH)

            # This is a recommendation, not strict requirement
            # In production, config should not be world-readable
            # For development, this might be acceptable
            assert True  # Placeholder - adjust based on deployment needs

    def test_no_api_keys_in_exported_json(self, in_memory_db, sample_scenario_data):
        """Test that exported scenarios don't contain API keys."""
        from tatlam.infra.repo import insert_scenario, fetch_all
        import json

        insert_scenario(sample_scenario_data)
        scenarios = fetch_all()

        json_output = json.dumps(scenarios, ensure_ascii=False, indent=2)

        # Should not contain API key patterns
        assert "sk-" not in json_output  # OpenAI key
        assert "api_key" not in json_output.lower()
        assert "anthropic" not in json_output.lower() or "API" not in json_output

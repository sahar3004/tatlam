"""
Unit tests for tatlam/core/doctrine.py

Tests doctrine/prompt loading functionality.
Target: Verify system prompt loads correctly from system_prompt_he.txt.
"""

import pytest
from pathlib import Path


@pytest.mark.unit
class TestDoctrine:
    """Test suite for doctrine loading."""

    def test_doctrine_file_exists(self):
        """Verify system_prompt_he.txt exists in project root."""
        doctrine_path = Path("system_prompt_he.txt")
        assert doctrine_path.exists(), "Doctrine file system_prompt_he.txt not found"

    def test_doctrine_loads_successfully(self):
        """Test doctrine module can load the prompt."""
        from tatlam.core.doctrine import load_prompt

        prompt = load_prompt()
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_doctrine_contains_hebrew(self):
        """Verify loaded prompt contains Hebrew text."""
        from tatlam.core.doctrine import load_prompt

        prompt = load_prompt()

        # Check for Hebrew characters (Unicode range: U+0590 to U+05FF)
        has_hebrew = any("\u0590" <= char <= "\u05FF" for char in prompt)
        assert has_hebrew, "Doctrine does not contain Hebrew characters"

    def test_doctrine_not_empty(self):
        """Ensure doctrine is not just whitespace."""
        from tatlam.core.doctrine import load_prompt

        prompt = load_prompt()
        assert prompt.strip() != "", "Doctrine is empty or only whitespace"

    def test_doctrine_contains_instructions(self):
        """Verify doctrine contains expected instruction keywords."""
        from tatlam.core.doctrine import load_prompt

        prompt = load_prompt()

        # Check for common instruction patterns (adjust based on actual content)
        # These are examples - adjust to match actual doctrine content
        expected_patterns = ["אבטחה", "תרחיש", "איום"]  # Security, Scenario, Threat

        found_patterns = [pattern for pattern in expected_patterns if pattern in prompt]
        assert len(found_patterns) > 0, "Doctrine missing expected instruction patterns"

    def test_doctrine_caching(self):
        """Test that multiple loads return consistent content."""
        from tatlam.core.doctrine import load_prompt

        prompt1 = load_prompt()
        prompt2 = load_prompt()

        assert prompt1 == prompt2, "Doctrine content inconsistent across loads"

    def test_doctrine_encoding(self):
        """Verify doctrine is properly encoded (UTF-8)."""
        doctrine_path = Path("system_prompt_he.txt")

        # Should not raise encoding errors
        with open(doctrine_path, encoding="utf-8") as f:
            content = f.read()

        assert content is not None
        assert len(content) > 0

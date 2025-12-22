"""
Unit tests for Gold Markdown parsing logic.
Mocks out the heavy 'run_batch' dependency to isolate the parsing logic.
"""
import sys
from unittest.mock import MagicMock

# --- ARCHITECTURAL ISOLATION ---
# 'import_gold_md' was moved to 'tatlam.core.md_parser'.
# It imports 'tatlam.core.batch_logic'.
# We mock it to prevent side effects and improve test speed.
mock_batch_logic = MagicMock()
sys.modules["tatlam.core.batch_logic"] = mock_batch_logic
# -------------------------------

import pytest
from tatlam.core.gold_md import parse_md_to_scenario

SAMPLE_MD = """
# תרחיש בדיקה בסיסי

**קטגוריה**: בדיקות
**רמת סיכון**: נמוך

## סיפור מקרה
אדם נכנס לחדר ומפעיל אזעקה.

## שלבי תגובה
1. זהה את האיום
2. דווח למרכז
"""

def test_parse_simple_scenario():
    """Test parsing a valid simple Hebrew markdown scenario."""
    # We need to make sure the parser logic actually runs.
    # Since we mocked run_batch, we hope import_gold_md doesn't use it 
    # inside parse_md_to_scenario.
    
    result = parse_md_to_scenario(SAMPLE_MD)
    
    assert isinstance(result, dict)
    # The parser usually cleans title
    assert "תרחיש בדיקה בסיסי" in result.get("title", "")
    assert result.get("category") == "בדיקות"
    
    # Check steps parsing
    steps = result.get("steps", [])
    # The parser might return list of strings or list of dicts depending on impl
    # Based on models.py it expects JSON list
    assert len(steps) > 0

def test_parse_garbage_input():
    """Test parser resilience against garbage input."""
    garbage = "dfgfdg 435435 %%$$##"
    result = parse_md_to_scenario(garbage)
    assert isinstance(result, dict)
    # Should probably return empty fields rather than crash
    
def test_parse_empty_input():
    """Test parser resilience against empty input."""
    result = parse_md_to_scenario("")
    assert isinstance(result, dict)


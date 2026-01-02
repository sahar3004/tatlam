"""
Unit tests for Scout and Curator nodes.
"""
import pytest
from unittest.mock import Mock, patch

from tatlam.graph.state import SwarmState, WorkflowPhase
from tatlam.graph.nodes.scout import scout_node, _parse_seeds, _build_scout_prompt
from tatlam.graph.nodes.curator import curator_node, _parse_curated_seeds


class TestScoutNode:
    """Tests for the Scout node."""

    def test_scout_parses_seeds_correctly(self):
        """Test that _parse_seeds extracts seeds from raw text."""
        raw_text = """
1. אדם עם מעיל כבד בקיץ מתנהג בעצבנות ליד הכרטוס
2. תיק עזוב מתחת לספסל ברציף עם חוטים בולטים
- רחפן נמוך מעל הכניסה הראשית בשעת לחץ
• משאית נטושה במרחק 50 מטר מהתחנה
"""
        seeds = _parse_seeds(raw_text)
        
        assert len(seeds) == 4
        assert "אדם עם מעיל כבד" in seeds[0]
        assert "תיק עזוב" in seeds[1]
        
    def test_scout_parses_empty_input(self):
        """Test that _parse_seeds handles empty input."""
        seeds = _parse_seeds("")
        assert seeds == []
        
    def test_scout_filters_short_lines(self):
        """Test that very short lines are filtered out."""
        raw_text = "קצר\nשורה ארוכה מספיק כדי להיות רעיון טוב לתרחיש"
        seeds = _parse_seeds(raw_text)
        
        assert len(seeds) == 1
        assert "שורה ארוכה" in seeds[0]

    def test_build_scout_prompt_includes_category(self):
        """Test that the prompt includes the category."""
        prompt = _build_scout_prompt("חפץ חשוד", count=10)
        
        assert "חפץ חשוד" in prompt
        assert "10" in prompt

    def test_scout_skips_when_no_local_client(self):
        """Test that scout gracefully skips when local LLM unavailable."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        with patch('tatlam.graph.nodes.scout._get_local_client', return_value=None):
            result = scout_node(state)
        
        assert result.scout_seeds == []
        assert result.current_phase == WorkflowPhase.SCOUTING
        
    def test_scout_populates_seeds_on_success(self):
        """Test that scout populates scout_seeds on successful LLM call."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="1. רעיון ראשון לתרחיש\n2. רעיון שני לתרחיש"))]
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch('tatlam.graph.nodes.scout._get_local_client', return_value=mock_client):
            with patch('tatlam.graph.nodes.scout.get_settings') as mock_settings:
                mock_settings.return_value.LOCAL_MODEL_NAME = "test-model"
                result = scout_node(state)
        
        assert len(result.scout_seeds) == 2
        assert "רעיון ראשון" in result.scout_seeds[0]


class TestCuratorNode:
    """Tests for the Curator node."""
    
    def test_curator_skips_when_no_seeds(self):
        """Test that curator skips when there are no seeds."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        state.scout_seeds = []
        
        result = curator_node(state)
        
        assert result.scout_seeds == []
        
    def test_curator_limits_seeds_when_no_cloud_client(self):
        """Test that curator limits seeds when cloud LLM unavailable."""
        state = SwarmState(category="חפץ חשוד", batch_size=3)
        state.scout_seeds = ["seed1", "seed2", "seed3", "seed4", "seed5"]
        
        with patch('tatlam.graph.nodes.curator._get_cloud_client', return_value=None):
            result = curator_node(state)
        
        assert len(result.scout_seeds) == 3  # Limited to batch_size
        
    def test_parse_curated_seeds_extracts_list(self):
        """Test that _parse_curated_seeds extracts selected seeds."""
        response = '{"selected_seeds": ["רעיון א", "רעיון ב"], "reasoning": "טובים"}'
        original = ["רעיון א", "רעיון ב", "רעיון ג"]
        
        curated = _parse_curated_seeds(response, original)
        
        assert len(curated) == 2
        assert "רעיון א" in curated
        
    def test_parse_curated_seeds_fallback_on_invalid_json(self):
        """Test fallback to original seeds on invalid JSON."""
        response = "not valid json"
        original = ["seed1", "seed2", "seed3"]
        
        curated = _parse_curated_seeds(response, original)
        
        # Should fallback to first 8 of original
        assert curated == original[:8]
        
    def test_curator_updates_phase(self):
        """Test that curator updates the workflow phase."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        state.scout_seeds = ["seed1", "seed2"]
        
        with patch('tatlam.graph.nodes.curator._get_cloud_client', return_value=None):
            result = curator_node(state)
        
        assert result.current_phase == WorkflowPhase.CURATING

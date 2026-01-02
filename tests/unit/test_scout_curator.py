"""
Unit tests for Scout and Curator nodes.
"""

from unittest.mock import Mock, patch, MagicMock

from tatlam.graph.state import SwarmState, WorkflowPhase
from tatlam.graph.nodes.scout import (
    scout_node,
    _parse_seeds,
    _build_scout_prompt,
    _call_local_llm_batch,
    _local_self_curate,
    _get_learning_context,
    _build_fallback_prompt,
    _get_local_client,
    _get_anthropic_client,
    _call_claude_refinement,
)
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
        """Test that scout gracefully skips when local LLM unavailable and no Claude."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)

        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=None):
            with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=None):
                result = scout_node(state)

        assert result.scout_seeds == []
        assert result.current_phase == WorkflowPhase.SCOUTING

    def test_scout_populates_seeds_on_success(self):
        """Test that scout populates scout_seeds on successful multi-round LLM call."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)

        # Mock the new batch function to return a list of ideas
        mock_ideas = [
            "רעיון ראשון לתרחיש אבטחה מעניין",
            "רעיון שני לתרחיש עם דילמה מורכבת",
        ]

        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=Mock()):
            with patch("tatlam.graph.nodes.scout._call_local_llm_batch", return_value=mock_ideas):
                with patch("tatlam.graph.nodes.scout._local_self_curate", return_value=mock_ideas):
                    with patch("tatlam.graph.nodes.scout.get_settings") as mock_settings:
                        mock_settings.return_value.LOCAL_MODEL_NAME = "test-model"
                        mock_settings.return_value.SCOUT_ROUNDS = 3
                        mock_settings.return_value.SCOUT_IDEAS_PER_ROUND = 50
                        mock_settings.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
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

        with patch("tatlam.graph.nodes.curator._get_cloud_client", return_value=None):
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

        with patch("tatlam.graph.nodes.curator._get_cloud_client", return_value=None):
            result = curator_node(state)

        assert result.current_phase == WorkflowPhase.CURATING


class TestScoutNewFunctions:
    """Tests for new multi-round Scout functions."""

    def test_get_learning_context_returns_dict(self):
        """Test that _get_learning_context returns proper dictionary."""
        mock_context = {"positive_examples": ["example1"], "negative_patterns": ["bad"]}
        
        with patch("tatlam.infra.repo.get_learning_context", return_value=mock_context):
            result = _get_learning_context("חפץ חשוד")
        
        assert "positive_examples" in result
        assert "negative_patterns" in result

    def test_get_learning_context_handles_exception(self):
        """Test that _get_learning_context handles exceptions gracefully."""
        with patch("tatlam.infra.repo.get_learning_context", side_effect=Exception("DB error")):
            result = _get_learning_context("חפץ חשוד")
        
        assert result == {"positive_examples": [], "negative_patterns": []}

    def test_call_local_llm_batch_generates_ideas(self):
        """Test that _call_local_llm_batch runs multiple rounds."""
        mock_client = Mock()
        mock_response = Mock()
        # Ideas need to be long enough to pass _parse_seeds filter (>15 chars)
        mock_response.choices = [Mock(message=Mock(content="1. רעיון ראשון לתרחיש אבטחה במפלס הכניסה\n2. רעיון שני לתרחיש עם דילמה מורכבת"))]
        mock_client.chat.completions.create.return_value = mock_response

        result = _call_local_llm_batch(
            mock_client, "test-model", "חפץ חשוד", rounds=2, per_round=10, venue_type="allenby"
        )

        # Should call LLM twice (2 rounds)
        assert mock_client.chat.completions.create.call_count == 2
        # Ideas are deduplicated, so we should have 2 unique ideas
        assert len(result) == 2

    def test_call_local_llm_batch_deduplicates(self):
        """Test that _call_local_llm_batch removes duplicates."""
        mock_client = Mock()
        mock_response = Mock()
        # Same idea twice should be deduplicated
        mock_response.choices = [Mock(message=Mock(content="רעיון זהה לתרחיש אבטחה"))]
        mock_client.chat.completions.create.return_value = mock_response

        result = _call_local_llm_batch(
            mock_client, "test-model", "חפץ חשוד", rounds=2, per_round=10, venue_type="allenby"
        )

        # Should have only 1 unique idea despite 2 rounds
        assert len(result) == 1

    def test_call_local_llm_batch_handles_failure(self):
        """Test that _call_local_llm_batch handles round failures gracefully."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("LLM Error")

        result = _call_local_llm_batch(
            mock_client, "test-model", "חפץ חשוד", rounds=2, per_round=10, venue_type="allenby"
        )

        # Should return empty list on failure
        assert result == []

    def test_local_self_curate_selects_ideas(self):
        """Test that _local_self_curate selects top K ideas."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="1, 3, 5"))]
        mock_client.chat.completions.create.return_value = mock_response

        ideas = ["idea1", "idea2", "idea3", "idea4", "idea5"]
        context = {"positive_examples": [], "negative_patterns": []}

        result = _local_self_curate(
            mock_client, "test-model", ideas, context, top_k=3, category="חפץ חשוד"
        )

        assert len(result) == 3
        assert "idea1" in result
        assert "idea3" in result
        assert "idea5" in result

    def test_local_self_curate_returns_all_if_less_than_topk(self):
        """Test that _local_self_curate returns all ideas if less than top_k."""
        mock_client = Mock()
        ideas = ["idea1", "idea2"]
        context = {"positive_examples": [], "negative_patterns": []}

        result = _local_self_curate(
            mock_client, "test-model", ideas, context, top_k=10, category="חפץ חשוד"
        )

        assert result == ideas

    def test_local_self_curate_handles_failure(self):
        """Test that _local_self_curate falls back on failure."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("LLM Error")

        ideas = ["idea1", "idea2", "idea3", "idea4", "idea5"]
        context = {"positive_examples": [], "negative_patterns": []}

        result = _local_self_curate(
            mock_client, "test-model", ideas, context, top_k=3, category="חפץ חשוד"
        )

        # Should fallback to first top_k
        assert len(result) == 3
        assert result == ideas[:3]

    def test_build_fallback_prompt_includes_category(self):
        """Test that _build_fallback_prompt includes category."""
        prompt = _build_fallback_prompt("חפץ חשוד", count=15)
        
        assert "חפץ חשוד" in prompt
        assert "15" in prompt

    def test_build_scout_prompt_jaffa_venue(self):
        """Test that _build_scout_prompt handles jaffa venue."""
        prompt = _build_scout_prompt("חפץ חשוד", count=20, venue_type="jaffa")
        
        assert "יפו" in prompt or "jaffa" in prompt
        assert "20" in prompt


class TestScoutCoverage100:
    """Tests to achieve 100% coverage for scout.py."""

    # === Client Getters (lines 41-47, 56-58) ===
    
    def test_get_local_client_returns_client(self):
        """Test that _get_local_client returns a client when available."""
        mock_client = Mock()
        # scout.py imports client_local inside _get_local_client, so patch at source
        with patch("tatlam.core.llm_factory.client_local", return_value=mock_client):
            result = _get_local_client()
        assert result == mock_client

    def test_get_local_client_returns_none_on_config_error(self):
        """Test that _get_local_client returns None on ConfigurationError."""
        from tatlam.core.llm_factory import ConfigurationError
        # Patch at the source module where client_local is defined
        with patch("tatlam.core.llm_factory.client_local", side_effect=ConfigurationError("test")):
            result = _get_local_client()
        assert result is None

    def test_get_anthropic_client_returns_client(self):
        """Test that _get_anthropic_client returns a client when available."""
        mock_client = Mock()
        # scout.py imports create_writer_client inside _get_anthropic_client, so patch at source
        with patch("tatlam.core.llm_factory.create_writer_client", return_value=mock_client):
            result = _get_anthropic_client()
        assert result == mock_client

    def test_get_anthropic_client_returns_none_on_error(self):
        """Test that _get_anthropic_client returns None on error."""
        # Patch at the source module where create_writer_client is defined
        with patch("tatlam.core.llm_factory.create_writer_client", side_effect=Exception("no api key")):
            result = _get_anthropic_client()
        assert result is None

    # === Claude Refinement (line 261) ===
    
    def test_call_claude_refinement_success(self):
        """Test that _call_claude_refinement returns refined text."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="רעיון משופר 1\nרעיון משופר 2")]
        mock_client.messages.create.return_value = mock_response
        
        result = _call_claude_refinement(mock_client, "claude-3", "raw ideas", "חפץ חשוד")
        
        assert "משופר" in result
        assert mock_client.messages.create.called

    def test_call_claude_refinement_empty_content(self):
        """Test that _call_claude_refinement handles empty content."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response
        
        result = _call_claude_refinement(mock_client, "claude-3", "raw ideas", "חפץ חשוד")
        
        assert result == ""

    # === Self-Curate Branches (lines 210-217) ===
    
    def test_local_self_curate_skips_out_of_range_indices(self):
        """Test that _local_self_curate skips invalid indices."""
        mock_client = Mock()
        mock_response = Mock()
        # Response includes out-of-range indices (99, 100)
        mock_response.choices = [Mock(message=Mock(content="1, 99, 100, 2"))]
        mock_client.chat.completions.create.return_value = mock_response

        ideas = ["idea1 long enough to pass", "idea2 long enough to pass", "idea3 long enough to pass"]
        context = {"positive_examples": [], "negative_patterns": []}

        result = _local_self_curate(
            mock_client, "test-model", ideas, context, top_k=3, category="חפץ חשוד"
        )

        # Should include valid indices only
        assert "idea1 long enough to pass" in result
        assert "idea2 long enough to pass" in result

    def test_local_self_curate_skips_duplicate_indices(self):
        """Test that _local_self_curate skips duplicate indices."""
        mock_client = Mock()
        mock_response = Mock()
        # Response includes duplicate indices - should only take unique
        mock_response.choices = [Mock(message=Mock(content="1, 1, 1, 2, 2, 3, 3, 3"))]
        mock_client.chat.completions.create.return_value = mock_response

        ideas = ["idea1", "idea2", "idea3", "idea4", "idea5"]
        context = {"positive_examples": [], "negative_patterns": []}

        result = _local_self_curate(
            mock_client, "test-model", ideas, context, top_k=3, category="חפץ חשוד"
        )

        # Should only include unique ideas, capped at top_k
        assert len(result) == 3
        assert "idea1" in result
        assert "idea2" in result
        assert "idea3" in result

    def test_local_self_curate_empty_response(self):
        """Test that _local_self_curate falls back when no valid indices."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="no numbers here"))]
        mock_client.chat.completions.create.return_value = mock_response

        ideas = ["idea1", "idea2", "idea3"]
        context = {"positive_examples": [], "negative_patterns": []}

        result = _local_self_curate(
            mock_client, "test-model", ideas, context, top_k=2, category="חפץ חשוד"
        )

        # Should fallback to first top_k
        assert result == ideas[:2]

    # === Scout Node Paths ===
    
    def test_scout_node_jaffa_venue_detection(self):
        """Test that scout_node detects jaffa venue from category."""
        state = SwarmState(category="jaffa surface test", batch_size=5)
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=None):
            with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=None):
                result = scout_node(state)
        
        # Jaffa detection happens internally, we just verify no crash
        assert result.current_phase == WorkflowPhase.SCOUTING

    def test_scout_node_with_local_and_claude(self):
        """Test scout_node full path with both local and Claude."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        mock_ideas = ["רעיון ראשון לתרחיש ארוך", "רעיון שני לתרחיש ארוך"]
        mock_claude = Mock()
        mock_claude_response = Mock()
        mock_claude_response.content = [Mock(text="רעיון משופר ראשון\nרעיון משופר שני")]
        mock_claude.messages.create.return_value = mock_claude_response
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=Mock()):
            with patch("tatlam.graph.nodes.scout._call_local_llm_batch", return_value=mock_ideas):
                with patch("tatlam.graph.nodes.scout._local_self_curate", return_value=mock_ideas):
                    with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=mock_claude):
                        with patch("tatlam.graph.nodes.scout.get_settings") as mock_settings:
                            mock_settings.return_value.LOCAL_MODEL_NAME = "test"
                            mock_settings.return_value.WRITER_MODEL_NAME = "claude"
                            mock_settings.return_value.SCOUT_ROUNDS = 1
                            mock_settings.return_value.SCOUT_IDEAS_PER_ROUND = 10
                            mock_settings.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
                            result = scout_node(state)
        
        assert len(result.scout_seeds) > 0

    def test_scout_node_curated_fallback(self):
        """Test that scout_node uses curated ideas when refined_ideas parsing fails."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        # Ideas are long enough to pass parsing
        mock_ideas = ["רעיון ראשון ארוך מאוד לתרחיש", "רעיון שני ארוך מאוד לתרחיש"]
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=Mock()):
            with patch("tatlam.graph.nodes.scout._call_local_llm_batch", return_value=mock_ideas):
                with patch("tatlam.graph.nodes.scout._local_self_curate", return_value=mock_ideas):
                    with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=None):
                        with patch("tatlam.graph.nodes.scout.get_settings") as mock_settings:
                            mock_settings.return_value.LOCAL_MODEL_NAME = "test"
                            mock_settings.return_value.SCOUT_ROUNDS = 1
                            mock_settings.return_value.SCOUT_IDEAS_PER_ROUND = 10
                            mock_settings.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
                            result = scout_node(state)
        
        # Should use curated ideas directly
        assert len(result.scout_seeds) == 2

    def test_scout_node_claude_fallback_mode(self):
        """Test scout_node when no local client, falls back to Claude generation."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        mock_claude = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="רעיון ראשון ארוך מספיק\nרעיון שני ארוך מספיק")]
        mock_response.content[0].text = "רעיון ראשון ארוך מספיק\nרעיון שני ארוך מספיק"
        mock_claude.messages.create.return_value = mock_response
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=None):
            with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=mock_claude):
                with patch("tatlam.graph.nodes.scout.get_settings") as mock_settings:
                    mock_settings.return_value.WRITER_MODEL_NAME = "claude"
                    mock_settings.return_value.SCOUT_ROUNDS = 1
                    mock_settings.return_value.SCOUT_IDEAS_PER_ROUND = 10
                    mock_settings.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
                    result = scout_node(state)
        
        assert mock_claude.messages.create.called

    def test_scout_node_self_curation_path(self):
        """Test scout_node Stage 1.5 self-curation when enough ideas generated."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        # More ideas than top_k triggers self-curation
        many_ideas = [f"רעיון ארוך מספיק מספר {i}" for i in range(15)]
        curated = many_ideas[:10]  # top_k
        
        mock_local = Mock()
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=mock_local):
            with patch("tatlam.graph.nodes.scout._call_local_llm_batch", return_value=many_ideas):
                with patch("tatlam.graph.nodes.scout._get_learning_context", return_value={"positive_examples": [], "negative_patterns": []}):
                    with patch("tatlam.graph.nodes.scout._local_self_curate", return_value=curated) as mock_curate:
                        with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=None):
                            with patch("tatlam.graph.nodes.scout.get_settings") as mock_settings:
                                mock_settings.return_value.LOCAL_MODEL_NAME = "test"
                                mock_settings.return_value.SCOUT_ROUNDS = 1
                                mock_settings.return_value.SCOUT_IDEAS_PER_ROUND = 20
                                mock_settings.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
                                result = scout_node(state)
        
        # Self-curation should have been called
        mock_curate.assert_called_once()
        assert len(result.scout_seeds) == 10

    def test_scout_node_claude_empty_response_hasattr(self):
        """Test scout_node when Claude returns content without text attribute."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        mock_claude = Mock()
        mock_response = Mock()
        # Content block without 'text' attribute
        mock_content_block = Mock(spec=[])  # Empty spec - no text attribute
        mock_response.content = [mock_content_block]
        mock_claude.messages.create.return_value = mock_response
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=None):
            with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=mock_claude):
                with patch("tatlam.graph.nodes.scout.get_settings") as mock_settings:
                    mock_settings.return_value.WRITER_MODEL_NAME = "claude"
                    mock_settings.return_value.SCOUT_ROUNDS = 1
                    mock_settings.return_value.SCOUT_IDEAS_PER_ROUND = 10
                    mock_settings.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
                    result = scout_node(state)
        
        # Should handle gracefully with no seeds
        assert result.scout_seeds == []

    def test_scout_node_curated_ideas_as_fallback(self):
        """Test that curated ideas are used when refined_ideas parsing returns empty."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        # Long ideas that pass _parse_seeds filter
        curated = ["רעיון ראשון ארוך מספיק לעבור את הפילטר", "רעיון שני ארוך מספיק לעבור"]
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=Mock()):
            with patch("tatlam.graph.nodes.scout._call_local_llm_batch", return_value=curated):
                with patch("tatlam.graph.nodes.scout._local_self_curate", return_value=curated):
                    with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=None):
                        with patch("tatlam.graph.nodes.scout.get_settings") as mock_settings:
                            mock_settings.return_value.LOCAL_MODEL_NAME = "test"
                            mock_settings.return_value.SCOUT_ROUNDS = 1
                            mock_settings.return_value.SCOUT_IDEAS_PER_ROUND = 10
                            mock_settings.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
                            result = scout_node(state)
        
        # Since no Claude, refined_ideas comes from curated, should parse them
        assert len(result.scout_seeds) == 2

    def test_scout_node_stage1_exception_handling(self):
        """Test that scout_node handles exceptions in Stage 1 gracefully."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        # Simulate exception during local LLM call
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=Mock()):
            with patch("tatlam.graph.nodes.scout._call_local_llm_batch", side_effect=Exception("LLM error")):
                with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=None):
                    result = scout_node(state)
        
        # Should catch exception and return empty seeds/handled state
        assert result.scout_seeds == []
        assert result.metrics.llm_errors > 0

    def test_scout_node_claude_empty_refinement_fallback(self):
        """Test fallback to curated ideas when Claude returns empty string."""
        state = SwarmState(category="חפץ חשוד", batch_size=5)
        
        curated = ["רעיון 1", "רעיון 2"]
        mock_local = Mock()
        mock_claude = Mock()
        
        # Claude returns empty content
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = ""
        mock_response.content = [mock_content]
        mock_claude.messages.create.return_value = mock_response
        
        with patch("tatlam.graph.nodes.scout._get_local_client", return_value=mock_local):
            with patch("tatlam.graph.nodes.scout._call_local_llm_batch", return_value=curated):
                with patch("tatlam.graph.nodes.scout._local_self_curate", return_value=curated):
                    with patch("tatlam.graph.nodes.scout._get_anthropic_client", return_value=mock_claude):
                        with patch("tatlam.graph.nodes.scout.get_settings") as s:
                            # Mock settings to ensure flow
                            s.return_value.WRITER_MODEL_NAME = "claude"
                            s.return_value.SCOUT_ROUNDS = 1
                            s.return_value.SCOUT_IDEAS_PER_ROUND = 10
                            s.return_value.SCOUT_TOP_K_TO_CLAUDE = 10
                            
                            result = scout_node(state)
        
        # Should fall back to curated ideas
        assert result.scout_seeds == curated
        # refined_ideas should have been empty
        assert not mock_claude.messages.create.return_value.content[0].text

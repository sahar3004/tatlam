from unittest.mock import MagicMock, patch, ANY
import pytest
from tatlam.graph.nodes.clerk import clerk_node, _parse_and_validate, _refine_to_json
from tatlam.graph.state import SwarmState, ScenarioCandidate, ScenarioStatus

@pytest.fixture
def mock_cloud_client():
    with patch("tatlam.core.llm_factory.client_cloud") as mock:
        client = MagicMock()
        mock.return_value = client
        yield mock, client

@pytest.fixture
def mock_settings():
    with patch("tatlam.graph.nodes.clerk.get_settings") as mock:
        settings = MagicMock()
        settings.GEN_MODEL = "gpt-4"
        mock.return_value = settings
        yield settings

@pytest.fixture
def mock_parser():
    with patch("tatlam.graph.nodes.clerk.strip_markdown_and_parse_json") as mock:
        yield mock

@pytest.fixture
def mock_coercer():
    with patch("tatlam.graph.nodes.clerk.coerce_bundle_shape") as mock:
        mock.side_effect = lambda x: x # Pass through or modify if needed
        yield mock

@pytest.fixture
def mock_system_prompt():
    with patch("tatlam.core.doctrine.get_system_prompt") as mock:
        mock.return_value = "System"
        yield mock

class TestClerkNode:

    def test_refine_to_json(self, mock_cloud_client, mock_system_prompt):
        mock_get, client = mock_cloud_client
        
        choice = MagicMock()
        choice.message.content = "{}"
        client.chat.completions.create.return_value.choices = [choice]
        
        res = _refine_to_json(client, "model", "draft")
        assert res == "{}"
        client.chat.completions.create.assert_called()
        assert client.chat.completions.create.call_args[1]["response_format"] == {"type": "json_object"}

    def test_parse_and_validate_structure(self, mock_parser, mock_coercer):
        state = SwarmState(bundle_id="bid", category="cat")
        
        # 1. Dict with scenarios
        mock_parser.return_value = {"scenarios": [{"title": "t1"}]}
        res = _parse_and_validate("txt", state)
        assert len(res) == 1
        assert res[0]["title"] == "t1"
        assert res[0]["category"] == "cat" # Injected default

        # 2. List
        mock_parser.return_value = [{"title": "t2", "category": "custom"}]
        res = _parse_and_validate("txt", state)
        assert len(res) == 1
        assert res[0]["title"] == "t2"
        assert res[0]["category"] == "custom"

        # 3. Single Dict (not wrapped)
        mock_parser.return_value = {"title": "t3"}
        res = _parse_and_validate("txt", state)
        assert len(res) == 1
        assert res[0]["title"] == "t3"

        # 4. Invalid Type
        mock_parser.return_value = "string" # not dict/list
        res = _parse_and_validate("txt", state)
        assert res == []
        
        # 5. None
        mock_parser.return_value = None
        res = _parse_and_validate("txt", state)
        assert res == []

    def test_parse_and_validate_filtering(self, mock_parser, mock_coercer):
        state = SwarmState(bundle_id="bid", category="cat")
        mock_parser.return_value = [
            {"title": "Valid"},
            {"no_title": "Invalid"}, # No title -> skip
        ]
        res = _parse_and_validate("txt", state)
        assert len(res) == 1
        assert res[0]["title"] == "Valid"

    def test_clerk_node_success(self, mock_cloud_client, mock_parser, mock_coercer, mock_settings):
        _, client = mock_cloud_client
        mock_parser.return_value = [{"title": "Refined"}]
        
        state = SwarmState(category="test")
        # Add raw candidate
        c = state.add_candidate({"_is_raw_draft": True, "_raw_text": "Draft"})
        c.status = ScenarioStatus.DRAFT
        
        final_state = clerk_node(state)
        
        # Check raw removed (filtered out of .candidates logic actually replaces list)
        # Wait, clerk_node sets status=ARCHIVED then filters.
        
        # Check new candidates
        assert len(final_state.candidates) == 1
        new_c = final_state.candidates[0]
        assert new_c.title == "Refined"
        assert new_c.status == ScenarioStatus.FORMATTED
        assert not new_c.data.get("_is_raw_draft")
        
        # Verify refinement called
        client.chat.completions.create.assert_called()

    def test_clerk_node_no_drafts(self):
        state = SwarmState()
        # No raw candidates
        final_state = clerk_node(state)
        assert final_state == state

    def test_clerk_node_client_failure(self, mock_cloud_client):
        mock_get, client = mock_cloud_client
        mock_get.side_effect = Exception("Client Down")
        
        state = SwarmState()
        c = state.add_candidate({"_is_raw_draft": True, "_raw_text": "Draft"})
        
        final_state = clerk_node(state)
        assert "Clerk failed" in final_state.errors[0]

    def test_clerk_node_refinement_retry_failure(self, mock_cloud_client, mock_parser, mock_settings):
        _, client = mock_cloud_client
        client.chat.completions.create.side_effect = Exception("LLM Error") 
        # Both attempts fail
        
        # Mock parser to fail on draft_text too (so fallback fails)
        mock_parser.return_value = None
        
        state = SwarmState(category="test")
        c = state.add_candidate({"_is_raw_draft": True, "_raw_text": "Draft"})
        c.status = ScenarioStatus.DRAFT
        
        final_state = clerk_node(state)
        
        # Should have parse errors
        assert final_state.metrics.parse_errors > 0 # From retry fail
        
        # Raw candidate remains? No, logic iterates and logs error/continue.
        # It sets `raw_candidate.status = ARCHIVED` at end of loop.
        # But `continue` is hit! So status NOT set to ARCHIVED.
        # And filtering at end: `[c for c in state.candidates if not c.data.get("_is_raw_draft")]`
        # But if we `continue`, the raw candidate is STILL in `state.candidates`.
        # AND it still has `_is_raw_draft`.
        # So it is REMOVED from the list?
        # Line 204: `state.candidates = [c for c in state.candidates if not c.data.get("_is_raw_draft")]`
        # This removes ALL raw drafts regardless of processing success?
        # Yes.
        
        assert len(final_state.candidates) == 0

    def test_clerk_node_fallback_to_draft(self, mock_cloud_client, mock_parser, mock_settings):
        _, client = mock_cloud_client
        client.chat.completions.create.side_effect = Exception("LLM Error") 
        
        # Parser works on draft text!
        mock_parser.side_effect = [None, None, [{"title": "From Draft"}]] 
        # 1. refined (fail)
        # 2. refined retry (fail) - wait, if Exception raised in refinement, it skips to catch retry logic.
        # If refinement RAISES, it goes to retry block.
        # Retry block raises -> logs error, adds error, CONTINUE.
        # So it SKIPS step 2 (parsing).
        
        # Wait, I want to test logic: `if not scenarios: scenarios = _parse_and_validate(draft_text)`
        # This happens if refinement SUCCEEDS but returns bad JSON.
        
        client.chat.completions.create.side_effect = None
        choice = MagicMock()
        choice.message.content = "Bad JSON"
        client.chat.completions.create.return_value.choices = [choice]
        
        # Refine succeeds (returns "Bad JSON").
        # Parse refined fails (returns None/empty).
        # Fallback to draft text.
        
        # mock_parser called twice: once for "Bad JSON", once for "Draft"
        def parse_side_effect(text):
            if text == "Bad JSON": return None
            if text == "Draft": return [{"title": "Fallback"}]
            return None
        mock_parser.side_effect = parse_side_effect
        
        state = SwarmState(category="test")
        c = state.add_candidate({"_is_raw_draft": True, "_raw_text": "Draft"})
        c.status = ScenarioStatus.DRAFT
        
        final_state = clerk_node(state)
        
        assert len(final_state.candidates) == 1
        assert final_state.candidates[0].title == "Fallback"

    def test_clerk_node_parse_failure_all_attempts(self, mock_cloud_client, mock_parser, mock_settings):
        """Test failure to parse both refined and draft text."""
        _, client = mock_cloud_client
        # Refinement succeeds (returns text)
        choice = MagicMock()
        choice.message.content = "Bad JSON"
        client.chat.completions.create.return_value.choices = [choice]
        
        # Parser fails for refined text AND draft text
        mock_parser.return_value = [] 
        
        state = SwarmState(category="test")
        c = state.add_candidate({"_is_raw_draft": True, "_raw_text": "Draft"})
        c.status = ScenarioStatus.DRAFT
        
        final_state = clerk_node(state)
        
        # Should hit line 184-186 (continue)
        # Parse error incremented
        assert final_state.metrics.parse_errors > 0
        # No formatted candidates
        assert len(final_state.candidates) == 0

    def test_clerk_node_empty_draft(self, mock_cloud_client):
        state = SwarmState()
        c = state.add_candidate({"_is_raw_draft": True, "_raw_text": ""})
        c.status = ScenarioStatus.DRAFT
        
        # Empty text -> continue -> filtered out
        final_state = clerk_node(state)
        assert len(final_state.candidates) == 0


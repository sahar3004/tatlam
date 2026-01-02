"""Unit tests for tatlam/graph/nodes/*.py"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from tatlam.graph.state import SwarmState, ScenarioCandidate, ScenarioStatus


class TestSupervisorNode:
    """Tests for supervisor node logic."""

    def test_should_continue_returns_archivist_when_target_reached(self):
        """Test routing to archivist when we have enough scenarios."""
        from tatlam.graph.nodes.supervisor import should_continue

        state = SwarmState(category="Test", target_count=2)

        c1 = state.add_candidate({"title": "One"})
        c1.status = ScenarioStatus.APPROVED

        c2 = state.add_candidate({"title": "Two"})
        c2.status = ScenarioStatus.APPROVED

        result = should_continue(state)
        assert result == "archivist"

    def test_should_continue_returns_writer_when_needs_more(self):
        """Test routing to writer when more scenarios needed."""
        from tatlam.graph.nodes.supervisor import should_continue

        state = SwarmState(category="Test", target_count=5)

        result = should_continue(state)
        assert result == "writer"

    def test_should_continue_returns_writer_for_repair(self):
        """Test routing to writer for repair when scenarios rejected."""
        from tatlam.graph.nodes.supervisor import should_continue

        state = SwarmState(category="Test", target_count=5, max_retries_per_scenario=2)

        c1 = state.add_candidate({"title": "Failed"})
        c1.status = ScenarioStatus.REJECTED
        c1.attempt_count = 1  # Can still be repaired

        result = should_continue(state)
        assert result == "writer"

    def test_should_continue_returns_end_on_max_iterations_no_approved(self):
        """Test ending when max iterations reached with no approved scenarios."""
        from tatlam.graph.nodes.supervisor import should_continue

        state = SwarmState(category="Test", target_count=5, max_iterations=3)
        state.iteration = 3

        result = should_continue(state)
        assert result == "end"

    def test_init_supervisor_validates_category(self):
        """Test initialization validates category."""
        from tatlam.graph.nodes.supervisor import init_supervisor

        state = SwarmState(category="", target_count=5)
        result = init_supervisor(state)

        assert len(result.errors) > 0
        assert "Category" in result.errors[0]

    def test_init_supervisor_validates_target_count(self):
        """Test initialization validates target count."""
        from tatlam.graph.nodes.supervisor import init_supervisor

        state = SwarmState(category="Test", target_count=0)
        result = init_supervisor(state)

        assert len(result.errors) > 0


class TestWriterNode:
    """Tests for writer node (mocked LLM calls)."""

    @patch("tatlam.graph.nodes.writer._get_clients")
    @patch("tatlam.graph.nodes.writer._call_llm")
    def test_writer_adds_raw_candidate(self, mock_call, mock_clients):
        """Test that writer adds a raw candidate to state."""
        from tatlam.graph.nodes.writer import writer_node

        mock_local = MagicMock()
        mock_clients.return_value = (mock_local, None)
        mock_call.return_value = "Generated text content"

        state = SwarmState(category="חפץ חשוד", target_count=5)
        result = writer_node(state)

        assert len(result.candidates) == 1
        assert result.candidates[0].data.get("_is_raw_draft") is True

    @patch("tatlam.graph.nodes.writer._get_clients")
    def test_writer_handles_no_clients(self, mock_clients):
        """Test writer handles case when no LLM clients available."""
        from tatlam.graph.nodes.writer import writer_node

        mock_clients.return_value = (None, None)

        state = SwarmState(category="Test", target_count=5)
        result = writer_node(state)

        assert len(result.errors) > 0

    def test_get_doctrine_context_returns_string(self):
        """Test doctrine context extraction."""
        from tatlam.graph.nodes.writer import _get_doctrine_context

        context = _get_doctrine_context()

        assert isinstance(context, str)
        assert "טווחי בטיחות" in context or "DOCTRINE" in context


class TestClerkNode:
    """Tests for clerk (formatter) node."""

    def test_clerk_skips_when_no_raw_drafts(self):
        """Test clerk does nothing when no raw drafts."""
        from tatlam.graph.nodes.clerk import clerk_node

        state = SwarmState(category="Test", target_count=5)
        result = clerk_node(state)

        assert len(result.candidates) == 0

    @patch("tatlam.core.llm_factory.client_cloud")
    def test_clerk_processes_raw_drafts(self, mock_cloud):
        """Test clerk processes raw drafts into formatted candidates."""
        from tatlam.graph.nodes.clerk import clerk_node

        state = SwarmState(category="Test", target_count=5)

        # Add a raw candidate
        raw = state.add_candidate({
            "_raw_text": '{"scenarios": [{"title": "Test", "category": "Test"}]}',
            "_is_raw_draft": True,
            "category": "Test",
        })
        raw.status = ScenarioStatus.DRAFT

        # Mock cloud client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"scenarios": [{"title": "Test", "category": "Test"}]}'
        mock_cloud.return_value.chat.completions.create.return_value = mock_response

        result = clerk_node(state)

        # Raw draft should be removed, formatted candidate added
        raw_count = sum(1 for c in result.candidates if c.data.get("_is_raw_draft"))
        assert raw_count == 0


class TestDeduplicatorNode:
    """Tests for deduplicator node (mocked embeddings)."""

    @patch("tatlam.graph.nodes.deduplicator._load_existing_embeddings")
    @patch("tatlam.graph.nodes.deduplicator._embed_text")
    def test_deduplicator_marks_unique(self, mock_embed, mock_load):
        """Test deduplicator marks non-duplicate as UNIQUE."""
        from tatlam.graph.nodes.deduplicator import deduplicator_node
        import numpy as np

        mock_load.return_value = ([], [])  # No existing embeddings
        mock_embed.return_value = np.array([0.1, 0.2, 0.3])

        state = SwarmState(category="Test", target_count=5)
        c1 = state.add_candidate({"title": "New Unique"})
        c1.status = ScenarioStatus.FORMATTED

        result = deduplicator_node(state)

        assert result.candidates[0].status == ScenarioStatus.UNIQUE

    @patch("tatlam.graph.nodes.deduplicator._load_existing_embeddings")
    @patch("tatlam.graph.nodes.deduplicator._embed_text")
    def test_deduplicator_marks_duplicate(self, mock_embed, mock_load):
        """Test deduplicator marks duplicate as REJECTED."""
        from tatlam.graph.nodes.deduplicator import deduplicator_node
        import numpy as np

        # Existing embedding that will match
        existing_vec = np.array([0.1, 0.2, 0.3])
        mock_load.return_value = (["Existing Title"], [existing_vec])

        # Same embedding for new candidate
        mock_embed.return_value = existing_vec

        state = SwarmState(category="Test", target_count=5, diversity_threshold=0.9)
        c1 = state.add_candidate({"title": "Duplicate", "background": ""})
        c1.status = ScenarioStatus.FORMATTED

        result = deduplicator_node(state)

        assert result.candidates[0].status == ScenarioStatus.REJECTED


class TestJudgeNode:
    """Tests for judge node (mocked LLM calls)."""

    def test_judge_skips_when_no_unique_candidates(self):
        """Test judge does nothing when no unique candidates."""
        from tatlam.graph.nodes.judge import judge_node

        state = SwarmState(category="Test", target_count=5)
        result = judge_node(state)

        assert result.metrics.total_approved == 0
        assert result.metrics.total_rejected == 0

    @patch("tatlam.graph.nodes.judge._score_with_llm")
    def test_judge_approves_high_score(self, mock_score):
        """Test judge approves scenarios above threshold."""
        from tatlam.graph.nodes.judge import judge_node

        mock_score.return_value = (85.0, "Good scenario")

        state = SwarmState(category="Test", target_count=5, score_threshold=70.0)
        c1 = state.add_candidate({
            "title": "Good Scenario",
            "category": "Test",
            "steps": ["step1", "step2", "step3", "step4"],
        })
        c1.status = ScenarioStatus.UNIQUE

        result = judge_node(state)

        assert result.candidates[0].status == ScenarioStatus.APPROVED
        assert result.metrics.total_approved == 1

    @patch("tatlam.graph.nodes.judge._score_with_llm")
    def test_judge_rejects_low_score(self, mock_score):
        """Test judge rejects scenarios below threshold."""
        from tatlam.graph.nodes.judge import judge_node

        mock_score.return_value = (50.0, "Needs improvement")

        state = SwarmState(category="Test", target_count=5, score_threshold=70.0)
        c1 = state.add_candidate({
            "title": "Weak Scenario",
            "category": "Test",
            "steps": ["step1", "step2", "step3", "step4"],
        })
        c1.status = ScenarioStatus.UNIQUE

        result = judge_node(state)

        assert result.candidates[0].status == ScenarioStatus.REJECTED

    def test_build_judge_rubric_from_doctrine(self):
        """Test rubric generation from doctrine."""
        from tatlam.graph.nodes.judge import _build_judge_rubric

        rubric = _build_judge_rubric()

        assert "בטיחות" in rubric or "Safety" in rubric
        assert "חוקיות" in rubric or "Legality" in rubric


class TestArchivistNode:
    """Tests for archivist node (mocked DB)."""

    def test_archivist_skips_when_no_approved(self):
        """Test archivist does nothing when no approved scenarios."""
        from tatlam.graph.nodes.archivist import archivist_node
        from tatlam.graph.state import WorkflowPhase

        state = SwarmState(category="Test", target_count=5)
        result = archivist_node(state)

        assert result.current_phase == WorkflowPhase.COMPLETE

    @patch("tatlam.graph.nodes.archivist.insert_scenario")
    @patch("tatlam.graph.nodes.archivist._save_embedding")
    def test_archivist_saves_approved_scenarios(self, mock_embed, mock_insert):
        """Test archivist saves approved scenarios to DB."""
        from tatlam.graph.nodes.archivist import archivist_node

        mock_insert.return_value = 1  # Scenario ID
        mock_embed.return_value = True

        state = SwarmState(category="Test", target_count=5)
        c1 = state.add_candidate({"title": "Approved", "category": "Test"})
        c1.status = ScenarioStatus.APPROVED

        result = archivist_node(state)

        mock_insert.assert_called_once()
        assert result.candidates[0].status == ScenarioStatus.ARCHIVED

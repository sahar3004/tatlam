"""Unit tests for tatlam/graph/state.py"""

from __future__ import annotations


from tatlam.graph.state import (
    SwarmState,
    ScenarioCandidate,
    ScenarioStatus,
    SwarmMetrics,
    WorkflowPhase,
)


class TestScenarioCandidate:
    """Tests for ScenarioCandidate dataclass."""

    def test_creation_with_defaults(self):
        """Test basic creation with minimal data."""
        data = {"title": "Test Title", "category": "Test Category"}
        candidate = ScenarioCandidate(data=data)

        assert candidate.title == "Test Title"
        assert candidate.category == "Test Category"
        assert candidate.status == ScenarioStatus.DRAFT
        assert candidate.score == 0.0
        assert candidate.attempt_count == 1

    def test_add_feedback(self):
        """Test feedback recording."""
        candidate = ScenarioCandidate(data={"title": "Test"})
        candidate.add_feedback("Good scenario", 85.0)

        assert candidate.score == 85.0
        assert candidate.critique == "Good scenario"
        assert len(candidate.feedback_history) == 1
        assert len(candidate.score_history) == 1
        assert candidate.attempt_count == 2

    def test_multiple_feedback_rounds(self):
        """Test multiple feedback iterations."""
        candidate = ScenarioCandidate(data={"title": "Test"})

        candidate.add_feedback("First feedback", 60.0)
        candidate.add_feedback("Second feedback", 75.0)

        assert candidate.score == 75.0  # Latest score
        assert candidate.critique == "Second feedback"
        assert len(candidate.feedback_history) == 2
        assert candidate.score_history == [60.0, 75.0]
        assert candidate.attempt_count == 3

    def test_to_dict(self):
        """Test serialization to dictionary."""
        candidate = ScenarioCandidate(
            data={"title": "Test", "category": "Cat"},
            status=ScenarioStatus.APPROVED,
            score=90.0,
        )
        d = candidate.to_dict()

        assert d["status"] == "approved"
        assert d["score"] == 90.0
        assert d["data"]["title"] == "Test"


class TestSwarmMetrics:
    """Tests for SwarmMetrics dataclass."""

    def test_update_score_stats_empty(self):
        """Test stats update with empty list."""
        metrics = SwarmMetrics()
        metrics.update_score_stats([])

        assert metrics.average_score == 0.0

    def test_update_score_stats(self):
        """Test stats update with scores."""
        metrics = SwarmMetrics()
        metrics.update_score_stats([60.0, 80.0, 100.0])

        assert metrics.average_score == 80.0
        assert metrics.highest_score == 100.0
        assert metrics.lowest_score == 60.0

    def test_finalize_sets_end_time(self):
        """Test finalize records end time."""
        metrics = SwarmMetrics()
        assert metrics.end_time == ""

        metrics.finalize()
        assert metrics.end_time != ""

    def test_to_dict(self):
        """Test serialization."""
        metrics = SwarmMetrics(total_generated=10, total_approved=5)
        d = metrics.to_dict()

        assert d["total_generated"] == 10
        assert d["total_approved"] == 5


class TestSwarmState:
    """Tests for SwarmState dataclass."""

    def test_creation_with_defaults(self):
        """Test basic creation."""
        state = SwarmState(category="Test Category", target_count=5)

        assert state.category == "Test Category"
        assert state.target_count == 5
        assert state.current_phase == WorkflowPhase.INIT
        assert len(state.candidates) == 0

    def test_add_candidate(self):
        """Test adding candidates."""
        state = SwarmState(category="Test")
        candidate = state.add_candidate({"title": "New Scenario"})

        assert len(state.candidates) == 1
        assert candidate.title == "New Scenario"
        assert state.metrics.total_generated == 1

    def test_approved_scenarios_property(self):
        """Test approved scenarios filtering."""
        state = SwarmState(category="Test")

        c1 = state.add_candidate({"title": "Approved"})
        c1.status = ScenarioStatus.APPROVED

        c2 = state.add_candidate({"title": "Rejected"})
        c2.status = ScenarioStatus.REJECTED

        c3 = state.add_candidate({"title": "Pending"})

        assert len(state.approved_scenarios) == 1
        assert state.approved_scenarios[0].title == "Approved"

    def test_rejected_scenarios_property(self):
        """Test rejected scenarios filtering."""
        state = SwarmState(category="Test")

        c1 = state.add_candidate({"title": "Rejected"})
        c1.status = ScenarioStatus.REJECTED

        c2 = state.add_candidate({"title": "Approved"})
        c2.status = ScenarioStatus.APPROVED

        assert len(state.rejected_scenarios) == 1
        assert state.rejected_scenarios[0].title == "Rejected"

    def test_needs_more_property(self):
        """Test needs_more logic."""
        state = SwarmState(category="Test", target_count=2)

        assert state.needs_more is True

        c1 = state.add_candidate({"title": "One"})
        c1.status = ScenarioStatus.APPROVED
        assert state.needs_more is True

        c2 = state.add_candidate({"title": "Two"})
        c2.status = ScenarioStatus.APPROVED
        assert state.needs_more is False

    def test_add_error(self):
        """Test error recording."""
        state = SwarmState(category="Test")
        state.add_error("Something went wrong")

        assert len(state.errors) == 1
        assert "Something went wrong" in state.errors[0]

    def test_to_bundle_dict(self):
        """Test conversion to bundle format."""
        state = SwarmState(category="Test", bundle_id="TEST-001")

        c1 = state.add_candidate({"title": "Approved"})
        c1.status = ScenarioStatus.APPROVED

        c2 = state.add_candidate({"title": "Rejected"})
        c2.status = ScenarioStatus.REJECTED

        bundle = state.to_bundle_dict()

        assert bundle["bundle_id"] == "TEST-001"
        assert len(bundle["scenarios"]) == 1  # Only approved

    def test_get_summary(self):
        """Test summary generation."""
        state = SwarmState(category="Test", target_count=5)
        state.iteration = 2

        c1 = state.add_candidate({"title": "One"})
        c1.status = ScenarioStatus.APPROVED

        summary = state.get_summary()

        assert summary["category"] == "Test"
        assert summary["iteration"] == 2
        assert summary["approved"] == 1
        assert summary["target"] == 5

    def test_phase_change_logging(self):
        """Test phase transition."""
        state = SwarmState(category="Test")
        assert state.current_phase == WorkflowPhase.INIT

        state.log_phase_change(WorkflowPhase.WRITING)
        assert state.current_phase == WorkflowPhase.WRITING


class TestWorkflowPhase:
    """Tests for WorkflowPhase enum."""

    def test_all_phases_exist(self):
        """Test all expected phases are defined."""
        phases = [
            WorkflowPhase.INIT,
            WorkflowPhase.WRITING,
            WorkflowPhase.FORMATTING,
            WorkflowPhase.DEDUPLICATING,
            WorkflowPhase.JUDGING,
            WorkflowPhase.REPAIRING,
            WorkflowPhase.ARCHIVING,
            WorkflowPhase.COMPLETE,
            WorkflowPhase.ERROR,
        ]
        assert len(phases) == 9


class TestScenarioStatus:
    """Tests for ScenarioStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses are defined."""
        statuses = [
            ScenarioStatus.DRAFT,
            ScenarioStatus.FORMATTED,
            ScenarioStatus.UNIQUE,
            ScenarioStatus.APPROVED,
            ScenarioStatus.REJECTED,
            ScenarioStatus.REPAIRED,
            ScenarioStatus.ARCHIVED,
        ]
        assert len(statuses) == 7

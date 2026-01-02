"""
Tests for the RLHF Learning System components.

Tests the FeedbackLogger, LearningStore, and learning-related repo functions.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestFeedbackLogger:
    """Tests for FeedbackLogger class."""
    
    def test_log_approval_creates_entry(self):
        """Test that logging an approval creates a valid entry."""
        from tatlam.core.feedback_logger import FeedbackLogger, UserAction
        
        logger = FeedbackLogger()
        scenario = {"title": "Test Scenario", "category": "חפץ חשוד"}
        
        entry = logger.log_approval(
            scenario,
            judge_score=85.0,
            judge_critique="Good scenario"
        )
        
        assert entry.user_action == UserAction.APPROVED.value
        assert entry.generated_output == scenario
        assert entry.judge_score == 85.0
        assert entry.category == "חפץ חשוד"
    
    def test_log_rejection_requires_reason(self):
        """Test that rejection without reason raises ValueError."""
        from tatlam.core.feedback_logger import FeedbackLogger
        
        logger = FeedbackLogger()
        scenario = {"title": "Test", "category": "Test"}
        
        with pytest.raises(ValueError, match="mandatory"):
            logger.log_rejection(scenario, reason="")
        
        with pytest.raises(ValueError, match="mandatory"):
            logger.log_rejection(scenario, reason="   ")
    
    def test_log_rejection_with_reason_succeeds(self):
        """Test that rejection with valid reason succeeds."""
        from tatlam.core.feedback_logger import FeedbackLogger, UserAction
        
        logger = FeedbackLogger()
        scenario = {"title": "Bad Scenario", "category": "Test"}
        
        entry = logger.log_rejection(
            scenario,
            reason="Too expensive",
            judge_score=40.0
        )
        
        assert entry.user_action == UserAction.REJECTED.value
        assert entry.user_reason == "Too expensive"
    
    def test_log_revision_with_notes(self):
        """Test logging a revision request."""
        from tatlam.core.feedback_logger import FeedbackLogger, UserAction
        import json
        
        logger = FeedbackLogger()
        scenario = {"title": "Needs Work", "category": "Test"}
        
        entry = logger.log_revision(
            scenario,
            notes="Fix the timeline",
            sections=["steps", "background"]
        )
        
        assert entry.user_action == UserAction.REVISED.value
        revision_data = json.loads(entry.revision_notes)
        assert revision_data["notes"] == "Fix the timeline"
        assert "steps" in revision_data["sections"]
    
    def test_get_rejection_reasons(self):
        """Test retrieving rejection reasons."""
        from tatlam.core.feedback_logger import FeedbackLogger
        
        logger = FeedbackLogger()
        
        # Log some rejections
        logger.log_rejection({"title": "A", "category": "cat1"}, reason="Reason A")
        logger.log_rejection({"title": "B", "category": "cat1"}, reason="Reason B")
        logger.log_rejection({"title": "C", "category": "cat2"}, reason="Reason C")
        
        # Get all reasons
        all_reasons = logger.get_rejection_reasons()
        assert len(all_reasons) == 3
        
        # Get filtered reasons
        cat1_reasons = logger.get_rejection_reasons(category="cat1")
        assert len(cat1_reasons) == 2


class TestLearningStore:
    """Tests for LearningStore class."""
    
    def test_add_to_hall_of_fame(self):
        """Test adding to Hall of Fame."""
        from tatlam.core.learning_store import LearningStore
        
        store = LearningStore()
        scenario = {"title": "Great Scenario", "category": "חפץ חשוד"}
        
        entry = store.add_to_hall_of_fame(scenario, score=92.0, scenario_id=123)
        
        assert entry.scenario_id == 123
        assert entry.score == 92.0
        assert entry.category == "חפץ חשוד"
    
    def test_add_to_graveyard_requires_reason(self):
        """Test that Graveyard requires reason."""
        from tatlam.core.learning_store import LearningStore
        
        store = LearningStore()
        scenario = {"title": "Bad", "category": "Test"}
        
        with pytest.raises(ValueError, match="mandatory"):
            store.add_to_graveyard(scenario, reason="", scenario_id=1)
    
    def test_get_positive_examples_filters_by_category(self):
        """Test filtering positive examples by category."""
        from tatlam.core.learning_store import LearningStore
        
        store = LearningStore()
        
        # Add scenarios to different categories
        store.add_to_hall_of_fame(
            {"title": "A", "category": "cat1"},
            score=90.0,
            scenario_id=1
        )
        store.add_to_hall_of_fame(
            {"title": "B", "category": "cat2"},
            score=85.0,
            scenario_id=2
        )
        
        # Get examples for cat1
        examples = store.get_positive_examples(category="cat1")
        assert len(examples) == 1
        assert examples[0]["title"] == "A"
    
    def test_get_negative_patterns_aggregates_reasons(self):
        """Test aggregating rejection patterns."""
        from tatlam.core.learning_store import LearningStore
        
        store = LearningStore()
        
        # Add rejections with same reason
        store.add_to_graveyard({"title": "A", "category": "test"}, reason="Too expensive", scenario_id=1)
        store.add_to_graveyard({"title": "B", "category": "test"}, reason="Too expensive", scenario_id=2)
        store.add_to_graveyard({"title": "C", "category": "test"}, reason="Wrong dates", scenario_id=3)
        
        patterns = store.get_negative_patterns()
        assert len(patterns) >= 2
        # Most common should be first
        assert patterns[0][0] == "Too expensive"
        assert patterns[0][1] == 2
    
    def test_get_pitfalls_for_context(self):
        """Test getting pitfalls for a specific context."""
        from tatlam.core.learning_store import LearningStore
        
        store = LearningStore()
        
        store.add_to_graveyard({"title": "A", "category": "cat1"}, reason="Issue 1", scenario_id=1)
        store.add_to_graveyard({"title": "B", "category": "cat1"}, reason="Issue 2", scenario_id=2)
        
        pitfalls = store.get_pitfalls_for_context({"category": "cat1"})
        assert len(pitfalls) == 2
        assert "Issue 1" in pitfalls
        assert "Issue 2" in pitfalls


class TestPromptManagerLearning:
    """Tests for PromptManager learning methods."""
    
    def test_format_revision_prompt_requires_feedback(self):
        """Test that revision prompt requires feedback."""
        from tatlam.core.prompts import PromptManager, PromptValidationError
        
        pm = PromptManager()
        scenario = {"title": "Test", "category": "Test"}
        
        with pytest.raises(PromptValidationError, match="empty"):
            pm.format_revision_prompt(scenario, user_feedback="")
    
    def test_format_revision_prompt_includes_feedback(self):
        """Test that revision prompt includes user feedback."""
        from tatlam.core.prompts import PromptManager
        
        pm = PromptManager()
        scenario = {"title": "Test", "category": "Test", "steps": []}
        
        prompt = pm.format_revision_prompt(
            scenario,
            user_feedback="Fix the timeline",
            revision_sections=["steps"]
        )
        
        assert "Fix the timeline" in prompt
        assert "steps" in prompt
    
    def test_format_learning_enhanced_prompt_adds_context(self):
        """Test that learning enhanced prompt adds examples and patterns."""
        from tatlam.core.prompts import PromptManager
        
        pm = PromptManager()
        
        prompt = pm.format_learning_enhanced_prompt(
            base_prompt="Generate a scenario",
            positive_examples=[{"title": "Good Example", "category": "cat1"}],
            negative_patterns=["Too expensive", "Wrong dates"]
        )
        
        assert "Good Example" in prompt
        assert "Too expensive" in prompt
        assert "Wrong dates" in prompt
    
    def test_format_learning_enhanced_prompt_returns_base_if_no_learning(self):
        """Test that base prompt returned if no learning data."""
        from tatlam.core.prompts import PromptManager
        
        pm = PromptManager()
        base = "Generate a scenario"
        
        prompt = pm.format_learning_enhanced_prompt(
            base_prompt=base,
            positive_examples=[],
            negative_patterns=[]
        )
        
        assert prompt == base

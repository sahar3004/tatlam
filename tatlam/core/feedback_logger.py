"""
tatlam/core/feedback_logger.py - Feedback Logger for RLHF Pipeline

This module captures and logs all user feedback on generated scenarios,
forming the foundation of the learning mechanism.

Key Features:
- Structured logging of approvals, revisions, and rejections
- Mandatory rejection reasons for learning
- Complete audit trail for debugging and analysis
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class UserAction(str, Enum):
    """User feedback actions on scenarios."""
    APPROVED = "approved"
    REVISED = "revised"
    REJECTED = "rejected"


@dataclass
class FeedbackEntry:
    """
    Complete record of user feedback on a generated scenario.
    
    This entry captures the full context needed for learning:
    - What was generated (input + output)
    - What the user did (action)
    - Why they did it (reason/notes)
    - Quality metrics (judge score/critique)
    
    Attributes:
        id: Unique identifier (UUID)
        input_context: Original prompt and parameters
        generated_output: The scenario that was generated
        user_action: "approved" | "revised" | "rejected"
        user_reason: Free-text reason (mandatory for reject)
        revision_notes: Specific revision instructions
        timestamp: ISO format timestamp
        judge_score: Score from Judge before user review
        judge_critique: Judge's detailed critique
        scenario_id: Database ID of the scenario (if saved)
        category: Scenario category for filtering
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    input_context: dict[str, Any] = field(default_factory=dict)
    generated_output: dict[str, Any] = field(default_factory=dict)
    user_action: str = UserAction.APPROVED.value
    user_reason: str | None = None
    revision_notes: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    judge_score: float = 0.0
    judge_critique: str = ""
    scenario_id: int | None = None
    category: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackEntry":
        """Create from dictionary."""
        return cls(**data)


class FeedbackLogger:
    """
    Logs user feedback on scenarios for the RLHF learning mechanism.
    
    This logger captures every user interaction with generated scenarios,
    creating an audit trail that enables:
    - Learning from successful examples (Hall of Fame)
    - Avoiding common mistakes (Graveyard patterns)
    - Debugging and quality analysis
    
    Usage:
        logger = FeedbackLogger()
        
        # Log approval
        logger.log_approval(scenario, judge_score=85.0, judge_critique="...")
        
        # Log revision request
        logger.log_revision(scenario, notes="Fix the timeline", sections=["steps"])
        
        # Log rejection (reason is mandatory)
        logger.log_rejection(scenario, reason="Too expensive", judge_critique="...")
    """
    
    def __init__(self):
        """Initialize the feedback logger."""
        self._entries: list[FeedbackEntry] = []
    
    def log_approval(
        self,
        scenario: dict[str, Any],
        *,
        input_context: dict[str, Any] | None = None,
        judge_score: float = 0.0,
        judge_critique: str = "",
        scenario_id: int | None = None,
    ) -> FeedbackEntry:
        """
        Log a user approval of a scenario.
        
        Args:
            scenario: The approved scenario data
            input_context: Original generation parameters
            judge_score: Score from the Judge
            judge_critique: Judge's critique
            scenario_id: Database ID if saved
            
        Returns:
            The created FeedbackEntry
        """
        entry = FeedbackEntry(
            input_context=input_context or {},
            generated_output=scenario,
            user_action=UserAction.APPROVED.value,
            judge_score=judge_score,
            judge_critique=judge_critique,
            scenario_id=scenario_id,
            category=str(scenario.get("category", "")),
        )
        
        self._entries.append(entry)
        logger.info(
            "Logged APPROVAL: id=%s, category=%s, score=%.1f",
            entry.id, entry.category, judge_score
        )
        
        return entry
    
    def log_revision(
        self,
        scenario: dict[str, Any],
        *,
        notes: str,
        sections: list[str] | None = None,
        input_context: dict[str, Any] | None = None,
        judge_score: float = 0.0,
        judge_critique: str = "",
        scenario_id: int | None = None,
    ) -> FeedbackEntry:
        """
        Log a user revision request on a scenario.
        
        Args:
            scenario: The scenario to be revised
            notes: User's revision notes (what to change)
            sections: Specific sections to revise (e.g., ["steps", "background"])
            input_context: Original generation parameters
            judge_score: Score from the Judge
            judge_critique: Judge's critique
            scenario_id: Database ID if saved
            
        Returns:
            The created FeedbackEntry
        """
        # Build structured revision notes
        revision_data = {
            "notes": notes,
            "sections": sections or [],
        }
        
        entry = FeedbackEntry(
            input_context=input_context or {},
            generated_output=scenario,
            user_action=UserAction.REVISED.value,
            revision_notes=json.dumps(revision_data, ensure_ascii=False),
            judge_score=judge_score,
            judge_critique=judge_critique,
            scenario_id=scenario_id,
            category=str(scenario.get("category", "")),
        )
        
        self._entries.append(entry)
        logger.info(
            "Logged REVISION: id=%s, category=%s, sections=%s",
            entry.id, entry.category, sections
        )
        
        return entry
    
    def log_rejection(
        self,
        scenario: dict[str, Any],
        *,
        reason: str,
        input_context: dict[str, Any] | None = None,
        judge_score: float = 0.0,
        judge_critique: str = "",
        scenario_id: int | None = None,
    ) -> FeedbackEntry:
        """
        Log a user rejection of a scenario.
        
        IMPORTANT: Rejection reason is mandatory for learning purposes.
        
        Args:
            scenario: The rejected scenario data
            reason: Why the user rejected it (MANDATORY)
            input_context: Original generation parameters
            judge_score: Score from the Judge
            judge_critique: Judge's critique
            scenario_id: Database ID if saved
            
        Returns:
            The created FeedbackEntry
            
        Raises:
            ValueError: If reason is empty or None
        """
        # Validate mandatory reason
        if not reason or not reason.strip():
            raise ValueError("Rejection reason is mandatory for learning purposes")
        
        entry = FeedbackEntry(
            input_context=input_context or {},
            generated_output=scenario,
            user_action=UserAction.REJECTED.value,
            user_reason=reason.strip(),
            judge_score=judge_score,
            judge_critique=judge_critique,
            scenario_id=scenario_id,
            category=str(scenario.get("category", "")),
        )
        
        self._entries.append(entry)
        logger.info(
            "Logged REJECTION: id=%s, category=%s, reason='%s'",
            entry.id, entry.category, reason[:50]
        )
        
        return entry
    
    def get_entries(
        self,
        action_filter: UserAction | None = None,
        category_filter: str | None = None,
        limit: int | None = None,
    ) -> list[FeedbackEntry]:
        """
        Retrieve feedback entries with optional filtering.
        
        Args:
            action_filter: Filter by user action type
            category_filter: Filter by scenario category
            limit: Maximum entries to return
            
        Returns:
            List of matching FeedbackEntry objects
        """
        entries = self._entries
        
        if action_filter:
            entries = [e for e in entries if e.user_action == action_filter.value]
        
        if category_filter:
            entries = [e for e in entries if e.category == category_filter]
        
        if limit:
            entries = entries[:limit]
        
        return entries
    
    def get_rejection_reasons(self, category: str | None = None) -> list[str]:
        """
        Get all rejection reasons, optionally filtered by category.
        
        Useful for building negative constraints in generation prompts.
        
        Args:
            category: Filter by scenario category
            
        Returns:
            List of rejection reason strings
        """
        entries = self.get_entries(action_filter=UserAction.REJECTED, category_filter=category)
        return [e.user_reason for e in entries if e.user_reason]
    
    def clear(self) -> None:
        """Clear all entries (useful for testing)."""
        self._entries = []


# Singleton instance for application-wide use
_feedback_logger: FeedbackLogger | None = None


def get_feedback_logger() -> FeedbackLogger:
    """Get the global FeedbackLogger instance."""
    global _feedback_logger
    if _feedback_logger is None:
        _feedback_logger = FeedbackLogger()
    return _feedback_logger


__all__ = [
    "FeedbackEntry",
    "FeedbackLogger",
    "UserAction",
    "get_feedback_logger",
]

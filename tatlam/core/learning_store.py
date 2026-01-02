"""
tatlam/core/learning_store.py - Smart Memory for RLHF Pipeline

This module implements the "Smart Memory" with two repositories:
- Hall of Fame: Successful scenarios for Few-Shot examples
- Graveyard: Rejected scenarios with reasons for negative constraints

Key Features:
- Persistent storage for learning data
- Query methods for prompt enhancement
- Pattern aggregation for common pitfalls
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HallOfFameEntry:
    """
    Entry in the Hall of Fame - a successful scenario.
    
    Used as Few-Shot examples in future generation prompts.
    """
    scenario_id: int
    scenario_data: dict[str, Any]
    category: str
    score: float
    approved_at: str = field(default_factory=lambda: datetime.now().isoformat())
    used_as_example_count: int = 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "scenario_id": self.scenario_id,
            "scenario_data": self.scenario_data,
            "category": self.category,
            "score": self.score,
            "approved_at": self.approved_at,
            "used_as_example_count": self.used_as_example_count,
        }


@dataclass
class GraveyardEntry:
    """
    Entry in the Graveyard - a rejected scenario.
    
    Used to build negative constraints and avoid common pitfalls.
    """
    scenario_id: int
    scenario_data: dict[str, Any]
    category: str
    rejection_reason: str
    judge_critique: str
    rejected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "scenario_id": self.scenario_id,
            "scenario_data": self.scenario_data,
            "category": self.category,
            "rejection_reason": self.rejection_reason,
            "judge_critique": self.judge_critique,
            "rejected_at": self.rejected_at,
        }


class LearningStore:
    """
    Manages the Hall of Fame and Graveyard for RLHF learning.
    
    This store enables the system to:
    1. Use approved scenarios as Few-Shot examples
    2. Learn from rejection patterns to avoid common mistakes
    3. Provide context-aware constraints during generation
    
    Usage:
        store = LearningStore()
        
        # Add successful scenario
        store.add_to_hall_of_fame(scenario, score=92.0, scenario_id=123)
        
        # Add rejected scenario
        store.add_to_graveyard(scenario, reason="Too expensive", scenario_id=456)
        
        # Get examples for generation prompt
        examples = store.get_positive_examples(category="suspicious_object")
        pitfalls = store.get_pitfalls_for_context({"category": "suspicious_object"})
    """
    
    def __init__(self):
        """Initialize the learning store."""
        self._hall_of_fame: list[HallOfFameEntry] = []
        self._graveyard: list[GraveyardEntry] = []
    
    # ==== Hall of Fame Methods ====
    
    def add_to_hall_of_fame(
        self,
        scenario: dict[str, Any],
        *,
        score: float,
        scenario_id: int | None = None,
    ) -> HallOfFameEntry:
        """
        Add a successful scenario to the Hall of Fame.
        
        Args:
            scenario: The approved scenario data
            score: Final quality score
            scenario_id: Database ID of the scenario
            
        Returns:
            The created HallOfFameEntry
        """
        entry = HallOfFameEntry(
            scenario_id=scenario_id or 0,
            scenario_data=scenario,
            category=str(scenario.get("category", "")),
            score=score,
        )
        
        self._hall_of_fame.append(entry)
        logger.info(
            "Added to Hall of Fame: category=%s, score=%.1f, id=%s",
            entry.category, score, scenario_id
        )
        
        return entry
    
    def get_positive_examples(
        self,
        category: str | None = None,
        limit: int = 3,
        min_score: float = 80.0,
    ) -> list[dict[str, Any]]:
        """
        Get high-quality examples for Few-Shot learning.
        
        Args:
            category: Filter by scenario category (None = all)
            limit: Maximum examples to return
            min_score: Minimum score threshold
            
        Returns:
            List of scenario dictionaries suitable for prompts
        """
        # Filter and sort by score (highest first)
        candidates = self._hall_of_fame
        
        if category:
            candidates = [e for e in candidates if e.category == category]
        
        candidates = [e for e in candidates if e.score >= min_score]
        candidates = sorted(candidates, key=lambda e: e.score, reverse=True)
        
        # Take top N and increment usage counter
        selected = candidates[:limit]
        for entry in selected:
            entry.used_as_example_count += 1
        
        return [e.scenario_data for e in selected]
    
    def get_hall_of_fame_stats(self) -> dict[str, Any]:
        """Get statistics about the Hall of Fame."""
        if not self._hall_of_fame:
            return {"total": 0, "by_category": {}, "average_score": 0}
        
        by_category = Counter(e.category for e in self._hall_of_fame)
        avg_score = sum(e.score for e in self._hall_of_fame) / len(self._hall_of_fame)
        
        return {
            "total": len(self._hall_of_fame),
            "by_category": dict(by_category),
            "average_score": avg_score,
        }
    
    # ==== Graveyard Methods ====
    
    def add_to_graveyard(
        self,
        scenario: dict[str, Any],
        *,
        reason: str,
        judge_critique: str = "",
        scenario_id: int | None = None,
    ) -> GraveyardEntry:
        """
        Add a rejected scenario to the Graveyard.
        
        Args:
            scenario: The rejected scenario data
            reason: User's rejection reason (mandatory)
            judge_critique: Judge's critique before user rejection
            scenario_id: Database ID of the scenario
            
        Returns:
            The created GraveyardEntry
            
        Raises:
            ValueError: If reason is empty
        """
        if not reason or not reason.strip():
            raise ValueError("Rejection reason is mandatory for Graveyard")
        
        entry = GraveyardEntry(
            scenario_id=scenario_id or 0,
            scenario_data=scenario,
            category=str(scenario.get("category", "")),
            rejection_reason=reason.strip(),
            judge_critique=judge_critique,
        )
        
        self._graveyard.append(entry)
        logger.info(
            "Added to Graveyard: category=%s, reason='%s', id=%s",
            entry.category, reason[:50], scenario_id
        )
        
        return entry
    
    def get_negative_patterns(
        self,
        category: str | None = None,
        limit: int = 10,
    ) -> list[tuple[str, int]]:
        """
        Get common rejection reasons with their frequency.
        
        Useful for building negative constraints in prompts.
        
        Args:
            category: Filter by scenario category (None = all)
            limit: Maximum patterns to return
            
        Returns:
            List of (reason, count) tuples sorted by frequency
        """
        entries = self._graveyard
        
        if category:
            entries = [e for e in entries if e.category == category]
        
        reasons = [e.rejection_reason for e in entries]
        counter = Counter(reasons)
        
        return counter.most_common(limit)
    
    def get_pitfalls_for_context(
        self,
        context: dict[str, Any],
        limit: int = 5,
    ) -> list[str]:
        """
        Get pitfalls relevant to a specific generation context.
        
        This is the key method for injecting learning into generation prompts.
        It analyzes the context (category, venue, etc.) and returns relevant
        rejection patterns to avoid.
        
        Args:
            context: Generation context with category, venue, etc.
            limit: Maximum pitfalls to return
            
        Returns:
            List of pitfall strings for use in prompts
        """
        category = context.get("category")
        
        # Get patterns specific to this category
        patterns = self.get_negative_patterns(category=category, limit=limit)
        
        # If not enough category-specific patterns, add general ones
        if len(patterns) < limit:
            general_patterns = self.get_negative_patterns(category=None, limit=limit - len(patterns))
            seen_reasons = {p[0] for p in patterns}
            for reason, count in general_patterns:
                if reason not in seen_reasons:
                    patterns.append((reason, count))
        
        return [reason for reason, _ in patterns[:limit]]
    
    def get_graveyard_entries(
        self,
        category: str | None = None,
        limit: int | None = None,
    ) -> list[GraveyardEntry]:
        """Get Graveyard entries with optional filtering."""
        entries = self._graveyard
        
        if category:
            entries = [e for e in entries if e.category == category]
        
        if limit:
            entries = entries[:limit]
        
        return entries
    
    def get_graveyard_stats(self) -> dict[str, Any]:
        """Get statistics about the Graveyard."""
        if not self._graveyard:
            return {"total": 0, "by_category": {}, "top_reasons": []}
        
        by_category = Counter(e.category for e in self._graveyard)
        top_reasons = self.get_negative_patterns(limit=5)
        
        return {
            "total": len(self._graveyard),
            "by_category": dict(by_category),
            "top_reasons": top_reasons,
        }
    
    # ==== Combined Methods ====
    
    def get_learning_context(
        self,
        category: str | None = None,
    ) -> dict[str, Any]:
        """
        Get complete learning context for prompt enhancement.
        
        Combines positive examples and negative patterns for a category.
        
        Args:
            category: Scenario category to focus on
            
        Returns:
            Dictionary with examples, pitfalls, and stats
        """
        return {
            "positive_examples": self.get_positive_examples(category=category),
            "negative_patterns": self.get_pitfalls_for_context({"category": category}),
            "hall_of_fame_stats": self.get_hall_of_fame_stats(),
            "graveyard_stats": self.get_graveyard_stats(),
        }
    
    def clear(self) -> None:
        """Clear all entries (useful for testing)."""
        self._hall_of_fame = []
        self._graveyard = []


# Singleton instance for application-wide use
_learning_store: LearningStore | None = None


def get_learning_store() -> LearningStore:
    """Get the global LearningStore instance."""
    global _learning_store
    if _learning_store is None:
        _learning_store = LearningStore()
    return _learning_store


__all__ = [
    "GraveyardEntry",
    "HallOfFameEntry",
    "LearningStore",
    "get_learning_store",
]

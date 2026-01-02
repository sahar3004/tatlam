"""SQLAlchemy 2.0 ORM Models for Tatlam.

This module defines the declarative ORM models using SQLAlchemy 2.0's
modern type-annotated syntax. The Scenario model mirrors the existing
sqlite3 schema exactly to ensure backward compatibility.

Usage:
    from tatlam.infra.models import Base, Scenario

    # Create tables
    Base.metadata.create_all(engine)

    # Query
    session.scalars(select(Scenario)).all()

    # Convert to dict for existing code
    scenario.to_dict()
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Scenario(Base):
    """ORM model for the scenarios table.

    This model maps directly to the existing sqlite3 schema, maintaining
    full backward compatibility with the dictionary-based API.

    All JSON fields (steps, required_response, etc.) are stored as TEXT
    in SQLite but handled as Python lists/dicts through the to_dict() method.
    """

    __tablename__ = "scenarios"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identifiers
    bundle_id: Mapped[str] = mapped_column(Text, default="", nullable=False)
    external_id: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Core fields
    title: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(Text, nullable=False, index=True)  # Index for filtering

    # Risk assessment
    threat_level: Mapped[str] = mapped_column(
        Text, default="", nullable=False, index=True
    )  # Index for prioritization
    likelihood: Mapped[str] = mapped_column(Text, default="", nullable=False)
    complexity: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Context
    location: Mapped[str] = mapped_column(Text, default="", nullable=False)
    background: Mapped[str] = mapped_column(Text, default="", nullable=False)
    operational_background: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # JSON-serialized list fields (stored as TEXT in SQLite)
    steps: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    required_response: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    debrief_points: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    comms: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    decision_points: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    escalation_conditions: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    lessons_learned: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    variations: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    validation: Mapped[str] = mapped_column(Text, default="[]", nullable=False)

    # Media and equipment
    media_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    mask_usage: Mapped[str | None] = mapped_column(Text, nullable=True)
    cctv_usage: Mapped[str] = mapped_column(Text, default="", nullable=False)
    authority_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # End states
    end_state_success: Mapped[str] = mapped_column(Text, default="", nullable=False)
    end_state_failure: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Metadata
    owner: Mapped[str] = mapped_column(Text, default="web", nullable=False)
    approved_by: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(
        Text, default="pending", nullable=False, index=True
    )  # Index for filtering
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        Text,
        default=lambda: datetime.now().isoformat(),
        nullable=False,
        index=True,  # Index for sorting
    )

    # JSON fields that need parsing in to_dict()
    _JSON_FIELDS = [
        "steps",
        "required_response",
        "debrief_points",
        "comms",
        "decision_points",
        "escalation_conditions",
        "lessons_learned",
        "variations",
        "validation",
    ]

    def _parse_json_field(self, val: str | None) -> list[Any] | dict[str, Any]:
        """Parse a JSON string field to Python object."""
        if val is None:
            return []
        if isinstance(val, (list, dict)):
            return val
        if isinstance(val, str) and not val.strip():
            return []
        try:
            loaded = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return []
        if isinstance(loaded, (list, dict)):
            return loaded
        return []

    def to_dict(self) -> dict[str, Any]:
        """Convert the ORM model to a dictionary.

        This method returns a dictionary structure identical to what the
        old sqlite3.Row dictionary would return, ensuring full backward
        compatibility with existing code in render_cards.py and elsewhere.

        JSON fields are automatically parsed from their TEXT storage format.

        Returns:
            dict[str, Any]: Dictionary with all scenario fields.
        """
        result: dict[str, Any] = {
            "id": self.id,
            "bundle_id": self.bundle_id,
            "external_id": self.external_id,
            "title": self.title,
            "category": self.category,
            "threat_level": self.threat_level,
            "likelihood": self.likelihood,
            "complexity": self.complexity,
            "location": self.location,
            "background": self.background,
            "operational_background": self.operational_background,
            "media_link": self.media_link,
            "mask_usage": self.mask_usage,
            "cctv_usage": self.cctv_usage,
            "authority_notes": self.authority_notes,
            "end_state_success": self.end_state_success,
            "end_state_failure": self.end_state_failure,
            "owner": self.owner,
            "approved_by": self.approved_by,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
        }

        # Parse JSON fields
        for field in self._JSON_FIELDS:
            result[field] = self._parse_json_field(getattr(self, field, "[]"))

        return result

    def __repr__(self) -> str:
        return f"<Scenario(id={self.id}, title='{self.title[:30]}...')>"


class ScenarioEmbedding(Base):
    """ORM model for scenario embeddings."""

    __tablename__ = "embeddings"  # Using default name from sqlite usage if possible, usually 'scenario_embeddings' or 'embeddings'

    # Primary key should wrap the unique title or just be id
    # Based on save_embedding: INSERT OR REPLACE INTO {EMB_TABLE} (title, vector_json)
    # So title is likely PK or Unique
    title: Mapped[str] = mapped_column(Text, primary_key=True)
    vector_json: Mapped[str] = mapped_column(Text, nullable=False)


# ==== RLHF Learning Tables ====


class HallOfFame(Base):
    """
    Hall of Fame: Approved scenarios used as Few-Shot examples.
    
    Part of the Iron Judge RLHF learning mechanism.
    """
    __tablename__ = "hall_of_fame"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    score: Mapped[float] = mapped_column(nullable=False)
    scenario_data_json: Mapped[str] = mapped_column(Text, nullable=False)  # Full scenario as JSON
    approved_at: Mapped[str] = mapped_column(
        Text,
        default=lambda: datetime.now().isoformat(),
        nullable=False,
        index=True,
    )
    used_as_example_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "category": self.category,
            "score": self.score,
            "scenario_data": json.loads(self.scenario_data_json) if self.scenario_data_json else {},
            "approved_at": self.approved_at,
            "used_as_example_count": self.used_as_example_count,
        }


class Graveyard(Base):
    """
    Graveyard: Rejected scenarios with reasons for negative learning.
    
    Part of the Iron Judge RLHF learning mechanism.
    """
    __tablename__ = "graveyard"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    category: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    rejection_reason: Mapped[str] = mapped_column(Text, nullable=False)
    judge_critique: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scenario_data_json: Mapped[str] = mapped_column(Text, nullable=False)  # Full scenario as JSON
    rejected_at: Mapped[str] = mapped_column(
        Text,
        default=lambda: datetime.now().isoformat(),
        nullable=False,
        index=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "category": self.category,
            "rejection_reason": self.rejection_reason,
            "judge_critique": self.judge_critique,
            "scenario_data": json.loads(self.scenario_data_json) if self.scenario_data_json else {},
            "rejected_at": self.rejected_at,
        }


class FeedbackLog(Base):
    """
    Feedback Log: Complete audit trail of user feedback.
    
    Captures all user interactions (approve/revise/reject) for analysis.
    """
    __tablename__ = "feedback_log"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # UUID
    input_context_json: Mapped[str] = mapped_column(Text, nullable=False)
    generated_output_json: Mapped[str] = mapped_column(Text, nullable=False)
    user_action: Mapped[str] = mapped_column(Text, nullable=False, index=True)  # approved/revised/rejected
    user_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    judge_critique: Mapped[str] = mapped_column(Text, default="", nullable=False)
    scenario_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    category: Mapped[str] = mapped_column(Text, default="", nullable=False, index=True)
    timestamp: Mapped[str] = mapped_column(
        Text,
        default=lambda: datetime.now().isoformat(),
        nullable=False,
        index=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "input_context": json.loads(self.input_context_json) if self.input_context_json else {},
            "generated_output": json.loads(self.generated_output_json) if self.generated_output_json else {},
            "user_action": self.user_action,
            "user_reason": self.user_reason,
            "revision_notes": self.revision_notes,
            "judge_score": self.judge_score,
            "judge_critique": self.judge_critique,
            "scenario_id": self.scenario_id,
            "category": self.category,
            "timestamp": self.timestamp,
        }


__all__ = [
    "Base",
    "Scenario",
    "ScenarioEmbedding",
    "HallOfFame",
    "Graveyard",
    "FeedbackLog",
]


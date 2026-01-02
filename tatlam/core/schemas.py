"""
Data Transfer Objects (DTOs) for Tatlam using Pydantic.

This module provides strict, type-safe schemas for passing data between
the Repository, Brain, and UI layers.
"""

from __future__ import annotations

from typing import Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ScenarioDTO(BaseModel):
    """
    Data Transfer Object for a Scenario.
    
    Ensures type safety and validation for scenario data flowing through the system.
    """
    id: Optional[int] = None
    bundle_id: str = ""
    external_id: str = ""
    title: str
    category: str
    
    # Risk Assessment
    threat_level: str = ""
    likelihood: str = ""
    complexity: str = ""
    
    # Context
    location: str = ""
    background: str = ""
    operational_background: str = ""
    
    # JSON Fields (Strictly typed lists)
    steps: List[Any] = Field(default_factory=list)
    required_response: List[Any] = Field(default_factory=list)
    debrief_points: List[Any] = Field(default_factory=list)
    comms: List[Any] = Field(default_factory=list)
    decision_points: List[Any] = Field(default_factory=list)
    escalation_conditions: List[Any] = Field(default_factory=list)
    lessons_learned: List[Any] = Field(default_factory=list)
    variations: List[Any] = Field(default_factory=list)
    validation: List[Any] = Field(default_factory=list)
    
    # Media & Equipment
    media_link: Optional[str] = None
    mask_usage: Optional[str] = None
    cctv_usage: str = ""
    authority_notes: str = ""
    
    # End States
    end_state_success: str = ""
    end_state_failure: str = ""
    
    # Metadata
    owner: str = "web"
    approved_by: str = ""
    status: str = "pending"
    rejection_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        from_attributes = True
        populate_by_name = True

    @field_validator("steps", "required_response", mode="before")
    def parse_empty_strings(cls, v: Any) -> Any:
        """Handle empty strings or nulls for list fields."""
        if v is None:
            return []
        if isinstance(v, str) and not v.strip():
            return []
        return v

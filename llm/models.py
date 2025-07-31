"""
LLM-specific Pydantic models and schemas.
"""

from typing import Any

from pydantic import BaseModel, Field

from models.memory import EventType


class EventClassification(BaseModel):
    """Event classification result from LLM."""

    event_type: EventType = Field(description="Classified event type")
    importance_score: float = Field(
        ge=0.0, le=1.0, description="Importance score (0.0-1.0)"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Extracted event data"
    )
    reasoning: str = Field(description="LLM reasoning for classification")

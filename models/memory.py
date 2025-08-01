"""
Memory-related Pydantic models for Short-term and Long-term memory system.
Designed to be domain-agnostic and suitable for multi-tenant applications.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Generic event types for business-agnostic categorization."""

    INQUIRY = "INQUIRY"
    FEEDBACK = "FEEDBACK"
    REQUEST = "REQUEST"
    COMPLAINT = "COMPLAINT"
    GENERIC_EVENT = "GENERIC_EVENT"
    TRANSACTION = "TRANSACTION"
    SUPPORT = "SUPPORT"
    INFORMATION = "INFORMATION"


class MemoryEvent(BaseModel):
    """Individual event stored in memory."""

    event_type: EventType = Field(..., description="Type of event")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data (flexible)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Event timestamp"
    )
    importance_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Event importance (0.0 - 1.0)"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class ShortTermMemory(BaseModel):
    """Short-term memory structure stored in Redis."""

    tenant_id: str = Field(..., description="Tenant/store identifier")
    user_id: str = Field(..., description="User identifier")
    session_id: str = Field(..., description="Current session identifier")

    # Conversation context
    history: list[dict[str, str]] = Field(
        default_factory=list, description="Recent conversation history"
    )
    summary: str = Field("", description="Context summary from LLM")

    # Last detected intent
    last_intent: str | None = Field(None, description="Last detected intent")

    # Session variables (flexible for any business)
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Session-specific variables"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="SM creation time"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update time"
    )
    expires_at: datetime | None = Field(None, description="Expiration time")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "tenant_id": "store_001",
                "user_id": "user123",
                "session_id": "sess_20250730_001",
                "history": [
                    {"role": "user", "message": "สวัสดีครับ"},
                    {"role": "bot", "message": "สวัสดีค่ะ มีอะไรให้ช่วยไหมคะ"},
                ],
                "summary": "User greeted, bot responded politely",
                "last_intent": "greeting",
                "variables": {"preferred_language": "th", "current_topic": "general"},
            }
        }


class LongTermMemory(BaseModel):
    """Long-term memory structure stored in JSON files."""

    tenant_id: str = Field(..., description="Tenant/store identifier")
    user_id: str = Field(..., description="User identifier")

    # Event history
    events: list[MemoryEvent] = Field(
        default_factory=list, description="Important events history"
    )

    # User attributes (persistent profile data)
    attributes: dict[str, Any] = Field(
        default_factory=dict, description="User attributes and preferences"
    )

    # Historical context
    history_summary: str = Field(
        "", description="Summary of user's historical interactions"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="LM creation time"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last update time"
    )

    def add_event(self, event: MemoryEvent) -> None:
        """Add a new event to the memory."""
        self.events.append(event)
        self.updated_at = datetime.now(UTC)

    def get_recent_events(self, limit: int = 10) -> list[MemoryEvent]:
        """Get most recent events."""
        return sorted(self.events, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_important_events(self, min_score: float = 0.7) -> list[MemoryEvent]:
        """Get events with high importance score."""
        return [event for event in self.events if event.importance_score >= min_score]

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "tenant_id": "store_001",
                "user_id": "user123",
                "events": [
                    {
                        "event_type": "INQUIRY",
                        "payload": {"question": "ราคาสินค้า", "category": "pricing"},
                        "timestamp": "2025-07-30T10:30:00Z",
                        "importance_score": 0.8,
                    }
                ],
                "attributes": {
                    "preferred_language": "th",
                    "segment": "regular_customer",
                    "timezone": "Asia/Bangkok",
                },
                "history_summary": "Customer frequently asks about pricing and promotions",
            }
        }


class MemoryConfig(BaseModel):
    """Memory system configuration."""

    # Redis settings for SM
    redis_url: str = Field(..., description="Redis connection URL")
    sm_ttl: int = Field(1800, description="SM TTL in seconds (30 minutes)")

    # JSON storage settings for LM
    lm_base_path: str = Field(
        "data/longterm", description="Base path for LM JSON files"
    )
    max_events_per_user: int = Field(1000, description="Max events to keep per user")
    event_retention_days: int = Field(365, description="Event retention period in days")

    # Event processing
    importance_threshold: float = Field(
        0.5, ge=0.0, le=1.0, description="Minimum importance to save to LM"
    )
    summary_trigger_events: int = Field(
        50, description="Number of events to trigger summary update"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "redis_url": "redis://localhost:6379/0",
                "sm_ttl": 1800,
                "lm_base_path": "data/longterm",
                "max_events_per_user": 1000,
                "importance_threshold": 0.5,
            }
        }

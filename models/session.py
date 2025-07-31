"""
Session and context-related Pydantic models.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionState(str, Enum):
    """Session states."""

    ACTIVE = "active"
    IDLE = "idle"
    ENDED = "ended"
    EXPIRED = "expired"


class SessionContext(BaseModel):
    """Session context data."""

    current_topic: str | None = Field(None, description="Current conversation topic")
    intent: str | None = Field(None, description="Detected user intent")
    entities: dict[str, Any] = Field(
        default_factory=dict, description="Extracted entities"
    )
    variables: dict[str, Any] = Field(
        default_factory=dict, description="Session variables"
    )

    # Conversation flow
    current_step: str | None = Field(None, description="Current conversation step")
    flow_data: dict[str, Any] = Field(
        default_factory=dict, description="Flow-specific data"
    )

    # User preferences within session
    language: str = Field("en", description="Session language")
    timezone: str = Field("UTC", description="Session timezone")


class Session(BaseModel):
    """User session representation."""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="Associated user ID")
    platform: str = Field(..., description="Platform where session is active")

    # Session metadata
    state: SessionState = Field(
        SessionState.ACTIVE, description="Current session state"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Session creation time"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last session update"
    )
    expires_at: datetime | None = Field(None, description="Session expiration time")

    # Context and data
    context: SessionContext = Field(
        default_factory=lambda: SessionContext(
            current_topic=None,
            intent=None,
            current_step=None,
            language="en",
            timezone="UTC",
        ),
        description="Session context",
    )
    message_history: list[str] = Field(
        default_factory=list, description="Recent message IDs"
    )

    # Metadata
    total_messages: int = Field(0, description="Total messages in this session")
    last_activity: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last activity timestamp"
    )

    # Memory integration fields
    has_memory_context: bool = Field(
        False, description="Whether session has loaded memory context"
    )
    memory_summary: str = Field("", description="Brief summary from memory system")
    tenant_id: str | None = Field(
        None, description="Tenant/store identifier for memory integration"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "session_id": "sess_line_U1234_20240101_120000",
                "user_id": "user_line_U1234567890abcdef",
                "platform": "line",
                "state": "active",
                "context": {
                    "current_topic": "weather",
                    "intent": "get_weather",
                    "entities": {"location": "Bangkok"},
                    "language": "en",
                    "timezone": "Asia/Bangkok",
                },
                "total_messages": 5,
            }
        }

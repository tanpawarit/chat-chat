"""
User-related Pydantic models.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .platform import PlatformType


class UserProfile(BaseModel):
    """User profile information from platform."""

    display_name: str | None = Field(None, description="User's display name")
    avatar_url: str | None = Field(None, description="User's profile picture URL")
    language: str | None = Field(None, description="User's preferred language")
    timezone: str | None = Field(None, description="User's timezone")
    status_message: str | None = Field(None, description="User's status message")


class User(BaseModel):
    """Normalized user representation across platforms."""

    user_id: str = Field(..., description="Unique user identifier")
    platform: PlatformType = Field(..., description="User's platform")
    platform_user_id: str = Field(..., description="Platform-specific user ID")

    # Profile information
    profile: UserProfile | None = Field(None, description="User profile data")

    # Metadata
    first_seen: datetime = Field(
        default_factory=datetime.utcnow, description="First interaction timestamp"
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="Last interaction timestamp"
    )
    message_count: int = Field(0, description="Total messages from this user")

    # Platform-specific data
    platform_data: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific user data"
    )

    # User preferences
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="User preferences and settings"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "user_id": "user_line_U1234567890abcdef",
                "platform": "line",
                "platform_user_id": "U1234567890abcdef1234567890abcdef",
                "profile": {
                    "display_name": "John Doe",
                    "avatar_url": "https://profile.line-scdn.net/avatar.jpg",
                    "language": "en",
                    "timezone": "Asia/Bangkok",
                },
                "message_count": 42,
                "preferences": {"notifications": True, "language": "en"},
            }
        }

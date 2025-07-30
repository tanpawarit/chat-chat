"""
Customer-related Pydantic models for multi-store support.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from models.platform import PlatformType
from models.user import UserProfile


class Customer(BaseModel):
    """Customer model representing a user in a specific store."""

    customer_id: str = Field(..., description="Unique customer identifier")
    store_id: str = Field(..., description="Store this customer belongs to")

    # Platform information
    platform: PlatformType = Field(..., description="Platform this customer uses")
    platform_user_id: str = Field(..., description="Platform-specific user ID")

    # Profile information
    profile: UserProfile | None = Field(None, description="Customer profile data")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When customer was first created"
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="Last interaction timestamp"
    )

    # Statistics
    message_count: int = Field(0, description="Total messages from this customer")

    # Customer-specific data
    preferences: dict[str, Any] = Field(
        default_factory=dict, description="Customer preferences and settings"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional customer metadata"
    )

    @classmethod
    def generate_customer_id(
        cls, store_id: str, platform: str, platform_user_id: str
    ) -> str:
        """
        Generate a unique customer ID.

        Args:
            store_id: Store identifier
            platform: Platform name
            platform_user_id: Platform-specific user ID

        Returns:
            Unique customer ID in format: {store_id}_{platform}_{platform_user_id}
        """
        return f"{store_id}_{platform}_{platform_user_id}"

    def increment_message_count(self) -> None:
        """Increment the message count and update last_seen timestamp."""
        self.message_count += 1
        self.last_seen = datetime.utcnow()

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "customer_id": "store_001_line_U1234567890abcdef",
                "store_id": "store_001",
                "platform": "line",
                "platform_user_id": "U1234567890abcdef1234567890abcdef",
                "profile": {
                    "display_name": "John Doe",
                    "avatar_url": "https://profile.line-scdn.net/avatar.jpg",
                    "language": "th",
                    "timezone": "Asia/Bangkok",
                },
                "message_count": 15,
                "preferences": {"language": "th", "notifications": True},
                "metadata": {"first_platform": "line", "signup_source": "qr_code"},
            }
        }


class CustomerStats(BaseModel):
    """Customer statistics for a store."""

    store_id: str = Field(..., description="Store identifier")
    total_customers: int = Field(0, description="Total number of customers")
    active_customers: int = Field(
        0, description="Active customers (messaged in last 30 days)"
    )
    new_customers_today: int = Field(0, description="New customers added today")
    platform_breakdown: dict[str, int] = Field(
        default_factory=dict, description="Customer count by platform"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "store_id": "store_001",
                "total_customers": 1250,
                "active_customers": 890,
                "new_customers_today": 15,
                "platform_breakdown": {"line": 1100, "facebook": 150},
            }
        }

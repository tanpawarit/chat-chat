"""
Platform-specific models and configurations.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Supported platform types."""

    LINE = "line"
    FACEBOOK = "facebook"
    WEB = "web"
    TELEGRAM = "telegram"


class AdapterCapabilities(BaseModel):
    """Capabilities supported by a platform adapter."""

    supports_text: bool = True
    supports_images: bool = True
    supports_video: bool = False
    supports_audio: bool = False
    supports_files: bool = False
    supports_location: bool = False
    supports_stickers: bool = False
    supports_quick_replies: bool = False
    supports_rich_menus: bool = False
    max_text_length: int | None = None
    max_file_size: int | None = None


class AdapterConfig(BaseModel):
    """Configuration for a platform adapter."""

    platform: PlatformType = Field(..., description="Platform type")
    enabled: bool = Field(True, description="Whether the adapter is enabled")
    webhook_path: str = Field(..., description="Webhook endpoint path")

    # Authentication
    access_token: str | None = Field(None, description="Platform access token")
    secret_key: str | None = Field(None, description="Platform secret key")
    verify_token: str | None = Field(None, description="Webhook verification token")

    # Configuration
    capabilities: AdapterCapabilities = Field(default=AdapterCapabilities())
    settings: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific settings"
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "ADAPTER_"


class LineConfig(AdapterConfig):
    """LINE-specific adapter configuration."""

    platform: Literal[PlatformType.LINE] = Field(default=PlatformType.LINE)
    webhook_path: str = Field(default="/webhook/line")

    # LINE-specific fields
    channel_access_token: str = Field(..., description="LINE Channel Access Token")
    channel_secret: str = Field(..., description="LINE Channel Secret")

    def __init__(self, **data):
        super().__init__(**data)
        # Set LINE-specific capabilities
        self.capabilities = AdapterCapabilities(
            supports_text=True,
            supports_images=True,
            supports_video=True,
            supports_audio=True,
            supports_files=True,
            supports_location=True,
            supports_stickers=True,
            supports_quick_replies=True,
            supports_rich_menus=True,
            max_text_length=5000,
            max_file_size=10 * 1024 * 1024,  # 10MB
        )


class WebhookPayload(BaseModel):
    """Base webhook payload structure."""

    platform: PlatformType = Field(..., description="Source platform")
    timestamp: str = Field(..., description="Webhook timestamp")
    events: list[dict[str, Any]] = Field(..., description="Platform events")
    raw_payload: dict[str, Any] = Field(..., description="Complete webhook payload")


class LineWebhookPayload(WebhookPayload):
    """LINE-specific webhook payload."""

    platform: Literal[PlatformType.LINE] = Field(default=PlatformType.LINE)
    destination: str | None = Field(None, description="LINE destination ID")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "platform": "line",
                "timestamp": "2024-01-01T00:00:00Z",
                "destination": "U1234567890abcdef1234567890abcdef",
                "events": [
                    {
                        "type": "message",
                        "message": {"type": "text", "text": "Hello, World!"},
                        "source": {
                            "type": "user",
                            "userId": "U1234567890abcdef1234567890abcdef",
                        },
                        "replyToken": "reply-token-12345",
                    }
                ],
                "raw_payload": {},
            }
        }

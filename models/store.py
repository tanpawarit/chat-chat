"""
Store-related Pydantic models for multi-store support.
"""

from typing import Any

from pydantic import BaseModel, Field

from models.platform import AdapterCapabilities


class StorePlatformConfig(BaseModel):
    """Platform configuration for a specific store."""

    enabled: bool = Field(
        ..., description="Whether this platform is enabled for the store"
    )
    channel_secret: str | None = Field(None, description="Platform channel secret")
    channel_access_token: str | None = Field(None, description="Platform access token")
    capabilities: AdapterCapabilities | None = Field(
        None, description="Platform capabilities"
    )

    # Platform-specific configuration
    platform_data: dict[str, Any] = Field(
        default_factory=dict, description="Platform-specific configuration data"
    )


class Store(BaseModel):
    """Store model with multi-platform support."""

    store_id: str = Field(..., description="Unique store identifier")
    name: str = Field(..., description="Store display name")
    active: bool = Field(True, description="Whether the store is active")

    # Platform configurations
    platforms: dict[str, StorePlatformConfig] = Field(
        default_factory=dict,
        description="Platform configurations (line, facebook, etc.)",
    )

    # Store metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Store metadata and settings"
    )

    def get_platform_config(self, platform: str) -> StorePlatformConfig | None:
        """
        Get platform configuration for this store.

        Args:
            platform: Platform name (line, facebook, etc.)

        Returns:
            StorePlatformConfig if found and enabled, None otherwise
        """
        config = self.platforms.get(platform)
        if config and config.enabled:
            return config
        return None

    def is_platform_enabled(self, platform: str) -> bool:
        """
        Check if a platform is enabled for this store.

        Args:
            platform: Platform name

        Returns:
            True if platform is enabled, False otherwise
        """
        config = self.platforms.get(platform)
        return config is not None and config.enabled

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "store_id": "store_001",
                "name": "ร้านกาแฟเก๋ไก๋",
                "active": True,
                "platforms": {
                    "line": {
                        "enabled": True,
                        "channel_secret": "your_channel_secret",
                        "channel_access_token": "your_access_token",
                        "capabilities": {
                            "supports_text": True,
                            "supports_images": True,
                            "max_text_length": 5000,
                            "max_file_size": 10485760,
                        },
                    },
                    "facebook": {"enabled": False},
                },
                "metadata": {
                    "description": "Coffee shop in Bangkok",
                    "timezone": "Asia/Bangkok",
                },
            }
        }

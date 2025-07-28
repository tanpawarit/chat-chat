"""
Abstract base class for platform adapters.
"""

from abc import ABC, abstractmethod
from typing import Any

from models.message import IncomingMessage, OutgoingMessage
from models.platform import AdapterConfig, PlatformType
from models.user import User


class PlatformAdapter(ABC):
    """Abstract base class for all platform adapters."""

    def __init__(self, config: AdapterConfig):
        """Initialize the adapter with configuration."""
        self.config = config
        self.platform = config.platform

    @property
    @abstractmethod
    def platform_type(self) -> PlatformType:
        """Return the platform type this adapter handles."""
        pass

    @abstractmethod
    async def parse_incoming(
        self, webhook_data: dict[str, Any]
    ) -> IncomingMessage | None:
        """
        Parse incoming webhook data from platform into normalized message.

        Args:
            webhook_data: Raw webhook data from platform

        Returns:
            Normalized IncomingMessage or None if parsing fails
        """
        pass

    @abstractmethod
    async def format_outgoing(
        self, message: OutgoingMessage, user: User
    ) -> dict[str, Any]:
        """
        Format normalized outgoing message into platform-specific format.

        Args:
            message: Normalized outgoing message
            user: Target user information

        Returns:
            Platform-specific message format
        """
        pass

    @abstractmethod
    async def send_message(self, formatted_message: dict[str, Any], user: User) -> bool:
        """
        Send formatted message to platform.

        Args:
            formatted_message: Platform-specific formatted message
            user: Target user

        Returns:
            True if message was sent successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_user_profile(self, platform_user_id: str) -> User | None:
        """
        Retrieve user profile from platform.

        Args:
            platform_user_id: Platform-specific user ID

        Returns:
            User object with profile data or None if not found
        """
        pass

    @abstractmethod
    async def validate_webhook(self, headers: dict[str, str], body: bytes) -> bool:
        """
        Validate incoming webhook request.

        Args:
            headers: HTTP headers from webhook request
            body: Raw request body

        Returns:
            True if webhook is valid, False otherwise
        """
        pass

    def generate_user_id(self, platform_user_id: str) -> str:
        """
        Generate normalized user ID from platform-specific user ID.

        Args:
            platform_user_id: Platform-specific user ID

        Returns:
            Normalized user ID in format: user_{platform}_{platform_user_id}
        """
        return f"user_{self.platform.value}_{platform_user_id}"

    def generate_message_id(self, platform_message_id: str) -> str:
        """
        Generate normalized message ID from platform-specific message ID.

        Args:
            platform_message_id: Platform-specific message ID

        Returns:
            Normalized message ID in format: msg_{platform}_{platform_message_id}
        """
        return f"msg_{self.platform.value}_{platform_message_id}"

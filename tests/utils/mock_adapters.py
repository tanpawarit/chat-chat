"""
Mock adapters for testing.
"""

from typing import Any
from unittest.mock import AsyncMock, Mock

from adapters.base.platform_base import PlatformAdapter
from models.message import IncomingMessage, MessageType, OutgoingMessage
from models.platform import PlatformType
from models.user import User, UserProfile


class MockLineAdapter(PlatformAdapter):
    """Mock LINE adapter for testing."""

    def __init__(self, store_config: dict[str, Any]):
        super().__init__(store_config)
        self.platform = PlatformType.LINE
        self._mock_user_profiles = {}
        self._sent_messages = []

    async def parse_incoming(
        self, webhook_data: dict[str, Any]
    ) -> IncomingMessage | None:
        """Mock parse incoming message."""
        if not webhook_data.get("events"):
            return None

        event = webhook_data["events"][0]
        if event.get("type") != "message":
            return None

        message = event.get("message", {})
        source = event.get("source", {})

        # Create mock user
        user = User(
            user_id=source.get("userId", "mock_user"),
            platform=PlatformType.LINE,
            profile=UserProfile(
                display_name="Mock User",
                picture_url="https://example.com/avatar.jpg",
                language="th",
            ),
        )

        return IncomingMessage(
            message_id=message.get("id", "mock_msg"),
            message_type=MessageType.TEXT
            if message.get("type") == "text"
            else MessageType.OTHER,
            content=message.get("text", ""),
            user=user,
            timestamp="2024-01-15T10:00:00Z",
            platform_data={"replyToken": event.get("replyToken"), "source": source},
        )

    def format_outgoing(self, message: OutgoingMessage) -> dict[str, Any]:
        """Mock format outgoing message."""
        if message.message_type == MessageType.TEXT:
            return {"type": "text", "text": message.content}
        return {"type": "text", "text": "Unsupported message type"}

    async def send_message(
        self, message: OutgoingMessage, platform_data: dict[str, Any]
    ) -> bool:
        """Mock send message."""
        formatted_message = self.format_outgoing(message)
        self._sent_messages.append(
            {"message": formatted_message, "platform_data": platform_data}
        )
        return True

    async def get_user_profile(self, user_id: str) -> UserProfile | None:
        """Mock get user profile."""
        if user_id in self._mock_user_profiles:
            return self._mock_user_profiles[user_id]

        return UserProfile(
            display_name=f"Mock User {user_id}",
            picture_url="https://example.com/avatar.jpg",
            language="th",
        )

    def set_mock_user_profile(self, user_id: str, profile: UserProfile):
        """Set mock user profile for testing."""
        self._mock_user_profiles[user_id] = profile

    def get_sent_messages(self) -> list:
        """Get list of sent messages for testing."""
        return self._sent_messages.copy()

    def clear_sent_messages(self):
        """Clear sent messages list."""
        self._sent_messages.clear()


class MockPlatformAdapterFactory:
    """Factory for creating mock platform adapters."""

    @staticmethod
    def create_line_adapter(
        store_config: dict[str, Any] | None = None,
    ) -> MockLineAdapter:
        """Create mock LINE adapter."""
        if store_config is None:
            store_config = {
                "store_id": "test_store",
                "platform": "line",
                "credentials": {
                    "channel_access_token": "mock_token",
                    "channel_secret": "mock_secret",
                },
            }
        return MockLineAdapter(store_config)

    @staticmethod
    def create_adapter_with_responses(
        platform: PlatformType = PlatformType.LINE, responses: list | None = None
    ) -> Mock:
        """Create mock adapter with predefined responses."""
        mock_adapter = Mock()
        mock_adapter.platform = platform

        if responses:
            mock_adapter.parse_incoming = AsyncMock(side_effect=responses)
        else:
            mock_adapter.parse_incoming = AsyncMock(return_value=None)

        mock_adapter.format_outgoing = Mock(
            return_value={"type": "text", "text": "Mock response"}
        )
        mock_adapter.send_message = AsyncMock(return_value=True)
        mock_adapter.get_user_profile = AsyncMock(
            return_value=UserProfile(
                display_name="Mock User",
                picture_url="https://example.com/avatar.jpg",
                language="th",
            )
        )

        return mock_adapter

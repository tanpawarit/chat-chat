"""
Test helper functions and utilities.
"""
import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

from models.message import IncomingMessage, MessageType
from models.platform import PlatformType
from models.user import User, UserProfile


class TestHelpers:
    """Helper functions for testing."""

    @staticmethod
    def load_fixture(filename: str) -> dict[str, Any]:
        """Load test fixture from JSON file."""
        fixture_path = Path(__file__).parent.parent / "fixtures" / filename
        with open(fixture_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def create_test_user(
        user_id: str = "test_user",
        platform: PlatformType = PlatformType.LINE,
        display_name: str = "Test User"
    ) -> User:
        """Create a test user with default values."""
        return User(
            user_id=user_id,
            platform=platform,
            profile=UserProfile(
                display_name=display_name,
                picture_url="https://example.com/avatar.jpg",
                language="th"
            )
        )

    @staticmethod
    def create_test_message(
        content: str = "Test message",
        message_type: MessageType = MessageType.TEXT,
        user: User | None = None
    ) -> IncomingMessage:
        """Create a test incoming message."""
        if user is None:
            user = TestHelpers.create_test_user()

        return IncomingMessage(
            message_id="test_msg_123",
            message_type=message_type,
            content=content,
            user=user,
            timestamp="2024-01-15T10:00:00Z",
            platform_data={}
        )

    @staticmethod
    def assert_message_equal(msg1: IncomingMessage, msg2: IncomingMessage):
        """Assert two messages are equal."""
        assert msg1.message_id == msg2.message_id
        assert msg1.message_type == msg2.message_type
        assert msg1.content == msg2.content
        assert msg1.user.user_id == msg2.user.user_id
        assert msg1.timestamp == msg2.timestamp

    @staticmethod
    def mock_async_response(return_value: Any = None, side_effect: Any = None):
        """Create a mock async function."""
        mock = AsyncMock()
        if return_value is not None:
            mock.return_value = return_value
        if side_effect is not None:
            mock.side_effect = side_effect
        return mock

    @staticmethod
    def run_async_test(coro):
        """Run async test function."""
        return asyncio.get_event_loop().run_until_complete(coro)


class MockFactory:
    """Factory for creating mock objects."""

    @staticmethod
    def create_mock_adapter(platform: PlatformType = PlatformType.LINE):
        """Create a mock platform adapter."""
        mock_adapter = Mock()
        mock_adapter.platform = platform
        mock_adapter.parse_incoming = AsyncMock()
        mock_adapter.format_outgoing = Mock()
        mock_adapter.send_message = AsyncMock()
        mock_adapter.get_user_profile = AsyncMock()
        return mock_adapter

    @staticmethod
    def create_mock_redis():
        """Create a mock Redis client."""
        mock_redis = Mock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.exists = AsyncMock(return_value=False)
        mock_redis.hget = AsyncMock(return_value=None)
        mock_redis.hset = AsyncMock(return_value=True)
        mock_redis.expire = AsyncMock(return_value=True)
        return mock_redis

    @staticmethod
    def create_mock_http_client():
        """Create a mock HTTP client."""
        mock_client = Mock()
        mock_client.get = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.put = AsyncMock()
        mock_client.delete = AsyncMock()
        return mock_client


class AssertionHelpers:
    """Helper functions for test assertions."""

    @staticmethod
    def assert_called_with_timeout(mock_func, timeout: float = 1.0):
        """Assert mock function was called within timeout."""
        import time
        start_time = time.time()
        while time.time() - start_time < timeout:
            if mock_func.called:
                return True
            time.sleep(0.01)
        raise AssertionError(f"Function not called within {timeout} seconds")

    @staticmethod
    def assert_json_equal(actual: dict[str, Any], expected: dict[str, Any]):
        """Assert two JSON objects are equal (ignoring order)."""
        assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)

    @staticmethod
    def assert_contains_keys(data: dict[str, Any], keys: list):
        """Assert dictionary contains all specified keys."""
        for key in keys:
            assert key in data, f"Key '{key}' not found in data"

    @staticmethod
    def assert_message_structure(message: dict[str, Any]):
        """Assert message has correct structure."""
        required_keys = ["message_id", "message_type", "content", "user", "timestamp"]
        AssertionHelpers.assert_contains_keys(message, required_keys)

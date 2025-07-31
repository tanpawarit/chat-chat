"""
Unit tests for LINE adapter.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from adapters.platforms.line_adapter import LineAdapter
from models.message import IncomingMessage, MessageType, OutgoingMessage
from models.platform import PlatformType
from models.user import UserProfile
from tests.fixtures.mock_data import MockLineData


class TestLineAdapter:
    """Test LINE adapter functionality."""

    @pytest.fixture
    def line_config(self):
        """LINE adapter configuration."""
        return {
            "store_id": "test_store_001",
            "platform": "line",
            "credentials": {
                "channel_access_token": "test_channel_token",
                "channel_secret": "test_channel_secret",
            },
        }

    @pytest.fixture
    def line_adapter(self, line_config):
        """Create LINE adapter instance."""
        return LineAdapter(line_config)

    def test_adapter_initialization(self, line_adapter):
        """Test LINE adapter initialization."""
        assert line_adapter.platform == PlatformType.LINE
        assert line_adapter.channel_access_token == "test_channel_token"
        assert line_adapter.channel_secret == "test_channel_secret"
        assert line_adapter.base_url == "https://api.line.me/v2/bot"

    @pytest.mark.asyncio
    async def test_parse_text_message(self, line_adapter):
        """Test parsing LINE text message."""
        webhook_data = MockLineData.webhook_text_message()

        with patch.object(line_adapter, "_get_user_profile") as mock_profile:
            mock_profile.return_value = UserProfile(
                display_name="Test User",
                picture_url="https://example.com/avatar.jpg",
                language="th",
            )

            message = await line_adapter.parse_incoming(webhook_data)

            assert message is not None
            assert isinstance(message, IncomingMessage)
            assert message.message_type == MessageType.TEXT
            assert message.content == "Hello, this is a test message"
            assert message.user.user_id == "user123"
            assert message.platform_data["replyToken"] == "reply123"

    @pytest.mark.asyncio
    async def test_parse_image_message(self, line_adapter):
        """Test parsing LINE image message."""
        webhook_data = MockLineData.webhook_image_message()

        with patch.object(line_adapter, "_get_user_profile") as mock_profile:
            mock_profile.return_value = UserProfile(
                display_name="Test User",
                picture_url="https://example.com/avatar.jpg",
                language="th",
            )

            message = await line_adapter.parse_incoming(webhook_data)

            assert message is not None
            assert message.message_type == MessageType.IMAGE
            assert message.content == ""  # Image messages don't have text content
            assert message.platform_data["messageId"] == "img123"

    @pytest.mark.asyncio
    async def test_parse_empty_webhook(self, line_adapter):
        """Test parsing empty webhook data."""
        webhook_data = {"events": []}

        message = await line_adapter.parse_incoming(webhook_data)

        assert message is None

    @pytest.mark.asyncio
    async def test_parse_non_message_event(self, line_adapter):
        """Test parsing non-message events."""
        webhook_data = {
            "events": [
                {
                    "type": "follow",
                    "source": {"type": "user", "userId": "user123"},
                    "timestamp": 1640995200000,
                    "replyToken": "reply123",
                }
            ]
        }

        message = await line_adapter.parse_incoming(webhook_data)

        assert message is None

    def test_format_text_message(self, line_adapter):
        """Test formatting text message for LINE."""
        outgoing_message = OutgoingMessage(
            message_type=MessageType.TEXT, content="Hello from bot!", platform_data={}
        )

        formatted = line_adapter.format_outgoing(outgoing_message)

        assert formatted["type"] == "text"
        assert formatted["text"] == "Hello from bot!"

    def test_format_image_message(self, line_adapter):
        """Test formatting image message for LINE."""
        outgoing_message = OutgoingMessage(
            message_type=MessageType.IMAGE,
            content="https://example.com/image.jpg",
            platform_data={"previewImageUrl": "https://example.com/preview.jpg"},
        )

        formatted = line_adapter.format_outgoing(outgoing_message)

        assert formatted["type"] == "image"
        assert formatted["originalContentUrl"] == "https://example.com/image.jpg"
        assert formatted["previewImageUrl"] == "https://example.com/preview.jpg"

    def test_format_unsupported_message(self, line_adapter):
        """Test formatting unsupported message type."""
        outgoing_message = OutgoingMessage(
            message_type=MessageType.OTHER,
            content="Unsupported content",
            platform_data={},
        )

        formatted = line_adapter.format_outgoing(outgoing_message)

        # Should fallback to text message
        assert formatted["type"] == "text"
        assert "not supported" in formatted["text"].lower()

    @pytest.mark.asyncio
    async def test_send_message_success(self, line_adapter):
        """Test successful message sending."""
        outgoing_message = OutgoingMessage(
            message_type=MessageType.TEXT, content="Test response", platform_data={}
        )

        platform_data = {"replyToken": "reply123"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={})
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await line_adapter.send_message(outgoing_message, platform_data)

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_failure(self, line_adapter):
        """Test failed message sending."""
        outgoing_message = OutgoingMessage(
            message_type=MessageType.TEXT, content="Test response", platform_data={}
        )

        platform_data = {"replyToken": "reply123"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = Mock()
            mock_response.status = 400
            mock_response.json = AsyncMock(return_value={"message": "Invalid request"})
            mock_post.return_value.__aenter__.return_value = mock_response

            result = await line_adapter.send_message(outgoing_message, platform_data)

            assert result is False

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, line_adapter):
        """Test successful user profile retrieval."""
        user_id = "user123"
        profile_data = MockLineData.user_profile()

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=profile_data)
            mock_get.return_value.__aenter__.return_value = mock_response

            profile = await line_adapter.get_user_profile(user_id)

            assert profile is not None
            assert profile.display_name == "Test User"
            assert profile.picture_url == "https://example.com/avatar.jpg"
            assert profile.language == "th"

    @pytest.mark.asyncio
    async def test_get_user_profile_failure(self, line_adapter):
        """Test failed user profile retrieval."""
        user_id = "user123"

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = Mock()
            mock_response.status = 404
            mock_response.json = AsyncMock(return_value={"message": "User not found"})
            mock_get.return_value.__aenter__.return_value = mock_response

            profile = await line_adapter.get_user_profile(user_id)

            assert profile is None

    def test_validate_signature_valid(self, line_adapter):
        """Test signature validation with valid signature."""
        body = '{"events":[]}'
        signature = "valid_signature"

        with patch("hmac.compare_digest") as mock_compare:
            mock_compare.return_value = True

            result = line_adapter._validate_signature(body, signature)

            assert result is True

    def test_validate_signature_invalid(self, line_adapter):
        """Test signature validation with invalid signature."""
        body = '{"events":[]}'
        signature = "invalid_signature"

        with patch("hmac.compare_digest") as mock_compare:
            mock_compare.return_value = False

            result = line_adapter._validate_signature(body, signature)

            assert result is False


@pytest.mark.unit
class TestLineAdapterEdgeCases:
    """Test LINE adapter edge cases."""

    @pytest.fixture
    def line_adapter(self):
        """Create LINE adapter with minimal config."""
        config = {
            "store_id": "test_store",
            "platform": "line",
            "credentials": {
                "channel_access_token": "token",
                "channel_secret": "secret",
            },
        }
        return LineAdapter(config)

    @pytest.mark.asyncio
    async def test_parse_malformed_webhook(self, line_adapter):
        """Test parsing malformed webhook data."""
        webhook_data = {"invalid": "data"}

        message = await line_adapter.parse_incoming(webhook_data)

        assert message is None

    @pytest.mark.asyncio
    async def test_network_error_handling(self, line_adapter):
        """Test network error handling."""
        outgoing_message = OutgoingMessage(
            message_type=MessageType.TEXT, content="Test", platform_data={}
        )
        platform_data = {"replyToken": "reply123"}

        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = Exception("Network error")

            result = await line_adapter.send_message(outgoing_message, platform_data)

            assert result is False

    def test_missing_credentials(self):
        """Test adapter creation with missing credentials."""
        config = {"store_id": "test_store", "platform": "line", "credentials": {}}

        with pytest.raises(KeyError):
            LineAdapter(config)

"""
Unit tests for message models.
"""

import pytest
from pydantic import ValidationError

from models.message import IncomingMessage, MessageType, OutgoingMessage
from models.platform import PlatformType
from models.user import User, UserProfile


class TestMessageType:
    """Test MessageType enum."""

    def test_message_type_values(self):
        """Test MessageType enum values."""
        assert MessageType.TEXT == "text"
        assert MessageType.IMAGE == "image"
        assert MessageType.VIDEO == "video"
        assert MessageType.AUDIO == "audio"
        assert MessageType.STICKER == "sticker"
        assert MessageType.LOCATION == "location"
        assert MessageType.OTHER == "other"


class TestIncomingMessage:
    """Test IncomingMessage model."""

    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            user_id="test_user_123",
            platform=PlatformType.LINE,
            profile=UserProfile(
                display_name="Test User",
                picture_url="https://example.com/avatar.jpg",
                language="th",
            ),
        )

    def test_create_text_message(self, sample_user):
        """Test creating a text message."""
        message = IncomingMessage(
            message_id="msg_123",
            message_type=MessageType.TEXT,
            content="Hello, world!",
            user=sample_user,
            timestamp="2024-01-15T10:00:00Z",
            platform_data={"replyToken": "reply_123"},
        )

        assert message.message_id == "msg_123"
        assert message.message_type == MessageType.TEXT
        assert message.content == "Hello, world!"
        assert message.user == sample_user
        assert message.timestamp == "2024-01-15T10:00:00Z"
        assert message.platform_data == {"replyToken": "reply_123"}

    def test_create_image_message(self, sample_user):
        """Test creating an image message."""
        message = IncomingMessage(
            message_id="img_123",
            message_type=MessageType.IMAGE,
            content="",
            user=sample_user,
            timestamp="2024-01-15T10:00:00Z",
            platform_data={"contentProvider": {"type": "line"}},
        )

        assert message.message_type == MessageType.IMAGE
        assert message.content == ""
        assert "contentProvider" in message.platform_data

    def test_required_fields(self, sample_user):
        """Test that required fields are validated."""
        # Missing message_id should raise validation error
        with pytest.raises(ValidationError):
            IncomingMessage(
                message_type=MessageType.TEXT,
                content="Hello",
                user=sample_user,
                timestamp="2024-01-15T10:00:00Z",
                platform_data={},
            )

    def test_optional_platform_data(self, sample_user):
        """Test that platform_data is optional."""
        message = IncomingMessage(
            message_id="msg_123",
            message_type=MessageType.TEXT,
            content="Hello",
            user=sample_user,
            timestamp="2024-01-15T10:00:00Z",
        )

        assert message.platform_data == {}

    def test_message_serialization(self, sample_user):
        """Test message serialization to dict."""
        message = IncomingMessage(
            message_id="msg_123",
            message_type=MessageType.TEXT,
            content="Hello",
            user=sample_user,
            timestamp="2024-01-15T10:00:00Z",
            platform_data={"replyToken": "reply_123"},
        )

        data = message.model_dump()

        assert data["message_id"] == "msg_123"
        assert data["message_type"] == "text"
        assert data["content"] == "Hello"
        assert "user" in data
        assert data["timestamp"] == "2024-01-15T10:00:00Z"
        assert data["platform_data"]["replyToken"] == "reply_123"


class TestOutgoingMessage:
    """Test OutgoingMessage model."""

    def test_create_text_response(self):
        """Test creating a text response message."""
        message = OutgoingMessage(
            message_type=MessageType.TEXT,
            content="This is a response",
            platform_data={"quickReply": {"items": []}},
        )

        assert message.message_type == MessageType.TEXT
        assert message.content == "This is a response"
        assert message.platform_data == {"quickReply": {"items": []}}

    def test_create_image_response(self):
        """Test creating an image response message."""
        message = OutgoingMessage(
            message_type=MessageType.IMAGE,
            content="https://example.com/image.jpg",
            platform_data={"previewImageUrl": "https://example.com/preview.jpg"},
        )

        assert message.message_type == MessageType.IMAGE
        assert message.content == "https://example.com/image.jpg"
        assert "previewImageUrl" in message.platform_data

    def test_required_fields(self):
        """Test that required fields are validated."""
        # Missing message_type should raise validation error
        with pytest.raises(ValidationError):
            OutgoingMessage(content="Hello", platform_data={})

        # Missing content should raise validation error
        with pytest.raises(ValidationError):
            OutgoingMessage(message_type=MessageType.TEXT, platform_data={})

    def test_optional_platform_data(self):
        """Test that platform_data is optional."""
        message = OutgoingMessage(message_type=MessageType.TEXT, content="Hello")

        assert message.platform_data == {}

    def test_message_serialization(self):
        """Test message serialization to dict."""
        message = OutgoingMessage(
            message_type=MessageType.TEXT,
            content="Response message",
            platform_data={"quickReply": {"items": ["Yes", "No"]}},
        )

        data = message.model_dump()

        assert data["message_type"] == "text"
        assert data["content"] == "Response message"
        assert data["platform_data"]["quickReply"]["items"] == ["Yes", "No"]


@pytest.mark.unit
class TestMessageIntegration:
    """Integration tests for message models."""

    def test_message_roundtrip(self, sample_user):
        """Test creating incoming message and generating response."""
        # Create incoming message
        incoming = IncomingMessage(
            message_id="msg_123",
            message_type=MessageType.TEXT,
            content="Hello, bot!",
            user=sample_user,
            timestamp="2024-01-15T10:00:00Z",
            platform_data={"replyToken": "reply_123"},
        )

        # Create response based on incoming message
        outgoing = OutgoingMessage(
            message_type=MessageType.TEXT,
            content=f"Hello, {incoming.user.profile.display_name}!",
            platform_data={"replyToken": incoming.platform_data["replyToken"]},
        )

        assert outgoing.content == "Hello, Test User!"
        assert outgoing.platform_data["replyToken"] == "reply_123"

    def test_different_message_types(self, sample_user):
        """Test handling different message types."""
        message_types = [
            MessageType.TEXT,
            MessageType.IMAGE,
            MessageType.VIDEO,
            MessageType.AUDIO,
            MessageType.STICKER,
            MessageType.LOCATION,
            MessageType.OTHER,
        ]

        for msg_type in message_types:
            message = IncomingMessage(
                message_id=f"msg_{msg_type}",
                message_type=msg_type,
                content="test content",
                user=sample_user,
                timestamp="2024-01-15T10:00:00Z",
                platform_data={},
            )
            assert message.message_type == msg_type

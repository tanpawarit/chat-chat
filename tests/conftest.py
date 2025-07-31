"""
pytest configuration and shared fixtures for chat-chat bot system.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from adapters.platforms.line_adapter import LineAdapter
from bot_gateway.gateway import BotGateway
from models.customer import Customer
from models.message import IncomingMessage, MessageType, OutgoingMessage
from models.platform import PlatformType
from models.store import Store
from models.user import User, UserProfile


# Test marks
def pytest_configure(config):
    """Configure pytest marks."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        user_id="test_user_123",
        platform=PlatformType.LINE,
        profile=UserProfile(
            display_name="Test User",
            picture_url="https://example.com/avatar.jpg",
            language="th",
        ),
    )


@pytest.fixture
def sample_store():
    """Create a sample store for testing."""
    return Store(
        store_id="test_store_001",
        name="Test Cafe",
        webhook_path="/webhook/line/test_store_001",
        platform_config={
            "channel_access_token": "test_token",
            "channel_secret": "test_secret",
        },
    )


@pytest.fixture
def sample_customer(sample_user, sample_store):
    """Create a sample customer for testing."""
    return Customer(
        customer_id="cust_123",
        user=sample_user,
        store_id=sample_store.store_id,
        preferences={"language": "th", "notification": True},
    )


@pytest.fixture
def sample_text_message(sample_user):
    """Create a sample text message for testing."""
    return IncomingMessage(
        message_id="msg_123",
        message_type=MessageType.TEXT,
        content="Hello, this is a test message",
        user=sample_user,
        timestamp="2024-01-01T10:00:00Z",
        platform_data={},
    )


@pytest.fixture
def sample_outgoing_message():
    """Create a sample outgoing message for testing."""
    return OutgoingMessage(
        message_type=MessageType.TEXT,
        content="This is a response message",
        platform_data={},
    )


@pytest.fixture
def mock_line_webhook_data():
    """Mock LINE webhook data."""
    return {
        "events": [
            {
                "type": "message",
                "message": {"type": "text", "id": "msg123", "text": "Hello"},
                "source": {"type": "user", "userId": "user123"},
                "timestamp": 1640995200000,
                "replyToken": "reply123",
            }
        ]
    }


@pytest.fixture
def mock_line_profile():
    """Mock LINE profile data."""
    return {
        "displayName": "Test User",
        "pictureUrl": "https://example.com/avatar.jpg",
        "language": "th",
    }


@pytest.fixture
def mock_line_adapter():
    """Create a mock LINE adapter."""
    adapter = Mock(spec=LineAdapter)
    adapter.platform = PlatformType.LINE
    adapter.parse_incoming = AsyncMock()
    adapter.format_outgoing = Mock()
    adapter.send_message = AsyncMock()
    adapter.get_user_profile = AsyncMock()
    return adapter


@pytest.fixture
def mock_bot_gateway():
    """Create a mock bot gateway."""
    gateway = Mock(spec=BotGateway)
    gateway.handle_message = AsyncMock()
    return gateway


@pytest.fixture
def test_config():
    """Test configuration data."""
    return {
        "platforms": {
            "line": {
                "webhook_path": "/webhook/line",
                "capabilities": {
                    "supports_text": True,
                    "supports_images": True,
                    "supports_quick_replies": True,
                },
            }
        },
        "stores": {
            "test_store_001": {
                "name": "Test Cafe",
                "platform": "line",
                "credentials": {
                    "channel_access_token": "test_token",
                    "channel_secret": "test_secret",
                },
            }
        },
    }


@pytest.fixture
def redis_mock():
    """Mock Redis client for testing."""
    redis_mock = Mock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.exists = AsyncMock(return_value=False)
    return redis_mock


@pytest.fixture
def fastapi_test_client():
    """Create FastAPI test client."""
    from main import app

    return TestClient(app)


@pytest.fixture
def sample_webhook_headers():
    """Sample webhook headers for testing."""
    return {"X-Line-Signature": "test_signature", "Content-Type": "application/json"}


@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test."""
    yield
    # Add any cleanup logic here if needed

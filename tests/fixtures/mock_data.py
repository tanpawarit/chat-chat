"""
Mock data for testing.
"""
from typing import Any


class MockLineData:
    """Mock data for LINE platform testing."""

    @staticmethod
    def webhook_text_message() -> dict[str, Any]:
        """Mock LINE webhook data for text message."""
        return {
            "events": [{
                "type": "message",
                "message": {
                    "type": "text",
                    "id": "msg123",
                    "text": "Hello, this is a test message"
                },
                "source": {
                    "type": "user",
                    "userId": "user123"
                },
                "timestamp": 1640995200000,
                "replyToken": "reply123"
            }]
        }

    @staticmethod
    def webhook_image_message() -> dict[str, Any]:
        """Mock LINE webhook data for image message."""
        return {
            "events": [{
                "type": "message",
                "message": {
                    "type": "image",
                    "id": "img123",
                    "contentProvider": {
                        "type": "line"
                    }
                },
                "source": {
                    "type": "user",
                    "userId": "user123"
                },
                "timestamp": 1640995200000,
                "replyToken": "reply123"
            }]
        }

    @staticmethod
    def user_profile() -> dict[str, Any]:
        """Mock LINE user profile data."""
        return {
            "displayName": "Test User",
            "pictureUrl": "https://example.com/avatar.jpg",
            "language": "th",
            "statusMessage": "Hello, World!"
        }

    @staticmethod
    def reply_message_request() -> dict[str, Any]:
        """Mock LINE reply message request."""
        return {
            "replyToken": "reply123",
            "messages": [{
                "type": "text",
                "text": "This is a reply message"
            }]
        }


class MockStoreData:
    """Mock data for store testing."""

    @staticmethod
    def store_config() -> dict[str, Any]:
        """Mock store configuration."""
        return {
            "store_id": "test_store_001",
            "name": "Test Cafe",
            "platform": "line",
            "webhook_path": "/webhook/line/test_store_001",
            "credentials": {
                "channel_access_token": "test_channel_token",
                "channel_secret": "test_channel_secret"
            },
            "settings": {
                "language": "th",
                "timezone": "Asia/Bangkok",
                "business_hours": {
                    "start": "08:00",
                    "end": "22:00"
                }
            }
        }

    @staticmethod
    def multiple_stores() -> list[dict[str, Any]]:
        """Mock multiple store configurations."""
        return [
            {
                "store_id": "store_001",
                "name": "Cafe A",
                "platform": "line"
            },
            {
                "store_id": "store_002",
                "name": "Cafe B",
                "platform": "line"
            }
        ]


class MockCustomerData:
    """Mock data for customer testing."""

    @staticmethod
    def customer_profile() -> dict[str, Any]:
        """Mock customer profile."""
        return {
            "customer_id": "cust_123",
            "user_id": "user123",
            "store_id": "test_store_001",
            "preferences": {
                "language": "th",
                "notification": True,
                "favorite_items": ["coffee", "cake"]
            },
            "history": {
                "first_visit": "2024-01-01T10:00:00Z",
                "last_visit": "2024-01-15T14:30:00Z",
                "visit_count": 5
            }
        }

    @staticmethod
    def customer_session() -> dict[str, Any]:
        """Mock customer session data."""
        return {
            "session_id": "session_123",
            "customer_id": "cust_123",
            "store_id": "test_store_001",
            "context": {
                "current_topic": "menu_inquiry",
                "last_action": "view_menu",
                "conversation_state": "active"
            },
            "created_at": "2024-01-15T14:00:00Z",
            "updated_at": "2024-01-15T14:30:00Z"
        }


class MockMessageData:
    """Mock data for message testing."""

    @staticmethod
    def text_messages() -> list[dict[str, Any]]:
        """Mock text message variations."""
        return [
            {
                "message_id": "msg_001",
                "content": "Hello",
                "message_type": "text",
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "message_id": "msg_002",
                "content": "What's on the menu today?",
                "message_type": "text",
                "timestamp": "2024-01-15T10:01:00Z"
            },
            {
                "message_id": "msg_003",
                "content": "Thank you!",
                "message_type": "text",
                "timestamp": "2024-01-15T10:02:00Z"
            }
        ]

    @staticmethod
    def response_templates() -> dict[str, str]:
        """Mock response message templates."""
        return {
            "greeting": "สวัสดีครับ! ยินดีต้อนรับสู่ {store_name}",
            "menu_inquiry": "เมนูวันนี้มีดังนี้ครับ...",
            "thank_you": "ขอบคุณที่ใช้บริการครับ!",
            "error": "ขออภัยครับ เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"
        }

"""
Integration tests for webhook processing flow.
"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from tests.fixtures.mock_data import MockLineData


@pytest.mark.integration
class TestWebhookFlow:
    """Test complete webhook processing flow."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def webhook_headers(self):
        """Sample webhook headers."""
        return {
            "X-Line-Signature": "test_signature",
            "Content-Type": "application/json"
        }

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_status_endpoint(self, client):
        """Test status endpoint."""
        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "timestamp" in data
        assert data["service"] == "chat-chat-bot"

    @patch('adapters.platforms.line_adapter.LineAdapter._validate_signature')
    @patch('bot_gateway.gateway.BotGateway.handle_message')
    def test_line_webhook_text_message(self, mock_handle, mock_validate, client, webhook_headers):
        """Test LINE webhook with text message."""
        mock_validate.return_value = True
        mock_handle.return_value = AsyncMock()

        webhook_data = MockLineData.webhook_text_message()

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=webhook_headers
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch('adapters.platforms.line_adapter.LineAdapter._validate_signature')
    def test_line_webhook_invalid_signature(self, mock_validate, client, webhook_headers):
        """Test LINE webhook with invalid signature."""
        mock_validate.return_value = False

        webhook_data = MockLineData.webhook_text_message()

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=webhook_headers
        )

        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]

    def test_line_webhook_missing_signature(self, client):
        """Test LINE webhook with missing signature."""
        webhook_data = MockLineData.webhook_text_message()
        headers = {"Content-Type": "application/json"}

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=headers
        )

        assert response.status_code == 400
        assert "Missing signature" in response.json()["detail"]

    def test_line_webhook_invalid_store(self, client, webhook_headers):
        """Test LINE webhook for non-existent store."""
        webhook_data = MockLineData.webhook_text_message()

        response = client.post(
            "/webhook/line/invalid_store",
            json=webhook_data,
            headers=webhook_headers
        )

        assert response.status_code == 404
        assert "Store not found" in response.json()["detail"]

    @patch('adapters.platforms.line_adapter.LineAdapter._validate_signature')
    def test_line_webhook_empty_events(self, mock_validate, client, webhook_headers):
        """Test LINE webhook with empty events."""
        mock_validate.return_value = True

        webhook_data = {"events": []}

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=webhook_headers
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @patch('adapters.platforms.line_adapter.LineAdapter._validate_signature')
    @patch('bot_gateway.gateway.BotGateway.handle_message')
    def test_line_webhook_multiple_events(self, mock_handle, mock_validate, client, webhook_headers):
        """Test LINE webhook with multiple events."""
        mock_validate.return_value = True
        mock_handle.return_value = AsyncMock()

        webhook_data = {
            "events": [
                {
                    "type": "message",
                    "message": {"type": "text", "id": "msg1", "text": "Hello 1"},
                    "source": {"type": "user", "userId": "user1"},
                    "timestamp": 1640995200000,
                    "replyToken": "reply1"
                },
                {
                    "type": "message",
                    "message": {"type": "text", "id": "msg2", "text": "Hello 2"},
                    "source": {"type": "user", "userId": "user2"},
                    "timestamp": 1640995201000,
                    "replyToken": "reply2"
                }
            ]
        }

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=webhook_headers
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert mock_handle.call_count == 2


@pytest.mark.integration
class TestWebhookErrorHandling:
    """Test webhook error handling scenarios."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @pytest.fixture
    def webhook_headers(self):
        """Sample webhook headers."""
        return {
            "X-Line-Signature": "test_signature",
            "Content-Type": "application/json"
        }

    def test_invalid_json_payload(self, client, webhook_headers):
        """Test webhook with invalid JSON payload."""
        response = client.post(
            "/webhook/line/test_store_001",
            data="invalid json",
            headers=webhook_headers
        )

        assert response.status_code == 422

    def test_missing_content_type(self, client):
        """Test webhook with missing content type."""
        webhook_data = MockLineData.webhook_text_message()
        headers = {"X-Line-Signature": "test_signature"}

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=headers
        )

        # FastAPI should handle this automatically
        assert response.status_code in [200, 400]

    @patch('adapters.platforms.line_adapter.LineAdapter._validate_signature')
    @patch('bot_gateway.gateway.BotGateway.handle_message')
    def test_gateway_exception(self, mock_handle, mock_validate, client, webhook_headers):
        """Test webhook when gateway raises exception."""
        mock_validate.return_value = True
        mock_handle.side_effect = Exception("Gateway error")

        webhook_data = MockLineData.webhook_text_message()

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=webhook_headers
        )

        assert response.status_code == 500

    @patch('services.adapter_factory.AdapterFactory.get_adapter')
    def test_adapter_creation_failure(self, mock_get_adapter, client, webhook_headers):
        """Test webhook when adapter creation fails."""
        mock_get_adapter.side_effect = Exception("Adapter creation failed")

        webhook_data = MockLineData.webhook_text_message()

        response = client.post(
            "/webhook/line/test_store_001",
            json=webhook_data,
            headers=webhook_headers
        )

        assert response.status_code == 500


@pytest.mark.integration
@pytest.mark.slow
class TestWebhookPerformance:
    """Test webhook performance scenarios."""

    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    @patch('adapters.platforms.line_adapter.LineAdapter._validate_signature')
    @patch('bot_gateway.gateway.BotGateway.handle_message')
    def test_concurrent_webhooks(self, mock_handle, mock_validate, client):
        """Test handling concurrent webhook requests."""
        import concurrent.futures

        mock_validate.return_value = True
        mock_handle.return_value = AsyncMock()

        webhook_data = MockLineData.webhook_text_message()
        headers = {
            "X-Line-Signature": "test_signature",
            "Content-Type": "application/json"
        }

        def send_webhook():
            return client.post(
                "/webhook/line/test_store_001",
                json=webhook_data,
                headers=headers
            )

        # Send 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_webhook) for _ in range(10)]
            responses = [future.result() for future in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

        # Gateway should be called 10 times
        assert mock_handle.call_count == 10

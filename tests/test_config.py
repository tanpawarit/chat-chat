"""
pytest configuration and test categories.
"""


# Test categories for better organization
class TestCategories:
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SLOW = "slow"


# Test data constants
class TestConstants:
    TEST_USER_ID = "test_user_123"
    TEST_STORE_ID = "test_store_001"
    TEST_CUSTOMER_ID = "cust_123"
    TEST_MESSAGE_ID = "msg_123"
    TEST_REPLY_TOKEN = "reply_123"

    # Platform specific
    LINE_WEBHOOK_PATH = "/webhook/line"
    LINE_CHANNEL_TOKEN = "test_channel_token"
    LINE_CHANNEL_SECRET = "test_channel_secret"

    # Test timeouts
    FAST_TEST_TIMEOUT = 1.0  # seconds
    SLOW_TEST_TIMEOUT = 10.0  # seconds

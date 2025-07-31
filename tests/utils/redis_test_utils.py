"""
Redis testing utilities.
"""

import json
from typing import Any
from unittest.mock import AsyncMock


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self):
        self._data = {}
        self._expires = {}

    async def get(self, key: str) -> str | None:
        """Mock Redis GET."""
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """Mock Redis SET."""
        self._data[key] = value
        if ex:
            self._expires[key] = ex
        return True

    async def delete(self, key: str) -> int:
        """Mock Redis DELETE."""
        if key in self._data:
            del self._data[key]
            if key in self._expires:
                del self._expires[key]
            return 1
        return 0

    async def exists(self, key: str) -> bool:
        """Mock Redis EXISTS."""
        return key in self._data

    async def hget(self, name: str, key: str) -> str | None:
        """Mock Redis HGET."""
        hash_data = self._data.get(name, {})
        if isinstance(hash_data, str):
            hash_data = json.loads(hash_data)
        return hash_data.get(key)

    async def hset(self, name: str, key: str, value: str) -> bool:
        """Mock Redis HSET."""
        if name not in self._data:
            self._data[name] = {}

        hash_data = self._data[name]
        if isinstance(hash_data, str):
            hash_data = json.loads(hash_data)

        hash_data[key] = value
        self._data[name] = json.dumps(hash_data)
        return True

    async def expire(self, key: str, seconds: int) -> bool:
        """Mock Redis EXPIRE."""
        if key in self._data:
            self._expires[key] = seconds
            return True
        return False

    def clear(self):
        """Clear all data."""
        self._data.clear()
        self._expires.clear()

    def get_data(self) -> dict[str, Any]:
        """Get all stored data for testing."""
        return self._data.copy()


class RedisTestHelpers:
    """Helper functions for Redis testing."""

    @staticmethod
    def create_mock_redis() -> MockRedisClient:
        """Create a new mock Redis client."""
        return MockRedisClient()

    @staticmethod
    def setup_session_data(
        redis_client: MockRedisClient, session_id: str, data: dict[str, Any]
    ):
        """Setup session data in mock Redis."""
        session_key = f"session:{session_id}"
        redis_client._data[session_key] = json.dumps(data)

    @staticmethod
    def setup_customer_data(
        redis_client: MockRedisClient, customer_id: str, data: dict[str, Any]
    ):
        """Setup customer data in mock Redis."""
        customer_key = f"customer:{customer_id}"
        redis_client._data[customer_key] = json.dumps(data)

    @staticmethod
    def setup_memory_data(
        redis_client: MockRedisClient, memory_id: str, data: dict[str, Any]
    ):
        """Setup memory data in mock Redis."""
        memory_key = f"memory:{memory_id}"
        redis_client._data[memory_key] = json.dumps(data)

    @staticmethod
    def assert_session_exists(redis_client: MockRedisClient, session_id: str):
        """Assert session exists in Redis."""
        session_key = f"session:{session_id}"
        assert session_key in redis_client._data

    @staticmethod
    def assert_data_equals(
        redis_client: MockRedisClient, key: str, expected_data: dict[str, Any]
    ):
        """Assert data in Redis equals expected data."""
        stored_data = redis_client._data.get(key)
        if stored_data:
            stored_data = json.loads(stored_data)
        assert stored_data == expected_data

    @staticmethod
    def get_session_data(
        redis_client: MockRedisClient, session_id: str
    ) -> dict[str, Any] | None:
        """Get session data from mock Redis."""
        session_key = f"session:{session_id}"
        data = redis_client._data.get(session_key)
        return json.loads(data) if data else None


class MockAsyncRedis:
    """Alternative mock Redis with AsyncMock behavior."""

    def __init__(self):
        self.get = AsyncMock()
        self.set = AsyncMock()
        self.delete = AsyncMock()
        self.exists = AsyncMock()
        self.hget = AsyncMock()
        self.hset = AsyncMock()
        self.expire = AsyncMock()

        # Default return values
        self.get.return_value = None
        self.set.return_value = True
        self.delete.return_value = 1
        self.exists.return_value = False
        self.hget.return_value = None
        self.hset.return_value = True
        self.expire.return_value = True

    def setup_get_response(self, key: str, value: str):
        """Setup GET response for specific key."""

        def side_effect(k):
            return value if k == key else None

        self.get.side_effect = side_effect

    def setup_exists_response(self, key: str, exists: bool = True):
        """Setup EXISTS response for specific key."""

        def side_effect(k):
            return exists if k == key else False

        self.exists.side_effect = side_effect

"""
Redis-based session storage implementation.
Handles persistence of session data using Redis with memory system integration.
"""

import json
import logging
from datetime import datetime
from typing import Any, cast

import redis.asyncio as redis

from models.session import Session, SessionState

logger = logging.getLogger(__name__)


class RedisSessionStore:
    """
    Redis-based session storage that works alongside the memory system.
    This stores traditional session data while memory system handles SM/LM.
    """

    def __init__(self, redis_url: str, key_prefix: str = "session"):
        """
        Initialize Redis session store.

        Args:
            redis_url: Redis connection URL
            key_prefix: Key prefix for session storage (default: "session")
        """
        self.redis_url = redis_url
        self.key_prefix = key_prefix
        self.redis_client: redis.Redis | None = None

        logger.info(f"RedisSessionStore initialized with prefix: {key_prefix}")

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self.redis_url)
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis for session storage")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
            logger.info("Disconnected from Redis")

    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"{self.key_prefix}:{session_id}"

    def _get_user_sessions_key(self, user_id: str, platform: str) -> str:
        """Generate Redis key for user sessions list."""
        return f"{self.key_prefix}:user:{user_id}:{platform}"

    async def save_session(self, session: Session, ttl: int = 3600) -> bool:
        """
        Save session to Redis.

        Args:
            session: Session to save
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            assert self.redis_client is not None  # Type guard
            key = self._get_session_key(session.session_id)

            # Convert session to JSON-serializable format
            session_data = self._serialize_session(session)

            # Save session data with TTL
            await self.redis_client.set(
                key, json.dumps(session_data, ensure_ascii=False), ex=ttl
            )

            # Add to user sessions list (for tracking)
            user_key = self._get_user_sessions_key(session.user_id, session.platform)
            await cast("Any", self.redis_client.sadd(user_key, session.session_id))
            await cast("Any", self.redis_client.expire(user_key, ttl))

            logger.debug(f"Saved session {session.session_id} to Redis")
            return True

        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {e}")
            return False

    async def load_session(self, session_id: str) -> Session | None:
        """
        Load session from Redis.

        Args:
            session_id: Session ID to load

        Returns:
            Session if found, None otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            assert self.redis_client is not None  # Type guard
            key = self._get_session_key(session_id)
            data = await self.redis_client.get(key)

            if data is None:
                logger.debug(f"Session {session_id} not found in Redis")
                return None

            # Deserialize session data
            session_dict = json.loads(data)
            session = self._deserialize_session(session_dict)

            logger.debug(f"Loaded session {session_id} from Redis")
            return session

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Redis.

        Args:
            session_id: Session ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            assert self.redis_client is not None  # Type guard
            key = self._get_session_key(session_id)
            result = await self.redis_client.delete(key)

            if result:
                logger.debug(f"Deleted session {session_id} from Redis")
                return True
            else:
                logger.debug(f"Session {session_id} not found for deletion")
                return False

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    async def get_user_sessions(self, user_id: str, platform: str) -> list[str]:
        """
        Get all session IDs for a user on a platform.

        Args:
            user_id: User identifier
            platform: Platform name

        Returns:
            List of session IDs
        """
        try:
            if not self.redis_client:
                await self.connect()

            assert self.redis_client is not None  # Type guard
            user_key = self._get_user_sessions_key(user_id, platform)
            session_ids = await cast("Any", self.redis_client.smembers(user_key))

            # Convert bytes to strings
            return [
                sid.decode("utf-8") if isinstance(sid, bytes) else sid
                for sid in session_ids
            ]

        except Exception as e:
            logger.error(f"Error getting sessions for {user_id}@{platform}: {e}")
            return []

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (Redis handles TTL automatically).
        This method is for compatibility with the session manager interface.

        Returns:
            Number of sessions cleaned (Redis TTL handles this automatically)
        """
        try:
            # Redis handles TTL cleanup automatically
            # This method exists for interface compatibility
            logger.debug("Redis TTL handles expired session cleanup automatically")
            return 0

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0

    async def update_session_activity(self, session_id: str, ttl: int = 3600) -> bool:
        """
        Update session activity timestamp and extend TTL.

        Args:
            session_id: Session ID to update
            ttl: New TTL in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                await self.connect()

            assert self.redis_client is not None  # Type guard
            key = self._get_session_key(session_id)

            # Check if session exists
            exists = await self.redis_client.exists(key)
            if not exists:
                return False

            # Extend TTL
            await self.redis_client.expire(key, ttl)

            logger.debug(f"Extended TTL for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating session activity {session_id}: {e}")
            return False

    async def get_session_info(self, session_id: str) -> dict[str, Any] | None:
        """
        Get basic session information without loading full session.

        Args:
            session_id: Session ID

        Returns:
            Session info dict or None
        """
        try:
            if not self.redis_client:
                await self.connect()

            assert self.redis_client is not None  # Type guard
            key = self._get_session_key(session_id)

            # Get TTL and check existence
            ttl = await self.redis_client.ttl(key)

            if ttl == -2:  # Key doesn't exist
                return None

            return {
                "session_id": session_id,
                "exists": True,
                "ttl": ttl,
                "expires_in_seconds": ttl if ttl > 0 else None,
            }

        except Exception as e:
            logger.error(f"Error getting session info {session_id}: {e}")
            return None

    # Private helper methods

    def _serialize_session(self, session: Session) -> dict[str, Any]:
        """Convert Session to JSON-serializable dict."""
        session_dict = session.model_dump()

        # Convert datetime objects to ISO strings
        datetime_fields = ["created_at", "updated_at", "expires_at", "last_activity"]
        for field in datetime_fields:
            if (
                field in session_dict
                and session_dict[field] is not None
                and isinstance(session_dict[field], datetime)
            ):
                session_dict[field] = session_dict[field].isoformat()

        # Convert enum to string
        if "state" in session_dict:
            session_dict["state"] = session_dict["state"]

        return session_dict

    def _deserialize_session(self, session_dict: dict[str, Any]) -> Session:
        """Convert JSON dict back to Session object."""
        # Convert ISO strings back to datetime objects
        datetime_fields = ["created_at", "updated_at", "expires_at", "last_activity"]
        for field in datetime_fields:
            if (
                field in session_dict
                and session_dict[field] is not None
                and isinstance(session_dict[field], str)
            ):
                session_dict[field] = datetime.fromisoformat(
                    session_dict[field].replace("Z", "+00:00")
                )

        # Convert string back to enum
        if "state" in session_dict and isinstance(session_dict["state"], str):
            session_dict["state"] = SessionState(session_dict["state"])

        return Session(**session_dict)


class RedisSessionStoreFactory:
    """Factory for creating Redis session store instances."""

    @staticmethod
    def create_from_config(config: dict[str, Any]) -> RedisSessionStore:
        """
        Create Redis session store from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Configured RedisSessionStore instance
        """
        return RedisSessionStore(
            redis_url=config["memory"]["redis_url"],
            key_prefix=config.get("session_key_prefix", "session"),
        )

    @staticmethod
    def create_with_url(
        redis_url: str, key_prefix: str = "session"
    ) -> RedisSessionStore:
        """
        Create Redis session store with URL.

        Args:
            redis_url: Redis connection URL
            key_prefix: Key prefix for sessions

        Returns:
            RedisSessionStore instance
        """
        return RedisSessionStore(redis_url, key_prefix)

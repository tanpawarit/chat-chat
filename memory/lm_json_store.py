"""
JSON-based Long-term Memory storage implementation.
Handles persistence of user memory data using JSON files.
"""

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from models.memory import LongTermMemory, MemoryConfig, MemoryEvent

logger = logging.getLogger(__name__)


class LongTermMemoryStore:
    """JSON file-based storage for Long-term Memory."""

    def __init__(self, config: MemoryConfig):
        """
        Initialize the LM store.

        Args:
            config: Memory configuration
        """
        self.config = config
        self.base_path = Path(config.lm_base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_user_file_path(self, tenant_id: str, user_id: str) -> Path:
        """Get the JSON file path for a specific user."""
        tenant_dir = self.base_path / tenant_id
        tenant_dir.mkdir(exist_ok=True)
        return tenant_dir / f"{user_id}.json"

    async def load_memory(self, tenant_id: str, user_id: str) -> LongTermMemory | None:
        """
        Load long-term memory for a user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier

        Returns:
            LongTermMemory if exists, None otherwise
        """
        try:
            file_path = self._get_user_file_path(tenant_id, user_id)

            if not file_path.exists():
                logger.info(f"No LM file found for {tenant_id}:{user_id}")
                return None

            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            # Parse datetime strings back to datetime objects
            for event_data in data.get("events", []):
                if "timestamp" in event_data:
                    event_data["timestamp"] = datetime.fromisoformat(
                        event_data["timestamp"].replace("Z", "+00:00")
                    )

            if "created_at" in data:
                data["created_at"] = datetime.fromisoformat(
                    data["created_at"].replace("Z", "+00:00")
                )
            if "updated_at" in data:
                data["updated_at"] = datetime.fromisoformat(
                    data["updated_at"].replace("Z", "+00:00")
                )

            memory = LongTermMemory(**data)
            logger.info(
                f"Loaded LM for {tenant_id}:{user_id} with {len(memory.events)} events"
            )
            return memory

        except Exception as e:
            logger.error(f"Error loading LM for {tenant_id}:{user_id}: {e}")
            return None

    async def save_memory(self, memory: LongTermMemory) -> bool:
        """
        Save long-term memory for a user.

        Args:
            memory: LongTermMemory to save

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_user_file_path(memory.tenant_id, memory.user_id)

            # Clean up old events if over limit
            await self._cleanup_old_events(memory)

            # Update timestamp
            memory.updated_at = datetime.now(UTC)

            # Convert to JSON-serializable format
            data = memory.model_dump()

            # Convert datetime objects to ISO strings
            for event_data in data.get("events", []):
                if "timestamp" in event_data and isinstance(
                    event_data["timestamp"], datetime
                ):
                    event_data["timestamp"] = event_data["timestamp"].isoformat()

            if isinstance(data.get("created_at"), datetime):
                data["created_at"] = data["created_at"].isoformat()
            if isinstance(data.get("updated_at"), datetime):
                data["updated_at"] = data["updated_at"].isoformat()

            # Write to file with backup
            temp_file = file_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Atomic rename
            temp_file.replace(file_path)

            logger.info(
                f"Saved LM for {memory.tenant_id}:{memory.user_id} with {len(memory.events)} events"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error saving LM for {memory.tenant_id}:{memory.user_id}: {e}"
            )
            return False

    async def add_event(self, tenant_id: str, user_id: str, event: MemoryEvent) -> bool:
        """
        Add a single event to user's long-term memory.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            event: Event to add

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing memory or create new
            memory = await self.load_memory(tenant_id, user_id)
            if memory is None:
                memory = LongTermMemory(
                    tenant_id=tenant_id, user_id=user_id, events=[], attributes={}
                )

            # Add event
            memory.add_event(event)

            # Save updated memory
            return await self.save_memory(memory)

        except Exception as e:
            logger.error(f"Error adding event for {tenant_id}:{user_id}: {e}")
            return False

    async def get_recent_events(
        self, tenant_id: str, user_id: str, limit: int = 10
    ) -> list[MemoryEvent]:
        """
        Get recent events for a user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        memory = await self.load_memory(tenant_id, user_id)
        if memory is None:
            return []

        return memory.get_recent_events(limit)

    async def get_important_events(
        self, tenant_id: str, user_id: str, min_score: float = 0.7
    ) -> list[MemoryEvent]:
        """
        Get important events for a user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            min_score: Minimum importance score

        Returns:
            List of important events
        """
        memory = await self.load_memory(tenant_id, user_id)
        if memory is None:
            return []

        return memory.get_important_events(min_score)

    async def update_attributes(
        self, tenant_id: str, user_id: str, attributes: dict
    ) -> bool:
        """
        Update user attributes in long-term memory.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            attributes: Attributes to update

        Returns:
            True if successful, False otherwise
        """
        try:
            memory = await self.load_memory(tenant_id, user_id)
            if memory is None:
                memory = LongTermMemory(
                    tenant_id=tenant_id, user_id=user_id, events=[], attributes={}
                )

            # Update attributes
            memory.attributes.update(attributes)

            return await self.save_memory(memory)

        except Exception as e:
            logger.error(f"Error updating attributes for {tenant_id}:{user_id}: {e}")
            return False

    async def _cleanup_old_events(self, memory: LongTermMemory) -> None:
        """Clean up old events based on retention policy."""
        try:
            # Remove events older than retention period
            cutoff_date = datetime.now(UTC) - timedelta(
                days=self.config.event_retention_days
            )
            memory.events = [
                event for event in memory.events if event.timestamp > cutoff_date
            ]

            # Keep only the most recent events if over limit
            if len(memory.events) > self.config.max_events_per_user:
                # Sort by timestamp (newest first) and keep only the limit
                memory.events.sort(key=lambda x: x.timestamp, reverse=True)
                memory.events = memory.events[: self.config.max_events_per_user]

            logger.debug(f"Cleaned up events for {memory.tenant_id}:{memory.user_id}")

        except Exception as e:
            logger.error(f"Error cleaning up events: {e}")

    async def delete_memory(self, tenant_id: str, user_id: str) -> bool:
        """
        Delete all memory data for a user.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_user_file_path(tenant_id, user_id)

            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted LM file for {tenant_id}:{user_id}")

            return True

        except Exception as e:
            logger.error(f"Error deleting LM for {tenant_id}:{user_id}: {e}")
            return False

    async def list_users(self, tenant_id: str) -> list[str]:
        """
        List all users with memory data for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of user IDs
        """
        try:
            tenant_dir = self.base_path / tenant_id
            if not tenant_dir.exists():
                return []

            user_files = tenant_dir.glob("*.json")
            return [f.stem for f in user_files]

        except Exception as e:
            logger.error(f"Error listing users for tenant {tenant_id}: {e}")
            return []

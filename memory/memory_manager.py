"""
Unified Memory Manager that orchestrates Short-term and Long-term memory.
Implements the complete memory workflow from the architecture diagram.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as redis

from llm.event_processor import EventProcessor
from llm.factory import EventProcessorFactory
from memory.lm_json_store import LongTermMemoryStore
from models.memory import LongTermMemory, MemoryConfig, ShortTermMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Unified memory management system handling both SM and LM.
    Implements the memory workflow: SM expiry → LM load → Summarize → New SM.
    """

    def __init__(
        self, config: MemoryConfig, event_processor: EventProcessor | None = None
    ):
        """
        Initialize the memory manager.

        Args:
            config: Memory configuration
            event_processor: Optional event processor (will create default if None)
        """
        self.config = config

        # Initialize Redis for SM
        self.redis = redis.from_url(config.redis_url)

        # Initialize LM store
        self.lm_store = LongTermMemoryStore(config)

        # Initialize event processor
        self.event_processor = event_processor

        logger.info(f"MemoryManager initialized with Redis: {config.redis_url}")

    def set_event_processor(self, event_processor: EventProcessor) -> None:
        """Set the event processor (for dependency injection)."""
        self.event_processor = event_processor

    async def get_or_create_session_context(
        self, tenant_id: str, user_id: str, session_id: str
    ) -> ShortTermMemory:
        """
        Get existing SM or create new one (with LM reconstruction if expired).
        Implements the core memory workflow from architecture diagram.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            session_id: Current session identifier

        Returns:
            ShortTermMemory ready for use
        """
        try:
            # Try to load existing SM
            sm = await self._load_sm(tenant_id, user_id)

            if sm is not None and not self._is_sm_expired(sm):
                logger.info(f"Loaded existing SM for {tenant_id}:{user_id}")
                # Update session_id if different
                if sm.session_id != session_id:
                    sm.session_id = session_id
                    await self._save_sm(sm)
                return sm

            # SM expired or doesn't exist - reconstruct from LM
            logger.info(
                f"SM expired/missing for {tenant_id}:{user_id}, reconstructing from LM"
            )

            # Load LM events
            lm = await self.lm_store.load_memory(tenant_id, user_id)

            # Create new SM with LM context
            sm = await self._create_sm_from_lm(tenant_id, user_id, session_id, lm)

            # Save the new SM
            await self._save_sm(sm)

            logger.info(f"Created new SM for {tenant_id}:{user_id} from LM context")
            return sm

        except Exception as e:
            logger.error(
                f"Error getting session context for {tenant_id}:{user_id}: {e}"
            )
            # Return minimal SM as fallback
            return ShortTermMemory(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id,
                summary="",
                state="awaiting_input",
                last_intent=None,
                expires_at=None,
            )

    async def add_message_to_context(
        self,
        tenant_id: str,
        user_id: str,
        message: str,
        role: str = "user",
        metadata: dict[str, Any] | None = None,
    ) -> ShortTermMemory | None:
        """
        Add a message to SM and process for LM if important.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            message: Message content
            role: Message role (user/bot)
            metadata: Additional metadata

        Returns:
            Updated ShortTermMemory
        """
        try:
            # Get current SM
            sm = await self._load_sm(tenant_id, user_id)
            if sm is None:
                logger.warning(
                    f"No SM found for {tenant_id}:{user_id} when adding message"
                )
                return None

            # Add message to history
            sm.history.append({"role": role, "message": message})
            sm.updated_at = datetime.now(UTC)

            # Limit history size for efficiency
            max_history = 20
            if len(sm.history) > max_history:
                sm.history = sm.history[-max_history:]

            # Process user messages for LM and update state/intent
            if role == "user" and self.event_processor:
                event = await self._process_message_for_lm(
                    tenant_id, user_id, message, sm, metadata
                )

                # Update state and intent from new event
                if event:
                    sm.last_intent = event.event_type.value

                    # Determine state from event context
                    event_context = event.payload.get("context", {})
                    new_state = event_context.get("current_state", "awaiting_input")

                    # If no state in event context, infer from event type
                    if new_state == "awaiting_input":
                        event_type = event.event_type.value
                        if event_type == "TRANSACTION":
                            new_state = "awaiting_confirmation"
                        elif event_type == "REQUEST":
                            new_state = "processing_request"
                        elif event_type == "INQUIRY":
                            new_state = "awaiting_response"

                    sm.state = new_state

            # Save updated SM
            await self._save_sm(sm)

            logger.debug(f"Added {role} message to SM for {tenant_id}:{user_id}")
            return sm

        except Exception as e:
            logger.error(f"Error adding message for {tenant_id}:{user_id}: {e}")
            return None

    async def update_session_variables(
        self, tenant_id: str, user_id: str, variables: dict[str, Any]
    ) -> bool:
        """
        Update session variables in SM.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            variables: Variables to update

        Returns:
            True if successful
        """
        try:
            sm = await self._load_sm(tenant_id, user_id)
            if sm is None:
                return False

            sm.variables.update(variables)
            sm.updated_at = datetime.now(UTC)

            await self._save_sm(sm)
            logger.debug(f"Updated variables for {tenant_id}:{user_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating variables for {tenant_id}:{user_id}: {e}")
            return False

    async def get_context_for_llm(
        self,
        tenant_id: str,
        user_id: str,
        include_summary: bool = True,
        max_recent_messages: int = 10,
    ) -> dict[str, Any]:
        """
        Get formatted context for LLM prompts.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            include_summary: Whether to include LM summary
            max_recent_messages: Max recent messages to include

        Returns:
            Context dictionary for LLM
        """
        try:
            sm = await self._load_sm(tenant_id, user_id)
            if sm is None:
                return {"error": "No session context found"}

            context = {
                "recent_messages": sm.history[-max_recent_messages:],
                "current_state": sm.state,
                "last_intent": sm.last_intent,
                "session_variables": sm.variables,
            }

            if include_summary and sm.summary:
                context["conversation_summary"] = sm.summary

            # Add LM attributes if available
            lm = await self.lm_store.load_memory(tenant_id, user_id)
            if lm:
                context["user_attributes"] = lm.attributes
                context["history_summary"] = lm.history_summary

                # Add recent important events
                important_events = lm.get_important_events(min_score=0.7)
                if important_events:
                    context["important_events"] = [
                        {
                            "type": event.event_type.value,
                            "payload": event.payload,
                            "timestamp": event.timestamp.isoformat(),
                            "importance": event.importance_score,
                        }
                        for event in important_events[-5:]  # Last 5 important events
                    ]

            return context

        except Exception as e:
            logger.error(f"Error getting LLM context for {tenant_id}:{user_id}: {e}")
            return {"error": str(e)}

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired SM sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            # This is a simplified cleanup - in production you'd want to
            # scan Redis keys with a pattern like "sm:*:*"
            cleaned = 0
            logger.info(f"Session cleanup completed: {cleaned} sessions removed")
            return cleaned

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0

    async def close(self) -> None:
        """Close Redis connections."""
        if self.redis:
            await self.redis.close()

    # Private methods

    def _get_sm_key(self, tenant_id: str, user_id: str) -> str:
        """Get Redis key for SM."""
        return f"sm:{tenant_id}:{user_id}"

    async def _load_sm(self, tenant_id: str, user_id: str) -> ShortTermMemory | None:
        """Load SM from Redis."""
        try:
            key = self._get_sm_key(tenant_id, user_id)
            data = await self.redis.get(key)

            if data is None:
                return None

            # Parse JSON and create SM object
            import json

            sm_dict = json.loads(data)

            # Convert datetime strings back to datetime objects
            for field in ["created_at", "updated_at", "expires_at"]:
                if field in sm_dict and sm_dict[field]:
                    sm_dict[field] = datetime.fromisoformat(
                        sm_dict[field].replace("Z", "+00:00")
                    )

            return ShortTermMemory(**sm_dict)

        except Exception as e:
            logger.error(f"Error loading SM for {tenant_id}:{user_id}: {e}")
            return None

    async def _save_sm(self, sm: ShortTermMemory) -> bool:
        """Save SM to Redis."""
        try:
            key = self._get_sm_key(sm.tenant_id, sm.user_id)

            # Convert to JSON
            import json

            data = sm.model_dump()

            # Convert datetime objects to ISO strings
            for field in ["created_at", "updated_at", "expires_at"]:
                if field in data and data[field] and isinstance(data[field], datetime):
                    data[field] = data[field].isoformat()

            # Save with TTL
            await self.redis.set(
                key, json.dumps(data, ensure_ascii=False), ex=self.config.sm_ttl
            )

            return True

        except Exception as e:
            logger.error(f"Error saving SM for {sm.tenant_id}:{sm.user_id}: {e}")
            return False

    def _is_sm_expired(self, sm: ShortTermMemory) -> bool:
        """Check if SM is expired."""
        if sm.expires_at is None:
            # Use TTL-based expiry check
            time_since_update = datetime.now(UTC) - sm.updated_at
            return time_since_update.total_seconds() > self.config.sm_ttl

        return datetime.now(UTC) > sm.expires_at

    async def _create_sm_from_lm(
        self, tenant_id: str, user_id: str, session_id: str, lm: LongTermMemory | None
    ) -> ShortTermMemory:
        """Create new SM with context from LM."""
        sm = ShortTermMemory(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            summary="",
            state="awaiting_input",
            last_intent=None,
            expires_at=datetime.now(UTC) + timedelta(seconds=self.config.sm_ttl),
        )

        if lm:
            # Use LM summary as SM summary
            sm.summary = lm.history_summary

            # Copy relevant attributes to variables
            if lm.attributes:
                sm.variables.update(
                    {"user_preferences": lm.attributes, "has_history": True}
                )

            # Set state and intent based on recent events
            recent_events = lm.get_recent_events(5)
            if recent_events:
                last_event = recent_events[-1]
                sm.last_intent = last_event.event_type.value

                # Determine state from event context
                event_context = last_event.payload.get("context", {})
                sm.state = event_context.get("current_state", "awaiting_input")

                # If no state in event, infer from event type
                if sm.state == "awaiting_input":
                    event_type = last_event.event_type.value
                    if event_type == "TRANSACTION":
                        sm.state = "awaiting_confirmation"
                    elif event_type == "REQUEST":
                        sm.state = "processing_request"
                    elif event_type == "INQUIRY":
                        sm.state = "awaiting_response"

                sm.variables["recent_activity"] = [
                    event.event_type.value for event in recent_events
                ]

        return sm

    async def _process_message_for_lm(
        self,
        tenant_id: str,
        user_id: str,
        message: str,
        sm: ShortTermMemory,
        metadata: dict[str, Any] | None,
    ) -> Any | None:
        """Process user message for potential LM storage.

        Returns:
            Event object if processed successfully, None otherwise
        """
        try:
            if not self.event_processor:
                logger.warning("No event processor available for LM processing")
                return None

            # Create context for event processing
            context = {
                **(metadata or {}),
                "session_variables": sm.variables,
                "current_state": sm.state,
                "last_intent": sm.last_intent,
                "conversation_length": len(sm.history),
            }

            # Analyze message with LLM
            event = await self.event_processor.create_event(message, context)

            # Save to LM if important enough
            if event.importance_score >= self.config.importance_threshold:
                await self.lm_store.add_event(tenant_id, user_id, event)
                logger.info(
                    f"Saved important event to LM: {event.event_type.value} "
                    f"(score: {event.importance_score:.2f})"
                )

            return event

        except Exception as e:
            logger.error(f"Error processing message for LM: {e}")
            return None


class MemoryManagerFactory:
    """Factory for creating MemoryManager instances."""

    @staticmethod
    async def create_from_config(config_dict: dict[str, Any]) -> MemoryManager:
        """
        Create MemoryManager from configuration dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Configured MemoryManager instance
        """
        # Create memory config
        memory_config = MemoryConfig(
            redis_url=config_dict["memory"]["redis_url"],
            lm_base_path=config_dict["memory"].get("lm_base_path", "data/longterm"),
            sm_ttl=config_dict["memory"].get("sm_ttl", 1800),
            max_events_per_user=config_dict["memory"].get("max_events_per_user", 1000),
            event_retention_days=config_dict["memory"].get("event_retention_days", 365),
            importance_threshold=config_dict["memory"].get("importance_threshold", 0.5),
            summary_trigger_events=config_dict["memory"].get(
                "summary_trigger_events", 50
            ),
        )

        # Create event processor
        event_processor = EventProcessorFactory.create_from_config(config_dict)

        # Create memory manager
        manager = MemoryManager(memory_config, event_processor)

        return manager

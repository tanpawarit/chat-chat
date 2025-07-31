"""
Session Manager with Memory System Integration.
Manages user sessions and conversation state with SM/LM integration.
"""

import logging
from datetime import UTC, datetime
from typing import Any

from memory.memory_manager import MemoryManager
from models.memory import ShortTermMemory
from models.session import Session, SessionContext, SessionState

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages user sessions with integrated memory system.
    Acts as a bridge between the existing session models and new memory system.
    """

    def __init__(self, memory_manager: MemoryManager):
        """
        Initialize session manager.

        Args:
            memory_manager: Integrated memory management system
        """
        self.memory_manager = memory_manager
        self._active_sessions: dict[str, Session] = {}

        logger.info("SessionManager initialized with memory integration")

    async def get_or_create_session(
        self, user_id: str, platform: str, tenant_id: str, session_id: str | None = None
    ) -> Session:
        """
        Get existing session or create new one with memory context.

        Args:
            user_id: User identifier
            platform: Platform name (line, facebook, etc.)
            tenant_id: Tenant/store identifier
            session_id: Optional existing session ID

        Returns:
            Session object with memory context loaded
        """
        try:
            # Generate session key
            session_key = f"{tenant_id}:{user_id}:{platform}"

            # Check for existing active session
            if session_key in self._active_sessions:
                session = self._active_sessions[session_key]
                if session.state == SessionState.ACTIVE:
                    logger.debug(f"Returning existing session for {session_key}")
                    return session

            # Create or load session with memory context
            if session_id is None:
                session_id = self._generate_session_id(user_id, platform)

            # Get memory context (this handles SM/LM workflow)
            sm = await self.memory_manager.get_or_create_session_context(
                tenant_id, user_id, session_id
            )

            # Create session object from memory context
            session = self._create_session_from_memory(
                session_id, user_id, platform, sm
            )

            # Store in active sessions
            self._active_sessions[session_key] = session

            logger.info(f"Created/loaded session {session_id} for {session_key}")
            return session

        except Exception as e:
            logger.error(f"Error getting session for {user_id}@{platform}: {e}")
            # Return minimal session as fallback
            return Session(
                session_id=session_id or self._generate_session_id(user_id, platform),
                user_id=user_id,
                platform=platform,
                state=SessionState.ACTIVE,
                expires_at=None,
                has_memory_context=False,
                memory_summary="",
                tenant_id=None,
                total_messages=0,
            )

    async def add_message(
        self,
        session: Session,
        message: str,
        role: str = "user",
        tenant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Session:
        """
        Add message to session and update memory.

        Args:
            session: Current session
            message: Message content
            role: Message role (user/bot)
            tenant_id: Tenant identifier (required for memory)
            metadata: Additional message metadata

        Returns:
            Updated session
        """
        try:
            if not tenant_id:
                logger.warning("No tenant_id provided for memory integration")
                # Fallback to basic session update
                session.message_history.append(message)
                session.total_messages += 1
                session.last_activity = datetime.now(UTC)
                return session

            # Update memory system
            sm = await self.memory_manager.add_message_to_context(
                tenant_id, session.user_id, message, role, metadata
            )

            if sm:
                # Update session from memory
                session = self._update_session_from_memory(session, sm)

            # Update session metadata
            session.total_messages += 1
            session.last_activity = datetime.now(UTC)
            session.updated_at = datetime.now(UTC)

            logger.debug(f"Added {role} message to session {session.session_id}")
            return session

        except Exception as e:
            logger.error(f"Error adding message to session {session.session_id}: {e}")
            return session

    async def update_context(
        self, session: Session, tenant_id: str, **context_updates
    ) -> Session:
        """
        Update session context and memory variables.

        Args:
            session: Current session
            tenant_id: Tenant identifier
            **context_updates: Context fields to update

        Returns:
            Updated session
        """
        try:
            # Update session context
            for key, value in context_updates.items():
                if hasattr(session.context, key):
                    setattr(session.context, key, value)

            # Update memory variables
            memory_variables = {
                key: value
                for key, value in context_updates.items()
                if key
                in ["current_topic", "intent", "current_step", "language", "timezone"]
            }

            if memory_variables:
                await self.memory_manager.update_session_variables(
                    tenant_id, session.user_id, memory_variables
                )

            session.updated_at = datetime.now(UTC)

            logger.debug(f"Updated context for session {session.session_id}")
            return session

        except Exception as e:
            logger.error(f"Error updating session context: {e}")
            return session

    async def get_llm_context(
        self,
        session: Session,
        tenant_id: str,
        include_summary: bool = True,
        max_recent_messages: int = 10,
    ) -> dict[str, Any]:
        """
        Get formatted context for LLM from memory system.

        Args:
            session: Current session
            tenant_id: Tenant identifier
            include_summary: Include conversation summary
            max_recent_messages: Max recent messages to include

        Returns:
            LLM context dictionary
        """
        try:
            context = await self.memory_manager.get_context_for_llm(
                tenant_id, session.user_id, include_summary, max_recent_messages
            )

            # Add session-specific context
            context.update(
                {
                    "session_id": session.session_id,
                    "platform": session.platform,
                    "session_state": session.state.value,
                    "total_messages": session.total_messages,
                    "session_context": {
                        "current_topic": session.context.current_topic,
                        "intent": session.context.intent,
                        "current_step": session.context.current_step,
                        "language": session.context.language,
                        "timezone": session.context.timezone,
                    },
                }
            )

            return context

        except Exception as e:
            logger.error(
                f"Error getting LLM context for session {session.session_id}: {e}"
            )
            return {"error": str(e)}

    async def end_session(self, session: Session, tenant_id: str | None = None) -> None:
        """
        End a session and clean up.

        Args:
            session: Session to end
            tenant_id: Tenant identifier (for memory cleanup)
        """
        try:
            session.state = SessionState.ENDED
            session.updated_at = datetime.now(UTC)

            # Remove from active sessions
            session_key = (
                f"{tenant_id or 'unknown'}:{session.user_id}:{session.platform}"
            )
            if session_key in self._active_sessions:
                del self._active_sessions[session_key]

            logger.info(f"Ended session {session.session_id}")

        except Exception as e:
            logger.error(f"Error ending session {session.session_id}: {e}")

    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        try:
            cleaned_count = 0
            expired_keys = []

            # Find expired sessions
            for key, session in self._active_sessions.items():
                if session.state == SessionState.EXPIRED:
                    expired_keys.append(key)

            # Remove expired sessions
            for key in expired_keys:
                del self._active_sessions[key]
                cleaned_count += 1

            # Also cleanup memory system
            memory_cleaned = await self.memory_manager.cleanup_expired_sessions()

            logger.info(
                f"Cleaned up {cleaned_count} sessions, {memory_cleaned} memory entries"
            )
            return cleaned_count

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            return 0

    async def close(self) -> None:
        """Close session manager and memory connections."""
        try:
            await self.memory_manager.close()
            self._active_sessions.clear()
            logger.info("SessionManager closed")
        except Exception as e:
            logger.error(f"Error closing SessionManager: {e}")

    # Private helper methods

    def _generate_session_id(self, user_id: str, platform: str) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"sess_{platform}_{user_id[:8]}_{timestamp}"

    def _create_session_from_memory(
        self, session_id: str, user_id: str, platform: str, sm: ShortTermMemory
    ) -> Session:
        """Create Session object from ShortTermMemory."""
        # Extract recent message IDs (simplified - in production you'd store actual IDs)
        message_history = [f"msg_{i}" for i in range(len(sm.history))]

        # Create session context from memory
        context = SessionContext(
            current_topic=sm.variables.get("current_topic"),
            intent=sm.last_intent,
            entities=sm.variables.get("entities", {}),
            variables=sm.variables,
            current_step=sm.variables.get("current_step"),
            flow_data=sm.variables.get("flow_data", {}),
            language=sm.variables.get("language", "en"),
            timezone=sm.variables.get("timezone", "UTC"),
        )

        return Session(
            session_id=session_id,
            user_id=user_id,
            platform=platform,
            state=SessionState.ACTIVE,
            created_at=sm.created_at,
            updated_at=sm.updated_at,
            expires_at=sm.expires_at,
            context=context,
            message_history=message_history,
            total_messages=len(sm.history),
            has_memory_context=bool(sm.summary),
            memory_summary=sm.summary,
            tenant_id=sm.tenant_id,
        )

    def _update_session_from_memory(
        self, session: Session, sm: ShortTermMemory
    ) -> Session:
        """Update Session object from ShortTermMemory."""
        # Update context from memory
        session.context.current_topic = sm.variables.get("current_topic")
        session.context.intent = sm.last_intent
        session.context.variables.update(sm.variables)

        # Update message history (simplified)
        session.message_history = [f"msg_{i}" for i in range(len(sm.history))]
        session.total_messages = len(sm.history)
        session.updated_at = sm.updated_at

        return session

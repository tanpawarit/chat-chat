"""
Central bot gateway for handling normalized messages from all platforms with memory support.
"""

import logging
from typing import Any

from models.message import IncomingMessage, MessageType, OutgoingMessage
from models.user import User

logger = logging.getLogger(__name__)


class BotGateway:
    """Central gateway for processing messages from all platforms with memory support."""

    def __init__(self, memory_manager=None, llm_service=None):
        """
        Initialize the bot gateway.
        
        Args:
            memory_manager: Optional MemoryManager instance for conversation persistence
            llm_service: Optional LLMService instance for intelligent responses
        """
        self.memory_manager = memory_manager
        self.llm_service = llm_service

    async def handle_message(
        self, message: IncomingMessage, user: User, store=None
    ) -> OutgoingMessage:
        """
        Handle incoming message with memory and LLM support.

        Args:
            message: Normalized incoming message
            user: User who sent the message
            store: Store context (optional)

        Returns:
            Normalized outgoing message response
        """
        # Debug logging
        logger.info(f"Processing message from {user.store_id}:{user.customer_id}")
        logger.debug(f"Message type: {message.message_type.value}, Text: {message.text}")

        try:
            # Extract identifiers
            tenant_id = user.store_id or "default_store"
            user_id = user.customer_id or user.platform_user_id
            session_id = f"session_{user.platform_user_id}"

            store_name = store.name if store else "Chat Bot"
            user_name = user.profile.display_name if user.profile else "คุณลูกค้า"

            # Handle non-text messages first
            if message.message_type != MessageType.TEXT or not message.text:
                response_text = await self._handle_non_text_message(message, store_name)
                return self._create_response(response_text)

            # Check for system warning messages (pass through as-is)
            if self._is_system_warning(message.text):
                return self._create_response(message.text)

            # Memory-powered conversation flow
            if self.memory_manager:
                try:
                    # Get or create session context
                    await self.memory_manager.get_or_create_session_context(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        session_id=session_id
                    )
                    logger.info(f"Loaded session context for {tenant_id}:{user_id}")

                    # Add user message to memory
                    await self.memory_manager.add_message_to_context(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        message=message.text,
                        role="user",
                        metadata={
                            "platform": message.platform,
                            "timestamp": message.timestamp.isoformat(),
                            "store_name": store_name,
                            "user_name": user_name
                        }
                    )

                    # Get memory context for LLM
                    memory_context = await self.memory_manager.get_context_for_llm(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        include_summary=True,
                        max_recent_messages=10
                    )

                    # Generate intelligent response using LLM
                    if self.llm_service:
                        response_text = await self.llm_service.generate_response(
                            user_message=message.text,
                            memory_context=memory_context
                        )
                    else:
                        # Fallback response if no LLM service
                        response_text = f"สวัสดีครับ/ค่ะ จาก {store_name}! ได้รับข้อความของท่านแล้ว: {message.text}"

                    # Add bot response to memory
                    await self.memory_manager.add_message_to_context(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        message=response_text,
                        role="bot",
                        metadata={
                            "generated_by": "llm_service",
                            "model_used": "openai/gpt-4o-mini"
                        }
                    )

                    logger.info(f"Generated response for {tenant_id}:{user_id}: {len(response_text)} chars")

                except Exception as e:
                    logger.error(f"Memory system error: {e}")
                    # Fallback to simple response
                    response_text = f"สวัสดีครับ/ค่ะ จาก {store_name}! ได้รับข้อความของท่านแล้ว"

            else:
                # No memory system - simple response
                response_text = f"สวัสดีครับ/ค่ะ จาก {store_name}! ท่านส่งข้อความว่า: {message.text}"

            return self._create_response(response_text)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Error fallback
            return self._create_response("ขออภัยครับ/ค่ะ เกิดข้อผิดพลาดชั่วคราว กรุณาลองใหม่อีกครั้งนะคะ")

    async def _handle_non_text_message(self, message: IncomingMessage, store_name: str) -> str:
        """Handle non-text messages (stickers, images, etc.)."""
        message_type_responses = {
            MessageType.STICKER: f"ได้รับสติกเกอร์จาก {store_name} แล้วครับ/ค่ะ! 😊",
            MessageType.IMAGE: f"ได้รับรูปภาพจาก {store_name} แล้วครับ/ค่ะ! 📷",
            MessageType.VIDEO: f"ได้รับวิดีโอจาก {store_name} แล้วครับ/ค่ะ! 🎥",
            MessageType.AUDIO: f"ได้รับข้อความเสียงจาก {store_name} แล้วครับ/ค่ะ! 🎵",
            MessageType.LOCATION: f"ได้รับตำแหน่งที่ตั้งจาก {store_name} แล้วครับ/ค่ะ! 📍",
        }

        return message_type_responses.get(
            message.message_type,
            f"ได้รับข้อความจาก {store_name} แล้วครับ/ค่ะ"
        )

    def _is_system_warning(self, text: str) -> bool:
        """Check if message is a system warning that should be passed through."""
        warning_prefixes = [
            "ข้อความของคุณยาวเกินไป",
            "ไฟล์ของคุณใหญ่เกินไป",
            "รูปภาพของคุณใหญ่เกินไป",
            "วิดีโอของคุณใหญ่เกินไป",
            "ไฟล์เสียงของคุณใหญ่เกินไป"
        ]
        return any(text.startswith(prefix) for prefix in warning_prefixes)

    def _create_response(self, text: str) -> OutgoingMessage:
        """Create standardized outgoing message."""
        return OutgoingMessage(
            message_type=MessageType.TEXT,
            text=text,
            media=None,
            location=None,
            quick_replies=None,
        )

    def get_status(self) -> dict[str, Any]:
        """
        Get gateway status information.

        Returns:
            Dictionary containing gateway status
        """
        return {
            "status": "active",
            "version": "1.0.0",
            "features": ["text_messaging", "media_detection", "echo_responses"],
        }

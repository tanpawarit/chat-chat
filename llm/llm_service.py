"""
LLM Service for generating context-aware responses using OpenRouter API.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

logger = logging.getLogger(__name__)


class LLMService:
    """Service for generating intelligent responses using LLM with memory context."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the LLM service.

        Args:
            api_key: OpenRouter API key
            model: Model to use for response generation
            base_url: OpenRouter base URL
        """
        self.llm = ChatOpenAI(
            api_key=SecretStr(api_key),
            model=model,
            base_url=base_url,
            temperature=0.7,  # More creative for conversation
        )

    async def generate_response(
        self,
        user_message: str,
        memory_context: dict[str, Any],
    ) -> str:
        """
        Generate a response using LLM with memory context.

        Args:
            user_message: The user's message
            memory_context: Memory context from MemoryManager

        Returns:
            Generated response text
        """
        try:
            # Build system prompt
            system_prompt = self._build_system_prompt(memory_context)

            # Build user prompt with context
            user_prompt = self._build_user_prompt(user_message, memory_context)

            # Log complete prompts for debugging
            print("=" * 80)
            print("🤖 COMPLETE LLM PROMPT SENT TO API")
            print("=" * 80)
            print("📋 SYSTEM PROMPT:")
            print("-" * 40)
            print(system_prompt)
            print("-" * 40)
            print("👤 USER PROMPT:")
            print("-" * 40)
            print(user_prompt)
            print("=" * 80)

            # Create messages
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            # Get LLM response
            response = await self.llm.ainvoke(messages)

            # Extract text content
            response_text = self._extract_text_content(response.content)

            return response_text.strip()

        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            # Fallback response
            return "ขออพ็ยครับ/ค่ะ เกิดข้อผิดพลาดเล็กน้อย กรุณาลองใหม่อีกครั้งนะคะ"

    def _build_system_prompt(self, memory_context: dict[str, Any]) -> str:
        """Build system prompt with memory context."""

        # Base personality
        system_prompt = """คุณเป็นพนักงานบริการลูกค้าที่เป็นมิตรและช่วยเหลือดี

                        คุณควร:
                        - ตอบด้วยภาษาไทยที่สุภาพและเป็นมิตร
                        - ใช้คำสุภาพ เช่น "ค่ะ" ให้เหมาะสมกับบริบท
                        - แสดงความสนใจและเอาใจใส่ลูกค้า
                        - ให้ข้อมูลที่ถูกต้องและเป็นประโยชน์
                        - หากไม่แน่ใจ ให้บอกว่าจะไปสอบถามเพิ่มเติม
                        """

        # Add user preferences if available
        if memory_context.get("user_attributes"):
            attributes = memory_context["user_attributes"]
            system_prompt += "\n\nข้อมูลลูกค้า:\n"

            if attributes.get("preferred_language"):
                system_prompt += f"- ภาษาที่ใช้: {attributes['preferred_language']}\n"

            if attributes.get("customer_segment"):
                system_prompt += f"- ประเภทลูกค้า: {attributes['customer_segment']}\n"

            if attributes.get("timezone"):
                system_prompt += f"- เขตเวลา: {attributes['timezone']}\n"

        # Add conversation summary if available
        if memory_context.get("history_summary"):
            system_prompt += (
                f"\n\nสรุปการสนทนาที่ผ่านมา:\n{memory_context['history_summary']}\n"
            )

        # Add important events context
        if memory_context.get("important_events"):
            system_prompt += "\n\nเหตุการณ์สำคัญที่ผ่านมา:\n"
            for event in memory_context["important_events"][
                -3:
            ]:  # Last 3 important events
                event_type = event["type"]
                timestamp = event["timestamp"]
                payload = event.get("payload", {})
                if payload and isinstance(payload, dict):
                    # Extract meaningful content from payload
                    content_parts = []

                    # For REQUEST events
                    if event_type == "REQUEST":
                        if payload.get("original_message"):
                            content_parts.append(
                                f"ข้อความ: '{payload['original_message']}'"
                            )
                        if payload.get("request_type"):
                            content_parts.append(f"ประเภท: {payload['request_type']}")
                        if payload.get("specifics"):
                            content_parts.append(f"รายละเอียด: {payload['specifics']}")
                        if payload.get("urgency"):
                            content_parts.append(f"ความเร่งด่วน: {payload['urgency']}")

                    # For TRANSACTION events
                    elif event_type == "TRANSACTION":
                        if payload.get("original_message"):
                            content_parts.append(
                                f"ข้อความ: '{payload['original_message']}'"
                            )
                        if payload.get("transaction_type"):
                            content_parts.append(
                                f"ประเภท: {payload['transaction_type']}"
                            )
                        if payload.get("stage"):
                            content_parts.append(f"ขั้นตอน: {payload['stage']}")
                        if payload.get("amount_mentioned"):
                            content_parts.append(
                                f"จำนวน: {payload['amount_mentioned']}"
                            )

                    # Generic fallback for other fields
                    else:
                        if payload.get("original_message"):
                            content_parts.append(
                                f"ข้อความ: '{payload['original_message']}'"
                            )
                        if payload.get("description"):
                            content_parts.append(payload["description"])

                    if content_parts:
                        system_prompt += f"- {event_type}: {', '.join(content_parts)} ({timestamp})\n"
                    else:
                        system_prompt += f"- {event_type}: {timestamp}\n"
                else:
                    system_prompt += f"- {event_type}: {timestamp}\n"

        return system_prompt

    def _build_user_prompt(
        self, user_message: str, memory_context: dict[str, Any]
    ) -> str:
        """Build user prompt with recent conversation context."""

        prompt_parts = []

        # Add recent conversation if available
        recent_messages = memory_context.get("recent_messages", [])
        if recent_messages:
            prompt_parts.append("บทสนทนาล่าสุด:")
            for msg in recent_messages[-5:]:  # Last 5 messages
                role = "ลูกค้า" if msg["role"] == "user" else "พนักงาน"
                prompt_parts.append(f"{role}: {msg['message']}")
            prompt_parts.append("")

        # Add current state if available
        if memory_context.get("current_state"):
            prompt_parts.append(f"สถานะปัจจุบัน: {memory_context['current_state']}")

        # Add session variables if available
        session_vars = memory_context.get("session_variables", {})
        if session_vars.get("current_topic"):
            prompt_parts.append(f"หัวข้อปัจจุบัน: {session_vars['current_topic']}")

        # Add the new user message
        prompt_parts.append(f"\nลูกค้า ส่งข้อความใหม่: {user_message}")
        prompt_parts.append("\nกรุณาตอบกลับอย่างเหมาะสม:")

        return "\n".join(prompt_parts)

    def _extract_text_content(self, content) -> str:
        """Extract text content from LLM response."""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                else:
                    text_parts.append(str(item))
            return " ".join(text_parts)

        return str(content)

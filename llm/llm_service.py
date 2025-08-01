"""
LLM Service for generating context-aware responses using OpenRouter API.
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from llm.config import LLMConfig
from llm.prompt_templates import ContextInjector

logger = logging.getLogger(__name__)


class LLMService:
    """Service for generating intelligent responses using LLM with memory context."""

    def __init__(
        self,
        api_key: str,
        model: str = LLMConfig.DEFAULT_RESPONSE_MODEL,
        base_url: str = LLMConfig.DEFAULT_BASE_URL,
        temperature: float = LLMConfig.RESPONSE_GENERATION_TEMPERATURE,
    ):
        """
        Initialize the LLM service.

        Args:
            api_key: OpenRouter API key
            model: Model to use for response generation
            base_url: OpenRouter base URL
            temperature: Temperature for LLM responses
        """
        self.llm = ChatOpenAI(
            api_key=SecretStr(api_key),
            model=model,
            base_url=base_url,
            temperature=temperature,  # Temperature from config
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
        """Build AI-optimized system prompt with structured context injection."""

        # Start with base AI-optimized system prompt
        system_prompt_parts = [LLMConfig.RESPONSE_GENERATION_SYSTEM_PROMPT]

        # Add user profile context if available
        user_profile_context = ContextInjector.build_user_profile_context(memory_context)
        if user_profile_context:
            system_prompt_parts.append(user_profile_context)

        # Add conversation history and important events context
        conversation_context = ContextInjector.build_conversation_history(memory_context)
        if conversation_context:
            system_prompt_parts.append(conversation_context)

        return "\n\n".join(system_prompt_parts)

    def _build_user_prompt(
        self, user_message: str, memory_context: dict[str, Any]
    ) -> str:
        """Build structured user prompt with current request context."""

        # Use the AI-optimized current request builder
        return ContextInjector.build_current_request(user_message)

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

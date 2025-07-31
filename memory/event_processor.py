"""
LLM-based event processing and importance scoring for memory system.
Uses OpenRouter + LangChain for intelligent event classification and extraction.
"""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from models.memory import EventType, MemoryEvent

logger = logging.getLogger(__name__)


def extract_text_content(content: str | list[str | dict[str, Any]]) -> str:
    """Extract text content from LangChain message content.

    Args:
        content: The content from a LangChain message response

    Returns:
        str: The extracted text content
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                # Handle different content block types
                if item.get("type") == "text" and "text" in item:
                    text_parts.append(item["text"])
                elif "content" in item:
                    text_parts.append(str(item["content"]))
                else:
                    # Fallback for other dict structures
                    text_parts.append(str(item))
        return " ".join(text_parts)

    return str(content)  # Fallback for any other type


class EventClassification(BaseModel):
    """Event classification result from LLM."""

    event_type: EventType = Field(description="Classified event type")
    importance_score: float = Field(
        ge=0.0, le=1.0, description="Importance score (0.0-1.0)"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Extracted event data"
    )
    reasoning: str = Field(description="LLM reasoning for classification")


class EventProcessor:
    """LLM-powered event processor for conversation analysis."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        """
        Initialize the event processor.

        Args:
            api_key: OpenRouter API key
            model: Model to use (default: gpt-4o-mini for cost efficiency)
            base_url: OpenRouter base URL
        """
        self.llm = ChatOpenAI(
            api_key=SecretStr(api_key),
            model=model,
            base_url=base_url,
            temperature=0.1,  # Low temperature for consistent classification
        )

        self.parser = JsonOutputParser(pydantic_object=EventClassification)

        # System prompt for event classification
        self.system_prompt = """You are an expert conversation analyst. Your task is to analyze user messages and classify them for a memory system.

Available Event Types:
- INQUIRY: Questions, requests for information
- FEEDBACK: Opinions, reviews, satisfaction/dissatisfaction
- REQUEST: Specific asks, bookings, assistance needs
- COMPLAINT: Problems, issues, dissatisfaction
- TRANSACTION: Purchase, payment, order-related
- SUPPORT: Help requests, guidance needs
- INFORMATION: Sharing information, providing details
- GENERIC_EVENT: General conversation, greetings, unclear intent

Importance Scoring Guidelines (0.0-1.0):
- 0.9-1.0: Critical issues, transactions, urgent complaints
- 0.7-0.8: Important requests, feedback, specific inquiries
- 0.5-0.6: General support, information requests
- 0.3-0.4: Casual inquiries, general information
- 0.1-0.2: Greetings, small talk, unclear messages

Payload Extraction:
Extract relevant information based on event type:
- For INQUIRY: question_type, topic, urgency
- For COMPLAINT: issue_type, severity, category
- For REQUEST: request_type, urgency, specifics
- For TRANSACTION: transaction_type, stage, amount_mentioned
- For FEEDBACK: sentiment, rating_implied, category
- For SUPPORT: help_type, complexity, topic
- For INFORMATION: info_type, category, relevance

Respond ONLY with valid JSON matching the EventClassification schema."""

    async def analyze_message(
        self, message: str, context: dict[str, Any] | None = None
    ) -> EventClassification:
        """
        Analyze a message using LLM to classify and extract information.

        Args:
            message: User message to analyze
            context: Additional context information

        Returns:
            EventClassification with type, importance, and payload
        """
        try:
            # Prepare the user prompt
            user_prompt = f"""Analyze this message:

Message: "{message}"

Context: {json.dumps(context or {}, ensure_ascii=False, indent=2)}

Classify the event type, calculate importance score (0.0-1.0), extract relevant payload data, and provide reasoning.

Respond with JSON only."""

            # Create messages
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=user_prompt),
            ]

            # Get LLM response
            response = await self.llm.ainvoke(messages)

            # Parse the response
            content_text = extract_text_content(response.content)
            result_dict = self.parser.parse(content_text)

            # Ensure all required fields are present with defaults if missing
            if "reasoning" not in result_dict:
                result_dict["reasoning"] = (
                    "LLM classification without explicit reasoning"
                )
            if "payload" not in result_dict:
                result_dict["payload"] = {}

            result = EventClassification(**result_dict)

            logger.info(
                f"LLM classified message as {result.event_type.value} "
                f"(importance: {result.importance_score:.2f})"
            )
            logger.debug(f"LLM reasoning: {result.reasoning}")

            return result

        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            # Fallback to basic classification
            return self._fallback_classification(message, context)

    async def create_event(
        self, message: str, context: dict[str, Any] | None = None
    ) -> MemoryEvent:
        """
        Create a complete MemoryEvent from a message using LLM analysis.

        Args:
            message: User message text
            context: Additional context information

        Returns:
            Complete MemoryEvent
        """
        # Analyze with LLM
        classification = await self.analyze_message(message, context)

        # Enhance payload with message metadata
        enhanced_payload = {
            **classification.payload,
            "original_message": message,
            "message_length": len(message),
            "language": self._detect_language(message),
            "llm_reasoning": classification.reasoning,
        }

        # Add context if provided
        if context:
            enhanced_payload["context"] = context

        # Create the event
        event = MemoryEvent(
            event_type=classification.event_type,
            payload=enhanced_payload,
            importance_score=classification.importance_score,
        )

        logger.info(
            f"Created event: {classification.event_type.value} "
            f"(importance: {classification.importance_score:.2f})"
        )

        return event

    async def summarize_events(
        self, events: list[MemoryEvent], current_summary: str = ""
    ) -> str:
        """
        Summarize a list of events for context compression.

        Args:
            events: List of events to summarize
            current_summary: Existing summary to update

        Returns:
            Updated summary text
        """
        if not events:
            return current_summary

        try:
            # Prepare events data for summarization
            events_data = []
            for event in events[-10:]:  # Last 10 events for efficiency
                events_data.append(
                    {
                        "type": event.event_type.value,
                        "importance": event.importance_score,
                        "message": event.payload.get("original_message", ""),
                        "timestamp": event.timestamp.isoformat(),
                        "key_data": {
                            k: v
                            for k, v in event.payload.items()
                            if k not in ["original_message", "llm_reasoning", "context"]
                        },
                    }
                )

            user_prompt = f"""Summarize the user's conversation history for memory system context.

Current Summary:
{current_summary}

Recent Events:
{json.dumps(events_data, ensure_ascii=False, indent=2)}

Create a concise summary (max 200 words) that captures:
1. Key patterns in user behavior
2. Important preferences or attributes
3. Recurring themes or issues
4. Current conversation context

Focus on information that would be useful for future conversations."""

            messages = [
                SystemMessage(
                    content="You are a conversation analyst creating concise memory summaries."
                ),
                HumanMessage(content=user_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            summary = extract_text_content(response.content).strip()

            logger.info(
                f"Generated summary of {len(events)} events ({len(summary)} chars)"
            )
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Fallback to basic summary
            return self._fallback_summary(events, current_summary)

    def _fallback_classification(
        self, message: str, context: dict[str, Any] | None = None
    ) -> EventClassification:
        """Fallback classification when LLM fails."""
        message_lower = message.lower()

        # Simple keyword-based fallback
        if any(word in message_lower for word in ["?", "ถาม", "สอบถาม", "how", "what"]):
            event_type = EventType.INQUIRY
            importance = 0.4
        elif any(word in message_lower for word in ["ร้องเรียน", "แย่", "เสีย", "problem"]):
            event_type = EventType.COMPLAINT
            importance = 0.8
        elif any(
            word in message_lower for word in ["ดี", "ชอบ", "good", "great", "ขอบคุณ"]
        ):
            event_type = EventType.FEEDBACK
            importance = 0.5
        elif any(
            word in message_lower for word in ["ซื้อ", "จ่าย", "buy", "pay", "order"]
        ):
            event_type = EventType.TRANSACTION
            importance = 0.9
        else:
            event_type = EventType.GENERIC_EVENT
            importance = 0.2

        return EventClassification(
            event_type=event_type,
            importance_score=importance,
            payload={"message": message, "classification_method": "fallback"},
            reasoning="Fallback classification due to LLM error",
        )

    def _fallback_summary(self, events: list[MemoryEvent], current_summary: str) -> str:
        """Fallback summary when LLM fails."""
        if not events:
            return current_summary

        # Basic summary based on event types and importance
        event_counts = {}
        important_events = []

        for event in events:
            event_counts[event.event_type.value] = (
                event_counts.get(event.event_type.value, 0) + 1
            )
            if event.importance_score > 0.7:
                important_events.append(event)

        summary_parts = [current_summary] if current_summary else []
        summary_parts.append(f"Recent activity: {len(events)} events")

        if event_counts:
            top_types = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            summary_parts.append(
                f"Main types: {', '.join([f'{t}({c})' for t, c in top_types])}"
            )

        if important_events:
            summary_parts.append(
                f"{len(important_events)} high-importance events recorded"
            )

        return " | ".join(summary_parts)

    def _detect_language(self, message: str) -> str:
        """Simple language detection."""
        import re

        thai_chars = re.findall(r"[\u0E00-\u0E7F]", message)
        return "th" if len(thai_chars) > len(message) * 0.3 else "en"


class EventProcessorFactory:
    """Factory for creating EventProcessor instances with different configurations."""

    @staticmethod
    def create_from_config(config: dict[str, Any]) -> EventProcessor:
        """
        Create EventProcessor from configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Configured EventProcessor instance
        """
        return EventProcessor(
            api_key=config["openrouter"]["api_key"],
            model=config.get("llm_model", "openai/gpt-4o-mini"),
            base_url=config.get("openrouter_base_url", "https://openrouter.ai/api/v1"),
        )

    @staticmethod
    def create_cheap(api_key: str) -> EventProcessor:
        """Create processor optimized for cost (fastest, cheapest model)."""
        return EventProcessor(
            api_key=api_key,
            model="openai/gpt-4o-mini",  # Most cost-effective
        )

    @staticmethod
    def create_accurate(api_key: str) -> EventProcessor:
        """Create processor optimized for accuracy (better model)."""
        return EventProcessor(
            api_key=api_key,
            model="openai/gpt-4o",  # More accurate
        )

    @staticmethod
    def create_fast(api_key: str) -> EventProcessor:
        """Create processor optimized for speed (fastest response)."""
        return EventProcessor(
            api_key=api_key,
            model="openai/gpt-3.5-turbo",  # Fastest
        )

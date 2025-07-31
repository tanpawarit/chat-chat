"""
LLM configuration utilities and defaults.
"""

from typing import Any


class LLMConfig:
    """Configuration settings for LLM services."""

    # Default models
    DEFAULT_EVENT_MODEL = "openai/gpt-4o-mini"  # Cost-effective for classification
    DEFAULT_RESPONSE_MODEL = "openai/gpt-4o-mini"  # Cost-effective for responses

    # Default settings
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    EVENT_PROCESSING_TEMPERATURE = 0.1  # Low for consistent classification
    RESPONSE_GENERATION_TEMPERATURE = 0.7  # More creative for conversation

    # System prompts
    EVENT_CLASSIFICATION_SYSTEM_PROMPT = """You are an expert conversation analyst. Your task is to analyze user messages and classify them for a memory system.

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

    RESPONSE_GENERATION_SYSTEM_PROMPT = """คุณเป็นพนักงานบริการลูกค้าที่เป็นมิตรและช่วยเหลือดี

                    คุณควร:
                    - ตอบด้วยภาษาไทยที่สุภาพและเป็นมิตร
                    - ใช้คำสุภาพ เช่น "ค่ะ" ให้เหมาะสมกับบริบท
                    - แสดงความสนใจและเอาใจใส่ลูกค้า
                    - ให้ข้อมูลที่ถูกต้องและเป็นประโยชน์
                    - หากไม่แน่ใจ ให้บอกว่าจะไปสอบถามเพิ่มเติม"""


def get_llm_config_from_dict(
    config: dict[str, Any], task: str = "event_processing"
) -> dict[str, Any]:
    """
    Extract LLM configuration from config for a specific task.

    Args:
        config: Configuration dictionary
        task: Task type (event_processing or response_generation)

    Returns:
        LLM-specific configuration
    """
    # Get LLM section or fallback to old structure
    llm_config = config.get("llm", {})

    if llm_config:
        # New structure - extract from llm section
        model = llm_config.get("models", {}).get(task, LLMConfig.DEFAULT_EVENT_MODEL)
        base_url = llm_config.get("base_url", LLMConfig.DEFAULT_BASE_URL)
        temperature = llm_config.get("temperatures", {}).get(
            task, LLMConfig.EVENT_PROCESSING_TEMPERATURE
        )
    else:
        # Fallback to old structure for backward compatibility
        model = config.get("llm_model", LLMConfig.DEFAULT_EVENT_MODEL)
        base_url = config.get("openrouter_base_url", LLMConfig.DEFAULT_BASE_URL)
        temperature = (
            LLMConfig.EVENT_PROCESSING_TEMPERATURE
            if task == "event_processing"
            else LLMConfig.RESPONSE_GENERATION_TEMPERATURE
        )

    return {
        "api_key": config["openrouter"]["api_key"],
        "model": model,
        "base_url": base_url,
        "temperature": temperature,
    }

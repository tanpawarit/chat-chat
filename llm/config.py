"""
LLM configuration utilities and defaults.
"""

from typing import Any

from llm.prompt_templates import (
    CUSTOMER_SERVICE_SYSTEM_PROMPT,
    EVENT_CLASSIFICATION_SYSTEM_PROMPT,
)


class LLMConfig:
    """Configuration settings for LLM services."""

    # Default models
    DEFAULT_EVENT_MODEL = "openai/gpt-4o-mini"  # Cost-effective for classification
    DEFAULT_RESPONSE_MODEL = "openai/gpt-4o-mini"  # Cost-effective for responses

    # Default settings
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    EVENT_PROCESSING_TEMPERATURE = 0.1  # Low for consistent classification
    RESPONSE_GENERATION_TEMPERATURE = 0.7  # More creative for conversation

    # System prompts (using AI-optimized templates)
    EVENT_CLASSIFICATION_SYSTEM_PROMPT = EVENT_CLASSIFICATION_SYSTEM_PROMPT
    RESPONSE_GENERATION_SYSTEM_PROMPT = CUSTOMER_SERVICE_SYSTEM_PROMPT


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

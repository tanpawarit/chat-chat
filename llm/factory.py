"""
Factory classes for creating LLM service instances with different configurations.
"""

from typing import Any

from llm.config import get_llm_config_from_dict


class EventProcessorFactory:
    """Factory for creating EventProcessor instances with different configurations."""

    @staticmethod
    def create_from_config(config: dict[str, Any], task: str = "event_processing"):
        """
        Create EventProcessor from configuration.

        Args:
            config: Configuration dictionary
            task: Task type for model selection

        Returns:
            Configured EventProcessor instance
        """
        # Import here to avoid circular imports
        from llm.event_processor import EventProcessor

        llm_config = get_llm_config_from_dict(config, task)
        return EventProcessor(**llm_config)


class LLMServiceFactory:
    """Factory for creating LLMService instances with different configurations."""

    @staticmethod
    def create_from_config(config: dict[str, Any], task: str = "response_generation"):
        """
        Create LLMService from configuration.

        Args:
            config: Configuration dictionary
            task: Task type for model selection

        Returns:
            Configured LLMService instance
        """
        # Import here to avoid circular imports
        from llm.llm_service import LLMService

        llm_config = get_llm_config_from_dict(config, task)
        return LLMService(**llm_config)

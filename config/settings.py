# Configuration settings for the chatbot application
# Includes environment variables, API keys, and general configuration

from pathlib import Path

import yaml


def load_config():
    """Load configuration from config.yaml file."""
    config_path = Path(__file__).parent.parent / "config.yaml"

    with open(config_path) as file:
        config = yaml.safe_load(file)

    return config

"""Configuration management for the example."""

import os


def load_config() -> dict:
    """Load and validate configuration from environment variables."""
    required_vars = {
        'AWS_REGION': 'region',
        'GOOGLE_CLIENT_ID': 'google_client_id',
        'GOOGLE_CLIENT_SECRET': 'google_client_secret',
        'CALLBACK_URL': 'callback_url'
    }
    
    config = {}
    for env_var, config_key in required_vars.items():
        value = os.getenv(env_var)
        if not value:
            raise ValueError(f"Missing required environment variable: {env_var}")
        config[config_key] = value
    
    return config

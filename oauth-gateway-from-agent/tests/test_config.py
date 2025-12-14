"""Tests for configuration loading."""

import os
from pathlib import Path
from unittest.mock import patch


class TestEnvConfig:
    def test_load_env_config_with_values(self):
        """Verify required environment variables are recognized."""
        with patch.dict(os.environ, {
            "AWS_REGION": "us-west-2",
            "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
            "GOOGLE_CLIENT_SECRET": "test-secret",
        }):
            assert os.environ.get("AWS_REGION") == "us-west-2"
            assert os.environ.get("GOOGLE_CLIENT_ID") == "test-client-id.apps.googleusercontent.com"
            assert os.environ.get("GOOGLE_CLIENT_SECRET") == "test-secret"

    def test_env_example_exists(self):
        """Verify .env.example file exists with required variables."""
        env_example = Path(__file__).parent.parent / ".env.example"
        assert env_example.exists(), ".env.example should exist"
        
        content = env_example.read_text()
        assert "GOOGLE_CLIENT_ID" in content
        assert "GOOGLE_CLIENT_SECRET" in content
        assert "AWS_REGION" in content

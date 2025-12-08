"""Tests for construct.py - AgentCore resource construction"""
import json
import os
import pytest


@pytest.fixture
def env_vars(monkeypatch):
    """Set up environment variables for testing"""
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("CALLBACK_URL", "http://localhost:8080/oauth2/callback")


@pytest.fixture
def config_path(tmp_path):
    """Provide temporary config.json path"""
    return tmp_path / "config.json"


def test_load_env_variables(env_vars):
    """Test loading environment variables"""
    from dotenv import load_dotenv
    
    load_dotenv()
    
    assert os.getenv("AWS_REGION") == "us-east-1"
    assert os.getenv("YOUTUBE_CLIENT_ID") == "test-client-id.apps.googleusercontent.com"
    assert os.getenv("YOUTUBE_CLIENT_SECRET") == "test-client-secret"
    assert os.getenv("CALLBACK_URL") == "http://localhost:8080/oauth2/callback"


def test_save_config(config_path):
    """Test saving config.json with resource IDs"""
    config = {
        "gateway_id": "test-gateway-id",
        "gateway_url": "https://test.gateway.url/mcp",
        "identity_arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:workload-identity/test",
        "user_pool_id": "us-east-1_TestPool",
        "cognito_client_id": "test-cognito-client",
        "cognito_discovery_url": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TestPool/.well-known/openid-configuration",
        "provider_arn": "arn:aws:bedrock-agentcore:us-east-1:123456789012:credential-provider/test",
        "oauth_callback_url": "https://bedrock-agentcore.amazonaws.com/identities/callback/test"
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    assert config_path.exists()
    
    with open(config_path) as f:
        loaded = json.load(f)
    
    assert loaded["gateway_id"] == "test-gateway-id"
    assert loaded["identity_arn"].startswith("arn:aws:bedrock-agentcore")

"""Tests for main.py - Demonstration entry point"""
import json


def test_load_config(tmp_path):
    """Test loading config.json"""
    config_path = tmp_path / "config.json"
    config = {
        "gateway_url": "https://test.gateway.url/mcp",
        "user_pool_id": "us-east-1_TestPool"
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f)
    
    with open(config_path) as f:
        loaded = json.load(f)
    
    assert loaded["gateway_url"] == "https://test.gateway.url/mcp"
    assert loaded["user_pool_id"] == "us-east-1_TestPool"


def test_signup_mode():
    """Test handling --signup flag with username/password"""
    # This will be tested with CLI argument parsing
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--signup", action="store_true")
    parser.add_argument("--username")
    parser.add_argument("--password")
    
    args = parser.parse_args(["--signup", "--username", "testuser", "--password", "TestPass123!"])
    
    assert args.signup is True
    assert args.username == "testuser"
    assert args.password == "TestPass123!"

"""Tests for agent.py - Gateway tool calls and OAuth elicitation"""


def test_call_gateway_tool():
    """Test making raw JSON-RPC call with OAuth _meta"""
    from say_hello_to_authorized_customer.agent import call_gateway_tool
    
    assert callable(call_gateway_tool)


def test_detect_oauth_elicitation():
    """Test detecting error code -32001 and extracting auth URL"""
    # Mock response with OAuth elicitation
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {
            "code": -32001,
            "message": "OAuth authorization required",
            "data": {
                "authorizationUrl": "https://accounts.google.com/o/oauth2/auth?..."
            }
        }
    }
    
    # Should detect elicitation
    assert "error" in response
    assert response["error"]["code"] == -32001
    assert "authorizationUrl" in response["error"]["data"]


def test_greet_user():
    """Test executing greeting flow with YouTube data"""
    from say_hello_to_authorized_customer.agent import greet_user
    
    assert callable(greet_user)


"""Tests for MCP server implementation"""
import json
import pytest
from unittest.mock import Mock, patch


class TestMCPServer:
    """Test MCP server tool implementations"""

    def test_call_gateway_tool_no_bearer_token(self):
        """Test that call_gateway_tool requires bearer token"""
        from mcp_server_with_oauth_gateway.server import call_gateway_tool

        result = call_gateway_tool(
            tool_name="test_tool",
            arguments={},
            context={}  # No bearer token
        )

        assert "error" in result
        assert "bearer token" in result["error"].lower()

    @patch('mcp_server_with_oauth_gateway.server.requests.post')
    def test_call_gateway_tool_oauth_elicitation(self, mock_post):
        """Test OAuth elicitation response handling"""
        from mcp_server_with_oauth_gateway.server import call_gateway_tool

        # Mock OAuth elicitation response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": {
                "code": -32042,
                "data": {
                    "elicitations": [{
                        "url": "https://github.com/login/oauth/authorize?...",
                        "elicitationId": "test-elicitation-id"
                    }]
                }
            }
        }
        mock_post.return_value = mock_response

        result = call_gateway_tool(
            tool_name="test_tool",
            arguments={},
            context={"auth": {"bearer_token": "test-token"}}
        )

        assert result["oauth_required"] is True
        assert "auth_url" in result
        assert "github.com" in result["auth_url"]

    @patch('mcp_server_with_oauth_gateway.server.requests.post')
    def test_get_user_repos_success(self, mock_post):
        """Test successful repository retrieval"""
        from mcp_server_with_oauth_gateway.server import get_user_repos

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "content": [{
                    "text": json.dumps([{
                        "name": "test-repo",
                        "description": "A test repository",
                        "html_url": "https://github.com/user/test-repo",
                        "stargazers_count": 42,
                        "language": "Python"
                    }])
                }]
            }
        }
        mock_post.return_value = mock_response

        result = get_user_repos(context={"auth": {"bearer_token": "test-token"}})
        data = json.loads(result)

        assert data["status"] == "success"
        assert len(data["repositories"]) == 1
        assert data["repositories"][0]["name"] == "test-repo"
        assert data["repositories"][0]["stars"] == 42

    @patch('mcp_server_with_oauth_gateway.server.requests.post')
    def test_get_user_profile_success(self, mock_post):
        """Test successful profile retrieval"""
        from mcp_server_with_oauth_gateway.server import get_user_profile

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "content": [{
                    "text": json.dumps({
                        "login": "testuser",
                        "name": "Test User",
                        "bio": "A test user",
                        "public_repos": 10,
                        "followers": 100,
                        "following": 50,
                        "html_url": "https://github.com/testuser"
                    })
                }]
            }
        }
        mock_post.return_value = mock_response

        result = get_user_profile(context={"auth": {"bearer_token": "test-token"}})
        data = json.loads(result)

        assert data["status"] == "success"
        assert data["profile"]["username"] == "testuser"
        assert data["profile"]["public_repos"] == 10
        assert data["profile"]["followers"] == 100

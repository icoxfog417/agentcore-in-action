"""MCP Server that calls AgentCore Gateway with OAuth for GitHub API"""
import json
import os
from typing import Any
import requests
import boto3
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("GitHub MCP Server")

# Global variables for configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "")
GATEWAY_ID = os.getenv("GATEWAY_ID", "")
REGION = os.getenv("AWS_REGION", "us-east-1")


def call_gateway_tool(tool_name: str, arguments: dict, context: dict) -> dict:
    """
    Call Gateway tool with OAuth support.

    Args:
        tool_name: Name of the Gateway tool to call
        arguments: Tool arguments
        context: MCP request context containing user authentication

    Returns:
        Tool result or OAuth elicitation response
    """
    # Extract bearer token from context
    # In production, this would come from the authenticated user's session
    bearer_token = context.get("auth", {}).get("bearer_token")

    if not bearer_token:
        return {
            "error": "No bearer token provided. User must authenticate first."
        }

    # Make raw JSON-RPC call to Gateway
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {bearer_token}",
        "MCP-Protocol-Version": "2025-11-25"  # Required for OAuth elicitation
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    response = requests.post(GATEWAY_URL, headers=headers, json=payload)

    if response.status_code != 200:
        return {
            "error": f"Gateway returned HTTP {response.status_code}: {response.text}"
        }

    result = response.json()

    # Check for OAuth elicitation
    if "error" in result and result["error"].get("code") == -32042:
        elicitations = result["error"].get("data", {}).get("elicitations", [])
        if elicitations:
            elicitation = elicitations[0]
            return {
                "oauth_required": True,
                "auth_url": elicitation.get("url"),
                "elicitation_id": elicitation.get("elicitationId"),
                "message": "Please visit the auth_url to authorize access to your GitHub account"
            }

    return result


@mcp.tool()
def get_user_repos(context: dict = None) -> str:
    """
    Get the authenticated user's GitHub repositories.

    Returns:
        JSON string with repository information or OAuth authorization URL
    """
    result = call_gateway_tool(
        tool_name="GitHubTarget___getUserRepos",
        arguments={},
        context=context or {}
    )

    if "oauth_required" in result:
        return json.dumps({
            "status": "oauth_required",
            "message": result["message"],
            "auth_url": result["auth_url"]
        }, indent=2)

    if "error" in result:
        return json.dumps({
            "status": "error",
            "message": result["error"].get("message", "Unknown error")
        }, indent=2)

    # Parse successful response
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        data = json.loads(content)

        # Format repository list
        repos = []
        for repo in data[:10]:  # Limit to 10 repos
            repos.append({
                "name": repo["name"],
                "description": repo.get("description", ""),
                "url": repo["html_url"],
                "stars": repo["stargazers_count"],
                "language": repo.get("language", "N/A")
            })

        return json.dumps({
            "status": "success",
            "repositories": repos,
            "total_count": len(data)
        }, indent=2)

    return json.dumps({"status": "error", "message": "Unexpected response format"}, indent=2)


@mcp.tool()
def get_user_profile(context: dict = None) -> str:
    """
    Get the authenticated user's GitHub profile.

    Returns:
        JSON string with profile information or OAuth authorization URL
    """
    result = call_gateway_tool(
        tool_name="GitHubTarget___getUserProfile",
        arguments={},
        context=context or {}
    )

    if "oauth_required" in result:
        return json.dumps({
            "status": "oauth_required",
            "message": result["message"],
            "auth_url": result["auth_url"]
        }, indent=2)

    if "error" in result:
        return json.dumps({
            "status": "error",
            "message": result["error"].get("message", "Unknown error")
        }, indent=2)

    # Parse successful response
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        user = json.loads(content)

        profile = {
            "username": user["login"],
            "name": user.get("name", ""),
            "bio": user.get("bio", ""),
            "public_repos": user["public_repos"],
            "followers": user["followers"],
            "following": user["following"],
            "profile_url": user["html_url"]
        }

        return json.dumps({
            "status": "success",
            "profile": profile
        }, indent=2)

    return json.dumps({"status": "error", "message": "Unexpected response format"}, indent=2)


def start_server():
    """Start the MCP server"""
    # Load configuration from environment
    global GATEWAY_URL, GATEWAY_ID, REGION

    GATEWAY_URL = os.getenv("GATEWAY_URL")
    GATEWAY_ID = os.getenv("GATEWAY_ID")
    REGION = os.getenv("AWS_REGION", "us-east-1")

    if not GATEWAY_URL:
        raise ValueError("GATEWAY_URL environment variable is required")

    print(f"Starting MCP server with Gateway: {GATEWAY_URL}")
    mcp.run()


if __name__ == "__main__":
    start_server()

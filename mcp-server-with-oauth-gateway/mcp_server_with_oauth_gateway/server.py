"""MCP Server that connects to AgentCore Gateway for YouTube API access.

This server exposes YouTube API tools via MCP protocol, using the Gateway
as a backend for OAuth-authenticated API calls.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(host="0.0.0.0", stateless_http=True)


@mcp.tool()
def list_my_channels(part: str = "snippet") -> dict:
    """List the authenticated user's YouTube channels.
    
    Args:
        part: Comma-separated list of channel resource properties to return.
              Common values: snippet, contentDetails, statistics
    
    Returns:
        Channel information for the authenticated user
    """
    # This tool will be invoked through the Gateway which handles OAuth
    # The actual API call is made by the Gateway target
    return {
        "tool": "listChannels",
        "params": {"part": part, "mine": True},
        "note": "This request will be routed through AgentCore Gateway"
    }


@mcp.tool()
def get_channel_info(channel_id: str, part: str = "snippet,statistics") -> dict:
    """Get information about a specific YouTube channel.
    
    Args:
        channel_id: The YouTube channel ID
        part: Comma-separated list of channel resource properties to return
    
    Returns:
        Channel information including statistics and metadata
    """
    return {
        "tool": "listChannels",
        "params": {"part": part, "id": channel_id},
        "note": "This request will be routed through AgentCore Gateway"
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

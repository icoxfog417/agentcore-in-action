#!/usr/bin/env python3
"""Test client for YouTube OAuth MCP Server."""

import asyncio
from fastmcp import Client


async def test_mcp_server():
    """Test the MCP server functionality."""
    client = Client("http://127.0.0.1:8000/mcp")
    
    async with client:
        # List available tools
        tools = await client.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        
        # Test list_youtube_channels (no token needed - server handles auth)
        print("\nCalling list_youtube_channels...")
        result = await client.call_tool("list_youtube_channels", {})
        print(f"Result: {result}")


if __name__ == "__main__":
    print("Testing YouTube OAuth MCP Server...")
    asyncio.run(test_mcp_server())

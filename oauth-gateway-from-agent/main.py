#!/usr/bin/env python3
"""Strands Agent with OAuth Gateway as MCP Server.

Demonstrates:
- Inbound Auth: User authenticates via Cognito (Google federated)
- Outbound Auth: Gateway handles YouTube OAuth via local callback server
"""

import json
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import boto3
import requests
from bedrock_agentcore.identity import requires_access_token
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp import MCPClient


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError("config.json not found. Run 'uv run python construct.py' first.")
    with open(config_path) as f:
        return json.load(f)


config = load_config()
REGION = config.get("region", "us-east-1")
INBOUND_PROVIDER_NAME = config.get("inbound_provider_name", "")
GATEWAY_ENDPOINT = config.get("gateway_endpoint", "")
LOCAL_CALLBACK_URL = config.get("local_callback_url", "http://localhost:8765/oauth2/callback")
CALLBACK_PORT = int(LOCAL_CALLBACK_URL.split(":")[-1].split("/")[0])


class CallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback."""
    session_id = None

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/oauth2/callback":
            params = parse_qs(parsed.query)
            CallbackHandler.session_id = params.get("session_id", [None])[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization complete!</h1><p>You can close this window.</p>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def call_youtube_api(endpoint: str, token: str):
    """Call YouTube API via Gateway."""
    resp = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "mcp-protocol-version": "2025-11-25"},
        json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "mcp-oauth-gateway-youtube-target___listChannels", "arguments": {"part": "snippet", "mine": True}}
        }
    )
    if resp.status_code != 200 or not resp.text:
        return {"error": {"code": -1, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}}
    return resp.json()


def handle_oauth_flow(endpoint: str, token: str) -> bool:
    """Handle OAuth elicitation flow. Returns True if authorized."""
    result = call_youtube_api(endpoint, token)
    
    if "error" not in result:
        return True  # Already authorized
    
    if result["error"].get("code") != -32042:
        print(f"Error: {result['error']}")
        return False
    
    # Get auth URL from elicitation
    elicitations = result["error"].get("data", {}).get("elicitations", [])
    if not elicitations:
        print("No elicitation URL found")
        return False
    
    auth_url = elicitations[0]["url"]
    print(f"\n⚠ YouTube authorization required!")
    print(f"  Opening browser for authorization...")
    
    # Start callback server
    CallbackHandler.session_id = None
    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    server_thread = threading.Thread(target=server.handle_request)
    server_thread.start()
    
    # Open browser
    webbrowser.open(auth_url)
    
    # Wait for callback
    print("  Waiting for authorization...")
    server_thread.join(timeout=120)
    server.server_close()
    
    session_id = CallbackHandler.session_id
    if not session_id:
        print("  Timeout waiting for authorization")
        return False
    
    # Complete session binding
    print("  Completing session binding...")
    identity_client = boto3.client("bedrock-agentcore", region_name=REGION)
    identity_client.complete_resource_token_auth(
        sessionUri=session_id,
        userIdentifier={"userToken": token}
    )
    
    print("✓ YouTube API authorized")
    return True


@requires_access_token(
    provider_name=INBOUND_PROVIDER_NAME,
    scopes=["openid", "email", "profile"],
    auth_flow="USER_FEDERATION",
    on_auth_url=lambda url: (print(f"\nOpen this URL to sign in:\n  {url}\n"), webbrowser.open(url)),
)
def run_agent(*, access_token: str):
    """Run agent with Gateway as MCP server."""
    print(f"✓ Authenticated (token length: {len(access_token)})")

    # Handle OAuth flow
    if not handle_oauth_flow(GATEWAY_ENDPOINT, access_token):
        return

    # Connect to Gateway and run agent
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            GATEWAY_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    )

    with mcp_client:
        tools = mcp_client.list_tools_sync()
        print(f"✓ Connected to Gateway, {len(tools)} tools available")

        agent = Agent(tools=tools)
        response = agent("List my YouTube channels")
        print(response)


if __name__ == "__main__":
    if not INBOUND_PROVIDER_NAME or not GATEWAY_ENDPOINT:
        print("Error: Missing config. Run 'uv run python construct.py' first.")
        exit(1)

    print("Starting OAuth Gateway Agent Demo...")
    print(f"  Gateway: {GATEWAY_ENDPOINT}")
    run_agent()

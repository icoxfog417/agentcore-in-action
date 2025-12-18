#!/usr/bin/env python3
"""MCP Server for YouTube OAuth Gateway functionality."""

import base64
import json
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import boto3
import requests
from bedrock_agentcore.identity import requires_access_token
from fastmcp import FastMCP


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        raise FileNotFoundError("config.json not found. Run 'uv run python construct.py' first.")
    with open(config_path) as f:
        return json.load(f)


config = load_config()
REGION = config.get("region", "us-east-1")
GATEWAY_ENDPOINT = config.get("gateway_endpoint", "")
OAUTH_SESSION_TABLE = config.get("OAuthSessionTableName", "")
KMS_KEY_ID = config.get("kms_key_id", "")
INBOUND_PROVIDER_NAME = config.get("inbound_provider_name", "")

mcp = FastMCP()

# Global token storage (set after authentication)
_user_token: str = ""


def store_session(session_id: str, user_token: str):
    """Store KMS-encrypted user_token in DynamoDB."""
    kms = boto3.client("kms", region_name=REGION)
    response = kms.encrypt(KeyId=KMS_KEY_ID, Plaintext=user_token.encode())
    encrypted_token = base64.b64encode(response["CiphertextBlob"]).decode()
    
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(OAUTH_SESSION_TABLE)
    table.put_item(Item={
        "session_id": session_id,
        "encrypted_user_token": encrypted_token,
        "status": "PENDING",
        "ttl": int(time.time()) + 300
    })


def poll_completion(session_id: str, timeout: int = 120) -> str:
    """Poll DynamoDB for OAuth completion status."""
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(OAUTH_SESSION_TABLE)
    
    start = time.time()
    while time.time() - start < timeout:
        resp = table.get_item(Key={"session_id": session_id})
        if "Item" in resp:
            status = resp["Item"].get("status", "PENDING")
            if status == "COMPLETE":
                return "COMPLETE"
            if status == "FAILED":
                return f"FAILED: {resp['Item'].get('error', 'Unknown error')}"
        time.sleep(2)
    return "TIMEOUT"


def call_gateway(method: str, params: dict, token: str) -> dict:
    """Call Gateway API."""
    resp = requests.post(
        GATEWAY_ENDPOINT,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "mcp-protocol-version": "2025-11-25"
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": f"mcp-oauth-gateway-youtube-target___{method}", "arguments": params}
        }
    )
    if resp.status_code != 200 or not resp.text:
        return {"error": {"code": -1, "message": f"HTTP {resp.status_code}: {resp.text[:200]}"}}
    return resp.json()


def handle_oauth_flow(token: str) -> tuple[bool, str]:
    """Handle OAuth elicitation flow. Returns (success, message)."""
    result = call_gateway("listChannels", {"part": "snippet", "mine": True}, token)
    
    if "error" not in result:
        return True, "Already authorized"
    
    if result["error"].get("code") != -32042:
        return False, f"Error: {result['error']}"
    
    # Get auth URL from elicitation
    elicitations = result["error"].get("data", {}).get("elicitations", [])
    if not elicitations:
        return False, "No elicitation URL found"
    
    auth_url = elicitations[0]["url"]
    
    # Extract session_id from auth URL
    parsed = urlparse(auth_url)
    query_params = parse_qs(parsed.query)
    session_id = query_params.get("request_uri", [""])[0]
    
    if not session_id:
        return False, "No request_uri found in auth URL"
    
    # Store token for CompleteResourceTokenAuth
    store_session(session_id, token)
    
    print("\n⚠ YouTube authorization required!")
    print("  Opening browser for authorization...")
    webbrowser.open(auth_url)
    
    print("  Waiting for authorization...")
    status = poll_completion(session_id)
    
    if status == "COMPLETE":
        print("✓ YouTube API authorized")
        return True, "Authorization complete"
    return False, f"Authorization failed: {status}"


@mcp.tool()
def list_youtube_channels() -> str:
    """List user's YouTube channels."""
    if not _user_token:
        return json.dumps({"error": "Not authenticated. Server requires restart with authentication."})
    
    # Handle outbound OAuth flow
    authorized, message = handle_oauth_flow(_user_token)
    if not authorized:
        return json.dumps({"error": message})
    
    result = call_gateway("listChannels", {"part": "snippet", "mine": True}, _user_token)
    return json.dumps(result, indent=2)


@requires_access_token(
    provider_name=INBOUND_PROVIDER_NAME,
    scopes=["openid", "email", "profile"],
    auth_flow="USER_FEDERATION",
    on_auth_url=lambda url: (print(f"\nOpen this URL to sign in:\n  {url}\n"), webbrowser.open(url)),
)
def run_server(*, access_token: str):
    """Run MCP server with authenticated token."""
    global _user_token
    _user_token = access_token
    print(f"✓ Authenticated (token length: {len(access_token)})")
    print(f"Starting YouTube OAuth MCP Server...")
    print(f"Gateway: {GATEWAY_ENDPOINT}")
    mcp.run(transport="streamable-http", host="127.0.0.1", stateless_http=True)


if __name__ == "__main__":
    if not GATEWAY_ENDPOINT or not INBOUND_PROVIDER_NAME:
        print("Error: Missing config. Run 'uv run python construct.py' first.")
        exit(1)
    
    print("Starting OAuth Gateway MCP Server...")
    run_server()

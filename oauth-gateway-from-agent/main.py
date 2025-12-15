#!/usr/bin/env python3
"""Strands Agent with OAuth Gateway as MCP Server.

Demonstrates:
- Inbound Auth: User authenticates via Cognito (Google federated)
- Outbound Auth: Gateway handles YouTube OAuth via CloudFront -> Lambda -> DynamoDB
"""

import base64
import json
import time
import webbrowser
from pathlib import Path

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
OAUTH_SESSION_TABLE = config.get("OAuthSessionTableName", "")


def get_user_id_from_token(token: str) -> str:
    """Extract user ID (sub claim) from JWT token."""
    payload = token.split(".")[1]
    # Add padding if needed
    payload += "=" * (4 - len(payload) % 4)
    decoded = json.loads(base64.urlsafe_b64decode(payload))
    return decoded.get("sub", "")


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


def store_session(session_id: str, user_token: str):
    """Store KMS-encrypted user_token in DynamoDB keyed by session_id."""
    # Encrypt token with KMS before storage (security best practice)
    kms = boto3.client("kms", region_name=REGION)
    response = kms.encrypt(
        KeyId=config["kms_key_id"],
        Plaintext=user_token.encode()  # Convert string to bytes for encryption
    )
    
    # Convert binary ciphertext to base64 string (DynamoDB can't store binary)
    encrypted_token = base64.b64encode(response["CiphertextBlob"]).decode()
    
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(OAUTH_SESSION_TABLE)
    table.put_item(Item={
        "session_id": session_id,
        "encrypted_user_token": encrypted_token,  # Store encrypted, not plain text
        "status": "PENDING",
        "ttl": int(time.time()) + 300  # 5-minute TTL (auto-delete for security)
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
    
    # Extract session_id (request_uri) from auth URL
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(auth_url)
    query_params = parse_qs(parsed.query)
    session_id = query_params.get("request_uri", [""])[0]
    
    if not session_id:
        print("No request_uri found in auth URL")
        return False
    
    # Store token keyed by session_id for CompleteResourceTokenAuth
    store_session(session_id, token)
    
    print("\n⚠ YouTube authorization required!")
    print("  Opening browser for authorization...")
    webbrowser.open(auth_url)
    
    # Poll for completion (Lambda handles complete_resource_token_auth)
    print("  Waiting for authorization...")
    status = poll_completion(session_id)
    
    if status == "COMPLETE":
        print("✓ YouTube API authorized")
        return True
    else:
        print(f"  Authorization failed: {status}")
        return False


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

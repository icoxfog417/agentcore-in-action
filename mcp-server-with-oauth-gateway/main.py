#!/usr/bin/env python3
"""MCP Server with OAuth Gateway - Interactive Demo.

This script guides you through the MCP server and OAuth authentication flow.

Usage:
    uv run python main.py              # Interactive demo
    uv run python main.py --server     # Run MCP server locally
"""

import argparse
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent / "config.json"


def main():
    parser = argparse.ArgumentParser(description="MCP Server with OAuth Gateway Demo")
    parser.add_argument("--server", action="store_true", help="Run MCP server locally")
    args = parser.parse_args()

    if args.server:
        run_mcp_server()
    else:
        run_interactive_demo()


def run_mcp_server():
    """Run the MCP server locally."""
    print("=" * 60)
    print("Starting MCP Server")
    print("=" * 60)
    print("\nServer will be available at: http://localhost:8000/mcp")
    print("\nThis MCP server exposes YouTube API tools that connect to")
    print("AgentCore Gateway for OAuth-authenticated API calls.")
    print("\nPress Ctrl+C to stop\n")

    server_path = Path(__file__).parent / "mcp_server_with_oauth_gateway" / "server.py"
    subprocess.run([sys.executable, str(server_path)])


def run_interactive_demo():
    """Guide developer through the OAuth flow experience."""
    print("=" * 60)
    print("MCP Server with OAuth Gateway - Interactive Demo")
    print("=" * 60)

    # Check config
    if not CONFIG_PATH.exists():
        print("\n❌ config.json not found!")
        print("\nFirst, run the construction script to set up AWS resources:")
        print("  uv run python construct.py")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    print("\n✓ Configuration loaded")
    print(f"  Gateway ID: {config.get('gateway_id', 'N/A')}")
    print(f"  Region: {config.get('region', 'N/A')}")

    # Menu
    while True:
        print("\n" + "-" * 60)
        print("What would you like to do?\n")
        print("  1. Start MCP Server locally")
        print("  2. Experience Inbound Auth (Sign in with Google)")
        print("  3. Experience Outbound Auth (Authorize YouTube API)")
        print("  4. View OAuth Flow Diagram")
        print("  5. Exit")
        print()

        choice = input("Enter choice [1-5]: ").strip()

        if choice == "1":
            demo_start_server()
        elif choice == "2":
            demo_inbound_auth(config)
        elif choice == "3":
            demo_outbound_auth(config)
        elif choice == "4":
            show_flow_diagram()
        elif choice == "5":
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid choice. Please enter 1-5.")


def demo_start_server():
    """Guide: Starting the MCP server."""
    print("\n" + "=" * 60)
    print("Step: Start MCP Server")
    print("=" * 60)

    print("""
The MCP server exposes YouTube API tools via the MCP protocol.
It connects to AgentCore Gateway which handles OAuth authentication.

To start the server, run in a separate terminal:

    uv run python main.py --server

The server will listen on http://localhost:8000/mcp

Available tools:
  - list_my_channels: Get authenticated user's YouTube channels
  - get_channel_info: Get info about a specific channel
""")

    start = input("Start server now? [y/N]: ").strip().lower()
    if start == "y":
        run_mcp_server()


def demo_inbound_auth(config: dict):
    """Guide: Inbound authentication flow."""
    print("\n" + "=" * 60)
    print("Step: Inbound Authentication (User Identity)")
    print("=" * 60)

    print("""
Inbound auth identifies WHO the user is.

Flow:
  1. User clicks "Sign in with Google" on Cognito Hosted UI
  2. Google authenticates the user
  3. Cognito issues a JWT containing the user's Google identity
  4. MCP client includes this JWT in requests to the Gateway
  5. Gateway validates the JWT and extracts user claims
""")

    hosted_ui_url = config.get("HostedUIUrl", "")
    if hosted_ui_url:
        print(f"Cognito Hosted UI URL:\n  {hosted_ui_url}\n")
        open_browser = input("Open in browser to sign in? [y/N]: ").strip().lower()
        if open_browser == "y":
            webbrowser.open(hosted_ui_url)
            print("\n✓ Browser opened. Complete sign-in with Google.")
            print("\nAfter sign-in, you'll be redirected to the callback page")
            print("which displays your Cognito JWT token.")
    else:
        print("⚠ Hosted UI URL not found in config.")
        print("  Check that CloudFormation stack deployed correctly.")


def demo_outbound_auth(config: dict):
    """Guide: Outbound authorization flow."""
    print("\n" + "=" * 60)
    print("Step: Outbound Authorization (API Access)")
    print("=" * 60)

    print("""
Outbound auth determines WHAT the user can access.

Flow (first-time user):
  1. MCP client calls a YouTube tool via Gateway
  2. Gateway Interceptor checks Token Vault for user's Google API token
  3. No token found → returns authorization URL
  4. User clicks URL and grants YouTube API access
  5. Google token stored in Token Vault for this user

Flow (returning user):
  1. MCP client calls a YouTube tool via Gateway
  2. Interceptor retrieves token from Token Vault
  3. Token injected into outbound request
  4. Gateway calls YouTube API with user's token
  5. Response returned to MCP client
""")

    callback_url = config.get("google_callback_url", "")
    if callback_url:
        print("Google OAuth Callback URL (for Token Vault):")
        print(f"  {callback_url}\n")
        print("⚠ Make sure this URL is registered in your Google OAuth App:")
        print("  Google Cloud Console → APIs & Services → Credentials")
        print("  → OAuth 2.0 Client ID → Authorized redirect URIs")


def show_flow_diagram():
    """Show the complete OAuth flow."""
    print("\n" + "=" * 60)
    print("Complete OAuth Flow Diagram")
    print("=" * 60)

    print("""
┌─────────────────────────────────────────────────────────────┐
│                    INBOUND AUTH FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User ──► Cognito Hosted UI ──► Google Sign-in             │
│                                      │                      │
│                                      ▼                      │
│                              Google Identity                │
│                                      │                      │
│                                      ▼                      │
│  User ◄── Cognito JWT ◄───── Cognito User Pool             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ JWT in Authorization header
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   AGENTCORE GATEWAY                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  MCP Request ──► JWT Validation ──► Interceptor Lambda     │
│                                           │                 │
│                                           ▼                 │
│                                    Token Vault              │
│                                           │                 │
│                              ┌────────────┴────────────┐    │
│                              │                         │    │
│                              ▼                         ▼    │
│                      Token Found?              No Token     │
│                              │                         │    │
│                              ▼                         ▼    │
│                    Inject Token           Return Auth URL   │
│                              │                              │
│                              ▼                              │
│                       YouTube API                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   OUTBOUND AUTH FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  (First time only)                                          │
│                                                             │
│  User ──► Authorization URL ──► Google Consent Screen      │
│                                        │                    │
│                                        ▼                    │
│                                 Grant API Access            │
│                                        │                    │
│                                        ▼                    │
│  Token Vault ◄─────────────── Google API Token             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
""")

    input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()

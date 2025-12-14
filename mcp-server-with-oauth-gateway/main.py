"""Main entry point for MCP Server with OAuth Gateway"""
import argparse
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"


def run_mcp_server():
    """Run the MCP server"""
    # Load config
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run construct.py first.")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    # Set environment variables for server
    os.environ["GATEWAY_URL"] = config["gateway_url"]
    os.environ["GATEWAY_ID"] = config["gateway_id"]
    os.environ["AWS_REGION"] = config["region"]

    print("Starting MCP server...")
    print(f"Gateway URL: {config['gateway_url']}")
    print(f"Gateway ID: {config['gateway_id']}")
    print(f"Region: {config['region']}")
    print()
    print("The server will expose the following tools:")
    print("  - get_user_repos: Get authenticated user's GitHub repositories")
    print("  - get_user_profile: Get authenticated user's GitHub profile")
    print()
    print("Note: On first use, clients will receive an OAuth authorization URL")
    print("      to grant access to their GitHub account.")
    print()

    # Import and run server
    from mcp_server_with_oauth_gateway.server import start_server
    start_server()


def run_oauth_callback_server():
    """Run the OAuth callback server"""
    # Load config
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found. Run construct.py first.")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    print("Starting OAuth callback server...")
    print(f"This server handles OAuth callbacks from GitHub authorization")
    print()

    from mcp_server_with_oauth_gateway.oauth_callback_handler import OAuthCallbackHandler

    handler = OAuthCallbackHandler(
        region=config["region"],
        identity_arn=config["identity_arn"]
    )
    handler.run(host="0.0.0.0", port=8080)


def main():
    """Main entry point with mode selection"""
    parser = argparse.ArgumentParser(
        description="MCP Server with OAuth Gateway Example"
    )
    parser.add_argument(
        "--mode",
        choices=["mcp", "oauth-callback"],
        default="mcp",
        help="Server mode: 'mcp' for MCP server, 'oauth-callback' for OAuth callback handler"
    )
    args = parser.parse_args()

    if args.mode == "mcp":
        run_mcp_server()
    elif args.mode == "oauth-callback":
        run_oauth_callback_server()


if __name__ == "__main__":
    main()

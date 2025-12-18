#!/usr/bin/env python3
"""Quick verification of callback URL configuration for step 6 debugging."""

import json
import os
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

def main():
    print("🔍 Verifying Callback Configuration\n")

    # 1. Load config
    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("❌ config.json not found")
        return

    with open(config_path) as f:
        config = json.load(f)

    region = config.get("region", "us-east-1")
    print(f"📍 Region: {region}\n")

    # 2. Expected callback URL
    expected_callback = f"https://bedrock-agentcore.{region}.amazonaws.com/identities/oauth2/callback"
    print(f"✅ Expected AgentCore callback URL:")
    print(f"   {expected_callback}\n")

    # 3. Check Cognito configuration
    pool_id = config.get("InboundUserPoolId")
    client_id = config.get("InboundClientId")

    if not pool_id or not client_id:
        print("⚠️  Missing Cognito IDs in config.json")
        print(f"   InboundUserPoolId: {pool_id}")
        print(f"   InboundClientId: {client_id}")
        return

    try:
        cognito = boto3.client("cognito-idp", region_name=region)
        response = cognito.describe_user_pool_client(
            UserPoolId=pool_id,
            ClientId=client_id
        )
        client_config = response["UserPoolClient"]

        callback_urls = client_config.get("CallbackURLs", [])
        print(f"📋 Cognito registered callback URLs:")
        for url in callback_urls:
            if url == expected_callback:
                print(f"   ✅ {url}")
            else:
                print(f"   ⚠️  {url}")

        # Check if expected callback is present
        print()
        if expected_callback in callback_urls:
            print("✅ AgentCore callback URL is correctly registered!")
        else:
            print("❌ AgentCore callback URL is MISSING!")
            print(f"   Expected: {expected_callback}")
            print(f"   Found:    {callback_urls}")
            print("\n💡 Fix with:")
            print(f"   aws cognito-idp update-user-pool-client \\")
            print(f"     --user-pool-id {pool_id} \\")
            print(f"     --client-id {client_id} \\")
            print(f"     --region {region} \\")
            print(f'     --callback-urls "{expected_callback}"')

        # Check OAuth flows
        print("\n📋 OAuth Configuration:")
        oauth_flows = client_config.get("AllowedOAuthFlows", [])
        oauth_scopes = client_config.get("AllowedOAuthScopes", [])
        flows_enabled = client_config.get("AllowedOAuthFlowsUserPoolClient", False)

        print(f"   Flows: {oauth_flows} {'✅' if 'code' in oauth_flows else '❌ Missing code flow!'}")
        print(f"   Scopes: {oauth_scopes}")

        required_scopes = {'openid', 'email', 'profile'}
        allowed_scopes = set(oauth_scopes)
        if required_scopes.issubset(allowed_scopes):
            print(f"   ✅ All required scopes present")
        else:
            print(f"   ❌ Missing scopes: {required_scopes - allowed_scopes}")

        print(f"   Flows enabled: {flows_enabled} {'✅' if flows_enabled else '❌'}")

        # Check supported IdPs
        print(f"\n📋 Identity Providers:")
        idps = client_config.get("SupportedIdentityProviders", [])
        print(f"   {idps} {'✅' if 'Google' in idps else '❌ Google not configured!'}")

    except Exception as e:
        print(f"❌ Error accessing Cognito: {e}")
        return

    # 4. Summary
    print("\n" + "=" * 60)
    print("📝 NEXT STEPS")
    print("=" * 60)
    print("\nIf you see ❌ above, fix the issues then retry.")
    print("\nTo debug the actual OAuth flow:")
    print("1. Run main.py with browser DevTools open (F12 → Network)")
    print("2. Look for the Cognito authorize request")
    print("3. Check the 'redirect_uri' parameter matches:")
    print(f"   {expected_callback}")
    print("\nSee debug_step6.md for detailed troubleshooting steps.")


if __name__ == "__main__":
    main()

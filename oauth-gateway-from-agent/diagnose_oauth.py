#!/usr/bin/env python3
"""Diagnostic script for OAuth Gateway authentication issues.

This script checks the configuration of Cognito and AgentCore resources
to identify issues with the inbound authentication flow.
"""

import json
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_REGION", "us-east-1")
STACK_NAME = "mcp-oauth-gateway-infra"


def check_config_file():
    """Check if config.json exists and is valid."""
    print("=" * 60)
    print("1. Checking config.json")
    print("=" * 60)

    config_path = Path(__file__).parent / "config.json"
    if not config_path.exists():
        print("❌ config.json not found!")
        print("   Run 'uv run python construct.py' first")
        return None

    with open(config_path) as f:
        config = json.load(f)

    print("✅ config.json found")
    print(f"\n📋 Key URLs:")
    print(f"  Inbound callback:  {config.get('inbound_callback_url', 'MISSING')}")
    print(f"  OAuth callback:    {config.get('oauth_callback_url', 'MISSING')}")
    print(f"  Gateway endpoint:  {config.get('gateway_endpoint', 'MISSING')}")
    return config


def check_cloudformation_stack():
    """Check CloudFormation stack outputs."""
    print("\n" + "=" * 60)
    print("2. Checking CloudFormation Stack")
    print("=" * 60)

    try:
        cfn = boto3.client("cloudformation", region_name=REGION)
        response = cfn.describe_stacks(StackName=STACK_NAME)
        stack = response["Stacks"][0]
        status = stack["StackStatus"]

        print(f"✅ Stack status: {status}")

        if status not in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
            print(f"⚠️  Stack is not ready: {status}")
            return None

        outputs = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
        print(f"\n📋 Stack Outputs:")
        for key in ["InboundUserPoolId", "InboundClientId", "InboundDiscoveryUrl", "OAuthCallbackUrl"]:
            print(f"  {key}: {outputs.get(key, 'MISSING')}")

        return outputs
    except Exception as e:
        print(f"❌ Error accessing CloudFormation: {e}")
        return None


def check_cognito_user_pool_client(pool_id: str, client_id: str):
    """Check Cognito User Pool Client configuration."""
    print("\n" + "=" * 60)
    print("3. Checking Cognito User Pool Client")
    print("=" * 60)

    try:
        cognito = boto3.client("cognito-idp", region_name=REGION)
        response = cognito.describe_user_pool_client(
            UserPoolId=pool_id,
            ClientId=client_id
        )
        client = response["UserPoolClient"]

        print("✅ Cognito client found")
        print(f"\n📋 Configuration:")
        print(f"  Client ID: {client_id}")
        print(f"  Callback URLs: {client.get('CallbackURLs', [])}")
        print(f"  Allowed OAuth Flows: {client.get('AllowedOAuthFlows', [])}")
        print(f"  Allowed OAuth Scopes: {client.get('AllowedOAuthScopes', [])}")
        print(f"  Supported Identity Providers: {client.get('SupportedIdentityProviders', [])}")

        # Check for issues
        callback_urls = client.get('CallbackURLs', [])
        expected_callback = f"https://bedrock-agentcore.{REGION}.amazonaws.com/identities/oauth2/callback"

        print(f"\n🔍 Validation:")
        if expected_callback not in callback_urls:
            print(f"❌ Missing AgentCore callback URL!")
            print(f"   Expected: {expected_callback}")
            print(f"   Found: {callback_urls}")
        else:
            print(f"✅ AgentCore callback URL registered")

        if 'code' not in client.get('AllowedOAuthFlows', []):
            print(f"❌ Authorization code flow not enabled!")
        else:
            print(f"✅ Authorization code flow enabled")

        required_scopes = {'openid', 'email', 'profile'}
        allowed_scopes = set(client.get('AllowedOAuthScopes', []))
        if not required_scopes.issubset(allowed_scopes):
            print(f"❌ Missing required scopes: {required_scopes - allowed_scopes}")
        else:
            print(f"✅ Required scopes present")

        return client
    except Exception as e:
        print(f"❌ Error accessing Cognito: {e}")
        return None


def check_cognito_identity_provider(pool_id: str):
    """Check Cognito Google Identity Provider configuration."""
    print("\n" + "=" * 60)
    print("4. Checking Cognito Google Identity Provider")
    print("=" * 60)

    try:
        cognito = boto3.client("cognito-idp", region_name=REGION)
        response = cognito.describe_identity_provider(
            UserPoolId=pool_id,
            ProviderName="Google"
        )
        idp = response["IdentityProvider"]

        print("✅ Google IdP found")
        print(f"\n📋 Configuration:")
        print(f"  Provider Type: {idp.get('ProviderType')}")
        print(f"  Provider Details: {idp.get('ProviderDetails', {}).get('authorize_scopes')}")
        print(f"  Attribute Mapping: {idp.get('AttributeMapping')}")

        return idp
    except Exception as e:
        print(f"❌ Error accessing Google IdP: {e}")
        return None


def check_agentcore_provider(provider_name: str):
    """Check AgentCore OAuth Provider configuration."""
    print("\n" + "=" * 60)
    print("5. Checking AgentCore Identity Provider")
    print("=" * 60)

    try:
        client = boto3.client("bedrock-agentcore-control", region_name=REGION)
        response = client.get_oauth2_credential_provider(name=provider_name)

        print("✅ AgentCore provider found")
        print(f"\n📋 Configuration:")
        print(f"  Name: {response.get('name')}")
        print(f"  ARN: {response.get('credentialProviderArn', response.get('oauth2CredentialProviderArn'))}")
        print(f"  Vendor: {response.get('credentialProviderVendor')}")

        config = response.get('oauth2ProviderConfig', {})
        if 'includedOauth2ProviderConfig' in config:
            included = config['includedOauth2ProviderConfig']
            print(f"  Issuer: {included.get('issuer')}")
            print(f"  Auth Endpoint: {included.get('authorizationEndpoint')}")
            print(f"  Token Endpoint: {included.get('tokenEndpoint')}")

        return response
    except Exception as e:
        print(f"❌ Error accessing AgentCore provider: {e}")
        return None


def main():
    print("🔍 OAuth Gateway Diagnostics")
    print(f"Region: {REGION}\n")

    # 1. Check config file
    config = check_config_file()
    if not config:
        print("\n⚠️  Cannot proceed without config.json")
        print("Run 'uv run python construct.py' to create resources")
        return

    # 2. Check CloudFormation
    cfn_outputs = check_cloudformation_stack()
    if not cfn_outputs:
        return

    # 3. Check Cognito User Pool Client
    pool_id = cfn_outputs.get("InboundUserPoolId")
    client_id = cfn_outputs.get("InboundClientId")
    if pool_id and client_id:
        check_cognito_user_pool_client(pool_id, client_id)

    # 4. Check Cognito Google IdP
    if pool_id:
        check_cognito_identity_provider(pool_id)

    # 5. Check AgentCore Provider
    provider_name = config.get("inbound_provider_name")
    if provider_name:
        check_agentcore_provider(provider_name)

    # Summary
    print("\n" + "=" * 60)
    print("📝 SUMMARY")
    print("=" * 60)
    print("\nIf you see errors above, the most common issues are:")
    print("\n1. ❌ Callback URL mismatch in Cognito User Pool Client")
    print("   → The CallbackURLs must include:")
    print(f"     https://bedrock-agentcore.{REGION}.amazonaws.com/identities/oauth2/callback")
    print("\n2. ❌ Missing Google callback URL in Google OAuth App")
    print("   → Go to Google Cloud Console and add:")
    print(f"     {config.get('inbound_callback_url', 'N/A')}")
    print("\n3. ❌ Cognito discovery URL mismatch")
    print("   → Verify Gateway's CUSTOM_JWT authorizer uses correct discovery URL")
    print("\n4. ❌ OAuth flow not enabled")
    print("   → Cognito client must have 'code' in AllowedOAuthFlows")


if __name__ == "__main__":
    main()

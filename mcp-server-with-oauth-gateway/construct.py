#!/usr/bin/env python3
"""Construct AWS resources for MCP Server with OAuth Gateway.

Uses CloudFormation for infrastructure (S3, CloudFront, Cognito, Lambda, IAM)
and boto3 for AgentCore resources (no CFN support yet).

Usage:
    uv run python construct.py          # Create all resources
    uv run python construct.py --clean  # Delete all resources
"""

import json
import os
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.environ.get("AWS_REGION", "us-east-1")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
STACK_NAME = "mcp-oauth-gateway"
CFN_STACK_NAME = f"{STACK_NAME}-infra"


def main():
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        print("Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in .env")
        sys.exit(1)

    print(f"Region: {REGION}")
    print("Starting resource construction...\n")

    # Step 1-3: Deploy CloudFormation stack (S3, CloudFront, Cognito, Lambda, IAM)
    print("Step 1-3: Deploying CloudFormation stack...")
    cfn_outputs = deploy_cfn_stack()
    print(f"  ✓ Stack deployed: {CFN_STACK_NAME}")
    for key, value in cfn_outputs.items():
        print(f"    {key}: {value[:60]}..." if len(value) > 60 else f"    {key}: {value}")

    # Update Lambda code with actual interceptor
    print("\n  Updating Lambda code...")
    update_lambda_code(cfn_outputs["InterceptorArn"])
    print("  ✓ Lambda code updated")

    # Upload callback HTML to S3
    print("\n  Uploading callback page...")
    upload_callback_html(cfn_outputs["BucketName"])
    print("  ✓ Callback page uploaded")

    # Step 4: AgentCore Resources (no CFN support)
    print("\nStep 4: Creating AgentCore Resources...")
    config = {"region": REGION, **cfn_outputs}

    # 4a: OAuth Provider
    print("  4a: Creating OAuth Provider...")
    provider_config = create_oauth_provider()
    config.update(provider_config)
    print(f"    ✓ Provider ARN: {provider_config['provider_arn']}")

    # Update Lambda env with provider ARN
    update_lambda_env(cfn_outputs["InterceptorArn"], provider_config["provider_arn"])

    # 4b: Gateway
    print("  4b: Creating Gateway...")
    gateway_config = create_gateway(cfn_outputs)
    config.update(gateway_config)
    print(f"    ✓ Gateway ID: {gateway_config['gateway_id']}")

    # 4c: Gateway Target
    print("  4c: Creating Gateway Target...")
    target_config = create_gateway_target(
        gateway_config["gateway_id"],
        provider_config["provider_arn"],
        provider_config["google_callback_url"]
    )
    config.update(target_config)
    print(f"    ✓ Target ID: {target_config['target_id']}")

    # Save config
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n✓ Configuration saved to {config_path}")

    print("\n" + "=" * 60)
    print("Register this callback URL in Google OAuth App:")
    print(f"  {config.get('google_callback_url', 'N/A')}")
    print("=" * 60)


def deploy_cfn_stack() -> dict:
    """Deploy CloudFormation stack and return outputs."""
    cfn = boto3.client("cloudformation", region_name=REGION)
    template_path = Path(__file__).parent / "mcp_server_with_oauth_gateway" / "oauth_gateway_infra.yaml"

    with open(template_path) as f:
        template_body = f.read()

    params = [
        {"ParameterKey": "StackName", "ParameterValue": STACK_NAME},
        {"ParameterKey": "GoogleClientId", "ParameterValue": GOOGLE_CLIENT_ID},
        {"ParameterKey": "GoogleClientSecret", "ParameterValue": GOOGLE_CLIENT_SECRET},
    ]

    try:
        cfn.create_stack(
            StackName=CFN_STACK_NAME,
            TemplateBody=template_body,
            Parameters=params,
            Capabilities=["CAPABILITY_NAMED_IAM"],
        )
        print("  ⏳ Creating stack (this may take a few minutes)...")
        waiter = cfn.get_waiter("stack_create_complete")
        waiter.wait(StackName=CFN_STACK_NAME, WaiterConfig={"Delay": 10, "MaxAttempts": 60})
    except cfn.exceptions.AlreadyExistsException:
        print("  ⏳ Updating existing stack...")
        try:
            cfn.update_stack(
                StackName=CFN_STACK_NAME,
                TemplateBody=template_body,
                Parameters=params,
                Capabilities=["CAPABILITY_NAMED_IAM"],
            )
            waiter = cfn.get_waiter("stack_update_complete")
            waiter.wait(StackName=CFN_STACK_NAME, WaiterConfig={"Delay": 10, "MaxAttempts": 60})
        except cfn.exceptions.ClientError as e:
            if "No updates are to be performed" not in str(e):
                raise

    # Get outputs
    response = cfn.describe_stacks(StackName=CFN_STACK_NAME)
    outputs = {o["OutputKey"]: o["OutputValue"] for o in response["Stacks"][0].get("Outputs", [])}
    return outputs


def update_lambda_code(lambda_arn: str):
    """Update Lambda with actual interceptor code."""
    lambda_client = boto3.client("lambda", region_name=REGION)
    function_name = lambda_arn.split(":")[-1]

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        interceptor_path = Path(__file__).parent / "mcp_server_with_oauth_gateway" / "interceptor.py"
        zf.write(interceptor_path, "interceptor.py")
    zip_buffer.seek(0)

    lambda_client.update_function_code(FunctionName=function_name, ZipFile=zip_buffer.read())
    waiter = lambda_client.get_waiter("function_updated_v2")
    waiter.wait(FunctionName=function_name)


def update_lambda_env(lambda_arn: str, provider_arn: str):
    """Update Lambda environment with OAuth provider ARN."""
    lambda_client = boto3.client("lambda", region_name=REGION)
    function_name = lambda_arn.split(":")[-1]
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Environment={"Variables": {"AWS_REGION_NAME": REGION, "OAUTH_PROVIDER_ARN": provider_arn}},
    )


def upload_callback_html(bucket_name: str):
    """Upload OAuth callback HTML pages to S3.
    
    Two separate pages for different OAuth flows:
    - callback_inbound.html: Cognito sign-in completion (inbound auth)
    - callback_outbound.html: YouTube API authorization (outbound auth via Token Vault)
    """
    s3 = boto3.client("s3", region_name=REGION)
    base_path = Path(__file__).parent / "mcp_server_with_oauth_gateway"
    
    for filename in ["callback_inbound.html", "callback_outbound.html"]:
        with open(base_path / filename) as f:
            html = f.read()
        s3.put_object(Bucket=bucket_name, Key=filename, Body=html, ContentType="text/html")


def create_oauth_provider() -> dict:
    """Create AgentCore OAuth Provider for Google."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    provider_name = f"{STACK_NAME}-google-provider"

    try:
        response = client.create_oauth2_credential_provider(
            name=provider_name,
            credentialProviderVendor="GoogleOauth2",
            oauth2ProviderConfigInput={
                "googleOauth2ProviderConfig": {"clientId": GOOGLE_CLIENT_ID, "clientSecret": GOOGLE_CLIENT_SECRET}
            },
        )
    except client.exceptions.ConflictException:
        response = client.get_oauth2_credential_provider(name=provider_name)

    return {
        "provider_arn": response.get("credentialProviderArn", response.get("oauth2CredentialProviderArn", "")),
        "provider_name": provider_name,
        "google_callback_url": response.get("callbackUrl", ""),
    }


def create_gateway(cfn_outputs: dict) -> dict:
    """Create AgentCore Gateway with CUSTOM_JWT auth and interceptor."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    gateway_name = f"{STACK_NAME}-gateway"

    try:
        response = client.create_gateway(
            name=gateway_name,
            roleArn=cfn_outputs["GatewayRoleArn"],
            protocolType="MCP",
            protocolConfiguration={
                "mcp": {
                    "supportedVersions": ["2025-11-25"],
                    "searchType": "SEMANTIC"
                }
            },
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration={
                "customJWTAuthorizer": {
                    "discoveryUrl": cfn_outputs["DiscoveryUrl"],
                    "allowedClients": [cfn_outputs["ClientId"]],
                }
            },
            interceptorConfiguration={"lambdaArn": cfn_outputs["InterceptorArn"], "payloadVersion": "1.0"},
            exceptionLevel="DEBUG",
        )
        gateway_id = response["gatewayId"]
    except client.exceptions.ConflictException:
        response = client.get_gateway(gatewayIdentifier=gateway_name)
        gateway_id = response["gatewayId"]

    return {"gateway_id": gateway_id, "gateway_name": gateway_name}


def create_gateway_target(gateway_id: str, provider_arn: str, callback_url: str) -> dict:
    """Create Gateway Target for YouTube API."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    target_name = f"{STACK_NAME}-youtube-target"

    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "YouTube Data API", "version": "v3"},
        "servers": [{"url": "https://www.googleapis.com/youtube/v3"}],
        "paths": {
            "/channels": {
                "get": {
                    "operationId": "listChannels",
                    "parameters": [
                        {"name": "part", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "mine", "in": "query", "schema": {"type": "boolean"}},
                    ],
                    "responses": {"200": {"description": "Successful response"}},
                }
            }
        },
    }

    try:
        response = client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=target_name,
            targetConfiguration={
                "mcp": {
                    "openApiSchema": {
                        "inlinePayload": json.dumps(openapi_spec)
                    }
                }
            },
            credentialProviderConfigurations=[{
                "credentialProviderType": "OAUTH",
                "credentialProvider": {
                    "oauthCredentialProvider": {
                        "providerArn": provider_arn,
                        "grantType": "AUTHORIZATION_CODE",
                        "defaultReturnUrl": callback_url,
                        "scopes": ["https://www.googleapis.com/auth/youtube.readonly"]
                    }
                }
            }],
        )
        target_id = response["targetId"]
    except client.exceptions.ConflictException:
        response = client.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_name)
        target_id = response["targetId"]

    return {"target_id": target_id, "target_name": target_name}


def cleanup():
    """Delete all resources."""
    print(f"Region: {REGION}")
    print("Starting cleanup...\n")

    config_path = Path(__file__).parent / "config.json"
    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)

    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    cfn = boto3.client("cloudformation", region_name=REGION)

    # Step 1: Delete AgentCore resources (reverse order)
    print("Step 1: Deleting AgentCore resources...")
    gateway_id = config.get("gateway_id")
    if gateway_id:
        try:
            control_client.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=f"{STACK_NAME}-youtube-target")
            print("  ✓ Deleted Gateway Target")
        except Exception as e:
            print(f"  ⚠ {e}")
        try:
            control_client.delete_gateway(gatewayIdentifier=f"{STACK_NAME}-gateway")
            print("  ✓ Deleted Gateway")
        except Exception as e:
            print(f"  ⚠ {e}")

    try:
        control_client.delete_oauth2_credential_provider(name=f"{STACK_NAME}-google-provider")
        print("  ✓ Deleted OAuth Provider")
    except Exception as e:
        print(f"  ⚠ {e}")

    # Step 2: Delete CloudFormation stack (handles all infrastructure)
    print("\nStep 2: Deleting CloudFormation stack...")
    try:
        # Empty S3 bucket first (CFN can't delete non-empty buckets)
        bucket_name = config.get("BucketName")
        if bucket_name:
            s3 = boto3.client("s3", region_name=REGION)
            try:
                objects = s3.list_objects_v2(Bucket=bucket_name).get("Contents", [])
                for obj in objects:
                    s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
            except Exception:
                pass

        cfn.delete_stack(StackName=CFN_STACK_NAME)
        print("  ⏳ Deleting stack (this may take a few minutes)...")
        waiter = cfn.get_waiter("stack_delete_complete")
        waiter.wait(StackName=CFN_STACK_NAME, WaiterConfig={"Delay": 10, "MaxAttempts": 60})
        print(f"  ✓ Stack deleted: {CFN_STACK_NAME}")
    except Exception as e:
        print(f"  ⚠ {e}")

    if config_path.exists():
        config_path.unlink()
        print("\n✓ Deleted config.json")

    print("\n✓ Cleanup complete")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        cleanup()
    else:
        main()

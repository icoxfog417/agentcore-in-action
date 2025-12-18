#!/usr/bin/env python3
"""Construct AWS resources for MCP Server with OAuth Gateway.

Uses CloudFormation for infrastructure (CloudFront, Lambda, DynamoDB, Cognito, IAM)
and boto3 for AgentCore resources (no CFN support yet).

Usage:
    uv run python construct.py          # Create all resources
    uv run python construct.py --clean  # Delete all resources
"""

import json
import os
import sys
import time
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

    # Step 1: Deploy CloudFormation stack (S3, CloudFront, Cognito, IAM)
    print("Step 1: Deploying CloudFormation stack...")
    cfn_outputs = deploy_cfn_stack()
    print(f"  ✓ Stack deployed: {CFN_STACK_NAME}")
    for key, value in cfn_outputs.items():
        print(f"    {key}: {value[:60]}..." if len(value) > 60 else f"    {key}: {value}")

    # Step 1b: Create and attach boto3 layer to Lambda
    print("\nStep 1b: Creating boto3 layer for Lambda...")
    create_boto3_layer()
    print("  ✓ boto3 layer attached to Lambda")

    # Step 2: AgentCore Resources (no CFN support)
    print("\nStep 2: Creating AgentCore Resources...")
    config = {"region": REGION, **cfn_outputs}

    # 2a: Inbound OAuth Provider (Cognito - for user authentication)
    print("  2a: Creating Inbound OAuth Provider (Cognito)...")
    inbound_config = create_inbound_cognito_provider(cfn_outputs)
    config.update(inbound_config)
    print(f"    ✓ Provider: {inbound_config['inbound_provider_name']}")

    # 2b: Outbound OAuth Provider (Google - for YouTube API access)
    print("  2b: Creating Outbound OAuth Provider (Google/YouTube)...")
    outbound_config = create_outbound_google_provider()
    config.update(outbound_config)
    print(f"    ✓ Provider: {outbound_config['outbound_provider_name']}")

    # 2c: Gateway
    print("  2c: Creating Gateway...")
    gateway_config = create_gateway(cfn_outputs)
    config.update(gateway_config)
    print(f"    ✓ Gateway ID: {gateway_config['gateway_id']}")

    # 2d: Gateway Target (use CloudFront callback URL for session binding)
    print("  2d: Creating Gateway Target...")
    callback_url = cfn_outputs["OAuthCallbackUrl"]
    target_config = create_gateway_target(
        gateway_config["gateway_id"],
        outbound_config["outbound_provider_arn"],
        callback_url
    )
    config.update(target_config)
    print(f"    ✓ Target ID: {target_config['target_id']}")

    # Add callback URLs and KMS key to config
    cognito_domain = cfn_outputs.get("InboundCognitoDomain", "")
    config["inbound_callback_url"] = f"https://{cognito_domain}.auth.{REGION}.amazoncognito.com/oauth2/idpresponse"
    config["oauth_callback_url"] = callback_url  # CloudFront URL for session binding
    config["kms_key_id"] = cfn_outputs.get("KMSKeyId", "")  # KMS key for token encryption

    # Save config
    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\n✓ Configuration saved to {config_path}")
    print(f"    ✓ KMS Key ID: {config['kms_key_id']}")

    print("\n" + "=" * 60)
    print("Register BOTH callback URLs in Google OAuth App:")
    print("\n📥 Inbound Auth (Cognito federation):")
    print(f"  {config['inbound_callback_url']}")
    print("\n📤 Outbound Auth (Token Vault):")
    print(f"  {config.get('outbound_callback_url', 'N/A')}")
    print("=" * 60)


def deploy_cfn_stack() -> dict:
    """Deploy CloudFormation stack and return outputs."""
    cfn = boto3.client("cloudformation", region_name=REGION)
    template_path = Path(__file__).parent / "oauth_gateway_from_agent" / "oauth_gateway_infra.yaml"

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

    response = cfn.describe_stacks(StackName=CFN_STACK_NAME)
    return {o["OutputKey"]: o["OutputValue"] for o in response["Stacks"][0].get("Outputs", [])}


def create_boto3_layer():
    """Create and attach boto3 layer to Lambda for bedrock-agentcore support."""
    import io
    import subprocess
    import tempfile
    import zipfile

    lambda_client = boto3.client("lambda", region_name=REGION)
    layer_name = f"{STACK_NAME}-boto3-layer"
    function_name = f"{STACK_NAME}-oauth-callback"

    # Check if layer already exists and is attached
    try:
        func = lambda_client.get_function(FunctionName=function_name)
        layers = func.get("Configuration", {}).get("Layers", [])
        if any(layer_name in layer.get("Arn", "") for layer in layers):
            print("  ✓ boto3 layer already attached")
            return
    except Exception:
        pass

    # Create layer zip with latest boto3
    with tempfile.TemporaryDirectory() as tmpdir:
        python_dir = Path(tmpdir) / "python"
        python_dir.mkdir()
        subprocess.run(
            ["uv", "pip", "install", "boto3", "--target", str(python_dir), "-q", "--upgrade"],
            check=True, capture_output=True
        )

        # Create zip in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in python_dir.rglob("*"):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(tmpdir))
                    zf.write(file_path, arcname)
        zip_buffer.seek(0)

        # Publish layer
        resp = lambda_client.publish_layer_version(
            LayerName=layer_name,
            Description="Latest boto3 with bedrock-agentcore support",
            Content={"ZipFile": zip_buffer.read()},
            CompatibleRuntimes=["python3.12"],
        )
        layer_arn = resp["LayerVersionArn"]

    # Attach layer to Lambda function
    lambda_client.update_function_configuration(
        FunctionName=function_name,
        Layers=[layer_arn]
    )


def create_inbound_cognito_provider(cfn_outputs: dict) -> dict:
    """Create AgentCore OAuth Provider for Cognito (Inbound - user authentication)."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    provider_name = f"{STACK_NAME}-inbound-cognito"
    cognito_domain = cfn_outputs.get("InboundCognitoDomain", "")

    cognito = boto3.client("cognito-idp", region_name=REGION)
    resp = cognito.describe_user_pool_client(
        UserPoolId=cfn_outputs["InboundUserPoolId"],
        ClientId=cfn_outputs["InboundClientId"]
    )
    client_secret = resp["UserPoolClient"]["ClientSecret"]

    try:
        response = client.create_oauth2_credential_provider(
            name=provider_name,
            credentialProviderVendor="CognitoOauth2",
            oauth2ProviderConfigInput={
                "includedOauth2ProviderConfig": {
                    "clientId": cfn_outputs["InboundClientId"],
                    "clientSecret": client_secret,
                    "issuer": f"https://cognito-idp.{REGION}.amazonaws.com/{cfn_outputs['InboundUserPoolId']}",
                    "authorizationEndpoint": f"https://{cognito_domain}.auth.{REGION}.amazoncognito.com/oauth2/authorize",
                    "tokenEndpoint": f"https://{cognito_domain}.auth.{REGION}.amazoncognito.com/oauth2/token",
                }
            },
        )
    except (client.exceptions.ConflictException, client.exceptions.ValidationException):
        response = client.get_oauth2_credential_provider(name=provider_name)

    # Get AgentCore Identity callback URL (with UUID) for Cognito to redirect to
    agentcore_callback_url = response.get("callbackUrl", "")

    # Update Cognito client with AgentCore callback URL (for inbound auth flow)
    cognito.update_user_pool_client(
        UserPoolId=cfn_outputs["InboundUserPoolId"],
        ClientId=cfn_outputs["InboundClientId"],
        CallbackURLs=[agentcore_callback_url],
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["openid", "email", "profile"],
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["Google", "COGNITO"],
    )
    print(f"    ✓ Updated Cognito CallbackURLs with AgentCore callback: {agentcore_callback_url}")

    return {
        "inbound_provider_arn": response.get("credentialProviderArn", response.get("oauth2CredentialProviderArn", "")),
        "inbound_provider_name": provider_name,
        "inbound_provider_callback_url": agentcore_callback_url,
    }


def create_outbound_google_provider() -> dict:
    """Create AgentCore OAuth Provider for Google (Outbound - YouTube API access)."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    provider_name = f"{STACK_NAME}-outbound-google"

    try:
        response = client.create_oauth2_credential_provider(
            name=provider_name,
            credentialProviderVendor="GoogleOauth2",
            oauth2ProviderConfigInput={
                "googleOauth2ProviderConfig": {"clientId": GOOGLE_CLIENT_ID, "clientSecret": GOOGLE_CLIENT_SECRET}
            },
        )
    except (client.exceptions.ConflictException, client.exceptions.ValidationException):
        response = client.get_oauth2_credential_provider(name=provider_name)

    return {
        "outbound_provider_arn": response.get("credentialProviderArn", response.get("oauth2CredentialProviderArn", "")),
        "outbound_provider_name": provider_name,
        "outbound_callback_url": response.get("callbackUrl", ""),
    }


def create_gateway(cfn_outputs: dict) -> dict:
    """Create AgentCore Gateway with CUSTOM_JWT auth."""
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    gateway_name = f"{STACK_NAME}-gateway"
    callback_url = cfn_outputs["OAuthCallbackUrl"]

    def ensure_workload_identity(gw_id: str):
        """Ensure workload identity has callback URL registered."""
        client.update_workload_identity(
            name=gw_id,
            allowedResourceOauth2ReturnUrls=[callback_url, callback_url.rstrip("/") + "/inbound"]
        )

    # Check if gateway already exists
    existing = client.list_gateways(maxResults=100)
    for gw in existing.get("items", []):
        if gw.get("name") == gateway_name:
            status = gw.get("status", "")
            gateway_id = gw["gatewayId"]
            if status == "READY":
                details = client.get_gateway(gatewayIdentifier=gateway_id)
                ensure_workload_identity(gateway_id)
                return {"gateway_id": gateway_id, "gateway_name": gateway_name, "gateway_endpoint": details.get("gatewayUrl", "")}
            elif status == "CREATING":
                print("    ⏳ Waiting for existing gateway to be ready...")
                while status == "CREATING":
                    time.sleep(5)
                    details = client.get_gateway(gatewayIdentifier=gateway_id)
                    status = details.get("status", "")
                if status == "READY":
                    ensure_workload_identity(gateway_id)
                    return {"gateway_id": gateway_id, "gateway_name": gateway_name, "gateway_endpoint": details.get("gatewayUrl", "")}

    # Create new gateway (no interceptor)
    response = client.create_gateway(
        name=gateway_name,
        roleArn=cfn_outputs["GatewayRoleArn"],
        protocolType="MCP",
        protocolConfiguration={"mcp": {"supportedVersions": ["2025-11-25"], "searchType": "SEMANTIC"}},
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration={
            "customJWTAuthorizer": {
                "discoveryUrl": cfn_outputs["InboundDiscoveryUrl"],
                "allowedClients": [cfn_outputs["InboundClientId"]],
            }
        },
        exceptionLevel="DEBUG",
    )
    gateway_id = response["gatewayId"]

    print("    ⏳ Waiting for gateway to be ready...")
    while True:
        details = client.get_gateway(gatewayIdentifier=gateway_id)
        status = details.get("status", "")
        if status == "READY":
            break
        if status == "FAILED":
            raise Exception("Gateway creation failed")
        time.sleep(5)

    ensure_workload_identity(gateway_id)
    return {"gateway_id": gateway_id, "gateway_name": gateway_name, "gateway_endpoint": details.get("gatewayUrl", "")}


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
            targetConfiguration={"mcp": {"openApiSchema": {"inlinePayload": json.dumps(openapi_spec)}}},
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
        targets = client.list_gateway_targets(gatewayIdentifier=gateway_id, maxResults=100)
        for t in targets.get("items", []):
            if t.get("name") == target_name:
                return {"target_id": t["targetId"], "target_name": target_name}
        raise Exception(f"Target {target_name} not found")

    return {"target_id": target_id, "target_name": target_name}


def cleanup():
    """Delete all resources."""
    print(f"Region: {REGION}")
    print("Starting cleanup...\n")

    config_path = Path(__file__).parent / "config.json"
    config = json.load(open(config_path)) if config_path.exists() else {}

    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    cfn = boto3.client("cloudformation", region_name=REGION)

    print("Step 1: Deleting AgentCore resources...")
    gateway_id = config.get("gateway_id")
    if gateway_id:
        try:
            control_client.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=config.get("target_id", ""))
            print("  ✓ Deleted Gateway Target")
        except Exception as e:
            print(f"  ⚠ {e}")
        try:
            control_client.delete_gateway(gatewayIdentifier=gateway_id)
            print("  ✓ Deleted Gateway")
        except Exception as e:
            print(f"  ⚠ {e}")

    for provider in [f"{STACK_NAME}-outbound-google", f"{STACK_NAME}-inbound-cognito"]:
        try:
            control_client.delete_oauth2_credential_provider(name=provider)
            print(f"  ✓ Deleted OAuth Provider ({provider})")
        except Exception as e:
            print(f"  ⚠ {e}")

    print("\nStep 2: Deleting CloudFormation stack...")
    try:
        bucket_name = config.get("BucketName")
        if bucket_name:
            s3 = boto3.client("s3", region_name=REGION)
            try:
                for obj in s3.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                    s3.delete_object(Bucket=bucket_name, Key=obj["Key"])
            except Exception:
                pass

        cfn.delete_stack(StackName=CFN_STACK_NAME)
        print("  ⏳ Deleting stack...")
        cfn.get_waiter("stack_delete_complete").wait(StackName=CFN_STACK_NAME, WaiterConfig={"Delay": 10, "MaxAttempts": 60})
        print(f"  ✓ Stack deleted: {CFN_STACK_NAME}")
    except Exception as e:
        print(f"  ⚠ {e}")

    if config_path.exists():
        config_path.unlink()
    print("\n✓ Cleanup complete")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--clean":
        cleanup()
    else:
        main()

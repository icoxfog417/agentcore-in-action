"""Build AgentCore components for MCP Server with OAuth Gateway"""
import json
import os
import sys
import time
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
OAUTH_CALLBACK_URL = os.getenv("OAUTH_CALLBACK_URL", "http://localhost:8080/oauth/callback")
CONFIG_FILE = "config.json"


def create_gateway_role(iam_client):
    """Create IAM role for Gateway"""
    role_name = f"github-gateway-role-{int(time.time())}"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy)
    )

    # Attach policy for gateway operations
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess'
    )

    print(f"✓ Created IAM role: {role_name}")
    return response["Role"]["Arn"], role_name


def create_runtime_role(iam_client):
    """Create IAM role for AgentCore Runtime (MCP Server)"""
    role_name = f"github-mcp-runtime-role-{int(time.time())}"

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    response = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy)
    )

    # Attach policies for runtime operations
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess'
    )

    print(f"✓ Created Runtime IAM role: {role_name}")
    return response["Role"]["Arn"], role_name


def create_workload_identity(control_client):
    """Create Workload Identity for OAuth token storage"""
    identity_response = control_client.create_workload_identity(
        name=f"github-workload-identity-{int(time.time())}",
        allowedResourceOauth2ReturnUrls=[OAUTH_CALLBACK_URL]
    )

    identity_arn = identity_response["workloadIdentityArn"]
    identity_name = identity_response["name"]
    print(f"✓ Created Workload Identity: {identity_name}")
    return identity_arn, identity_name


def create_oauth_provider(control_client):
    """Create OAuth credential provider for GitHub"""
    provider_response = control_client.create_oauth2_credential_provider(
        name=f"github-oauth-provider-{int(time.time())}",
        credentialProviderVendor="GitHubOauth2",
        oauth2ProviderConfigInput={
            "gitHubOauth2ProviderConfig": {
                "clientId": GITHUB_CLIENT_ID,
                "clientSecret": GITHUB_CLIENT_SECRET
            }
        }
    )

    provider_arn = provider_response["providerArn"]
    provider_name = provider_response["name"]
    callback_url = provider_response["callbackUrl"]

    print(f"✓ Created OAuth Provider: {provider_name}")
    print(f"⚠ Register this callback URL with GitHub OAuth App:")
    print(f"  {callback_url}")

    return provider_arn, provider_name, callback_url


def create_gateway(control_client, role_arn, identity_arn):
    """Create Gateway with Identity-based authentication"""
    gateway_response = control_client.create_gateway(
        name=f"github-gateway-{int(time.time())}",
        protocolType="MCP",
        protocolConfiguration={
            "mcp": {
                "supportedVersions": ["2025-11-25"],
                "searchType": "SEMANTIC"
            }
        },
        authorizerType="WORKLOAD_IDENTITY",
        authorizerConfiguration={
            "workloadIdentityAuthorizer": {
                "workloadIdentityArn": identity_arn
            }
        },
        roleArn=role_arn
    )

    gateway_id = gateway_response["gatewayId"]
    gateway_url = gateway_response["gatewayUrl"]

    print(f"✓ Created Gateway: {gateway_id}")
    print(f"  Gateway URL: {gateway_url}")

    # Wait for gateway to be ready
    print("Waiting for gateway to be ready...")
    waiter_count = 0
    while waiter_count < 30:
        try:
            status = control_client.get_gateway(gatewayIdentifier=gateway_id)
            if status["status"] == "AVAILABLE":
                print("✓ Gateway is ready")
                break
        except Exception as e:
            pass
        time.sleep(10)
        waiter_count += 1

    return gateway_id, gateway_url


def create_gateway_target(control_client, gateway_id, provider_arn):
    """Create Gateway Target with GitHub API spec"""
    # GitHub API OpenAPI specification
    github_api_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "GitHub API",
            "version": "v3"
        },
        "servers": [{
            "url": "https://api.github.com"
        }],
        "paths": {
            "/user/repos": {
                "get": {
                    "operationId": "getUserRepos",
                    "summary": "List repositories for the authenticated user",
                    "parameters": [
                        {
                            "name": "per_page",
                            "in": "query",
                            "schema": {"type": "integer", "default": 30}
                        },
                        {
                            "name": "sort",
                            "in": "query",
                            "schema": {"type": "string", "enum": ["created", "updated", "pushed", "full_name"]}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/user": {
                "get": {
                    "operationId": "getUserProfile",
                    "summary": "Get the authenticated user",
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    target_response = control_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="GitHubTarget",
        targetConfiguration={
            "mcp": {
                "openApiSchema": {
                    "inlinePayload": json.dumps(github_api_spec)
                }
            }
        },
        credentialProviderConfigurations=[{
            "credentialProviderType": "OAUTH",
            "credentialProvider": {
                "oauthCredentialProvider": {
                    "providerArn": provider_arn,
                    "grantType": "AUTHORIZATION_CODE",
                    "defaultReturnUrl": OAUTH_CALLBACK_URL,
                    "scopes": ["repo", "user"]
                }
            }
        }]
    )

    target_id = target_response["targetId"]
    print(f"✓ Created Gateway Target: {target_id}")
    return target_id


def deploy_mcp_server(control_client, runtime_role_arn, gateway_url, gateway_id):
    """Deploy MCP server to AgentCore Runtime"""
    # Create runtime configuration
    runtime_response = control_client.create_runtime(
        name=f"github-mcp-server-{int(time.time())}",
        runtimeType="CONTAINER",
        runtimeConfiguration={
            "container": {
                "imageUri": "public.ecr.aws/bedrock-agentcore/mcp-server:latest",  # Placeholder
                "environment": {
                    "GATEWAY_URL": gateway_url,
                    "GATEWAY_ID": gateway_id,
                    "AWS_REGION": REGION
                }
            }
        },
        roleArn=runtime_role_arn
    )

    runtime_id = runtime_response["runtimeId"]
    runtime_arn = runtime_response["runtimeArn"]

    print(f"✓ Created Runtime: {runtime_id}")
    print(f"  Runtime ARN: {runtime_arn}")

    return runtime_id, runtime_arn


def save_config(config):
    """Save configuration to JSON file"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"✓ Configuration saved to {CONFIG_FILE}")


def cleanup_resources():
    """Delete all created resources"""
    if not os.path.exists(CONFIG_FILE):
        print(f"No {CONFIG_FILE} found. Nothing to cleanup.")
        return

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    iam_client = boto3.client("iam", region_name=REGION)

    # Delete in reverse order
    print("Cleaning up resources...")

    # Delete Runtime
    if "runtime_id" in config:
        try:
            control_client.delete_runtime(runtimeIdentifier=config["runtime_id"])
            print(f"✓ Deleted Runtime: {config['runtime_id']}")
        except Exception as e:
            print(f"Failed to delete Runtime: {e}")

    # Delete Gateway Target
    if "target_id" in config and "gateway_id" in config:
        try:
            control_client.delete_gateway_target(
                gatewayIdentifier=config["gateway_id"],
                targetIdentifier=config["target_id"]
            )
            print(f"✓ Deleted Gateway Target: {config['target_id']}")
            time.sleep(10)  # Wait for target deletion to propagate
        except Exception as e:
            print(f"Failed to delete Gateway Target: {e}")

    # Delete Gateway
    if "gateway_id" in config:
        try:
            control_client.delete_gateway(gatewayIdentifier=config["gateway_id"])
            print(f"✓ Deleted Gateway: {config['gateway_id']}")
        except Exception as e:
            print(f"Failed to delete Gateway: {e}")

    # Delete OAuth Provider
    if "provider_name" in config:
        try:
            control_client.delete_oauth2_credential_provider(name=config["provider_name"])
            print(f"✓ Deleted OAuth Provider: {config['provider_name']}")
        except Exception as e:
            print(f"Failed to delete OAuth Provider: {e}")

    # Delete Workload Identity
    if "identity_name" in config:
        try:
            control_client.delete_workload_identity(name=config["identity_name"])
            print(f"✓ Deleted Workload Identity: {config['identity_name']}")
        except Exception as e:
            print(f"Failed to delete Workload Identity: {e}")

    # Delete IAM roles
    for role_name in [config.get("gateway_role_name"), config.get("runtime_role_name")]:
        if role_name:
            try:
                # Detach policies first
                policies = iam_client.list_attached_role_policies(RoleName=role_name)
                for policy in policies["AttachedPolicies"]:
                    iam_client.detach_role_policy(
                        RoleName=role_name,
                        PolicyArn=policy["PolicyArn"]
                    )
                iam_client.delete_role(RoleName=role_name)
                print(f"✓ Deleted IAM role: {role_name}")
            except Exception as e:
                print(f"Failed to delete IAM role {role_name}: {e}")

    # Remove config file
    os.remove(CONFIG_FILE)
    print(f"✓ Removed {CONFIG_FILE}")


def main():
    """Main construction flow"""
    import argparse
    parser = argparse.ArgumentParser(description="Build AgentCore components")
    parser.add_argument("--cleanup", action="store_true", help="Delete all resources")
    args = parser.parse_args()

    if args.cleanup:
        cleanup_resources()
        return

    # Validate environment
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        print("Error: GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET required in .env")
        sys.exit(1)

    print("Building AgentCore components for MCP Server with OAuth Gateway...\n")

    iam_client = boto3.client("iam", region_name=REGION)
    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    try:
        # Step 1: Create IAM roles
        print("Step 1: Creating IAM roles...")
        gateway_role_arn, gateway_role_name = create_gateway_role(iam_client)
        runtime_role_arn, runtime_role_name = create_runtime_role(iam_client)
        print()

        # Step 2: Create Workload Identity
        print("Step 2: Creating Workload Identity...")
        identity_arn, identity_name = create_workload_identity(control_client)
        print()

        # Step 3: Create OAuth Provider
        print("Step 3: Creating OAuth Provider...")
        provider_arn, provider_name, callback_url = create_oauth_provider(control_client)
        print()

        # Step 4: Create Gateway
        print("Step 4: Creating Gateway...")
        gateway_id, gateway_url = create_gateway(control_client, gateway_role_arn, identity_arn)
        print()

        # Step 5: Create Gateway Target
        print("Step 5: Creating Gateway Target...")
        target_id = create_gateway_target(control_client, gateway_id, provider_arn)
        print()

        # Step 6: Deploy MCP Server (Note: This is placeholder - actual deployment varies)
        print("Step 6: MCP Server deployment...")
        print("⚠ Note: MCP server deployment to AgentCore Runtime is configured via runtime creation")
        print("  In production, you would deploy a containerized MCP server")
        print("  For this example, you'll run the server locally and connect via mcp-proxy-for-aws")
        runtime_id = "local"  # Placeholder for local development
        runtime_arn = "local"
        print()

        # Save configuration
        config = {
            "gateway_id": gateway_id,
            "gateway_url": gateway_url,
            "gateway_role_arn": gateway_role_arn,
            "gateway_role_name": gateway_role_name,
            "runtime_role_arn": runtime_role_arn,
            "runtime_role_name": runtime_role_name,
            "identity_arn": identity_arn,
            "identity_name": identity_name,
            "provider_arn": provider_arn,
            "provider_name": provider_name,
            "target_id": target_id,
            "runtime_id": runtime_id,
            "runtime_arn": runtime_arn,
            "oauth_callback_url": callback_url,
            "region": REGION
        }

        save_config(config)

        print("\n✅ Construction complete!")
        print("\nNext steps:")
        print("1. Register the OAuth callback URL with your GitHub OAuth App:")
        print(f"   {callback_url}")
        print("2. Run the MCP server: uv run python main.py")
        print("3. Configure Claude Desktop to connect via mcp-proxy-for-aws")

    except Exception as e:
        print(f"\n❌ Error during construction: {e}")
        print("Run with --cleanup to remove partial resources")
        sys.exit(1)


if __name__ == "__main__":
    main()

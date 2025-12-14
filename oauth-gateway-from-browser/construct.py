"""Build AgentCore components for YouTube OAuth example"""
import json
import os
import sys
import time
import boto3
from dotenv import load_dotenv

load_dotenv()

REGION = os.getenv("AWS_REGION", "us-east-1")
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:8080/oauth2/callback")
CONFIG_FILE = "config.json"


def create_gateway_role(iam_client):
    """Create IAM role for Gateway"""
    role_name = f"youtube-gateway-role-{int(time.time())}"
    
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
    return response["Role"]["Arn"]


def create_cognito_resources(cognito_client):
    """Create Cognito user pool and client"""
    # Create user pool
    pool_response = cognito_client.create_user_pool(
        PoolName=f"youtube-agent-users-{int(time.time())}",
        Policies={
            "PasswordPolicy": {
                "MinimumLength": 8,
                "RequireUppercase": False,
                "RequireLowercase": False,
                "RequireNumbers": False,
                "RequireSymbols": False
            }
        }
    )
    user_pool_id = pool_response["UserPool"]["Id"]
    print(f"✓ Created user pool: {user_pool_id}")
    
    # Create domain
    domain_prefix = f"youtube-gw-{user_pool_id.lower().replace('_', '-')[:20]}"
    cognito_client.create_user_pool_domain(
        Domain=domain_prefix,
        UserPoolId=user_pool_id
    )
    print(f"✓ Created domain: {domain_prefix}")
    
    # Create resource server
    resource_server_id = "youtube-gateway-resources"
    cognito_client.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier=resource_server_id,
        Name="YouTube Gateway Resources",
        Scopes=[{
            "ScopeName": "YouTubeTarget",
            "ScopeDescription": "Access to YouTube Gateway target"
        }]
    )
    print(f"✓ Created resource server: {resource_server_id}")
    
    # Create app client
    client_response = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName="youtube-agent-client",
        GenerateSecret=False,
        AllowedOAuthFlows=["code"],
        AllowedOAuthFlowsUserPoolClient=True,
        AllowedOAuthScopes=[
            "openid",
            f"{resource_server_id}/YouTubeTarget"
        ],
        CallbackURLs=["http://localhost:8080/cognito/callback"],
        SupportedIdentityProviders=["COGNITO"]
    )
    cognito_client_id = client_response["UserPoolClient"]["ClientId"]
    print(f"✓ Created app client: {cognito_client_id}")
    
    discovery_url = f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
    
    return user_pool_id, cognito_client_id, discovery_url, domain_prefix


def create_workload_identity(control_client):
    """Create AgentCore workload identity"""
    response = control_client.create_workload_identity(
        name=f"youtube-workload-identity-{int(time.time())}",
        allowedResourceOauth2ReturnUrls=[CALLBACK_URL]
    )
    
    identity_arn = response["workloadIdentityArn"]
    print(f"✓ Created workload identity: {identity_arn}")
    return identity_arn


def create_oauth_provider(control_client):
    """Create OAuth credential provider for YouTube"""
    response = control_client.create_oauth2_credential_provider(
        name=f"youtube-oauth-provider-{int(time.time())}",
        credentialProviderVendor="GoogleOauth2",
        oauth2ProviderConfigInput={
            "googleOauth2ProviderConfig": {
                "clientId": YOUTUBE_CLIENT_ID,
                "clientSecret": YOUTUBE_CLIENT_SECRET
            }
        }
    )
    
    provider_arn = response["credentialProviderArn"]
    callback_url = response["callbackUrl"]
    print(f"✓ Created OAuth provider: {provider_arn}")
    print(f"  Callback URL: {callback_url}")
    return provider_arn, callback_url


def create_gateway(control_client, role_arn, cognito_client_id, cognito_discovery_url):
    """Create Gateway with Cognito authorizer"""
    response = control_client.create_gateway(
        name=f"youtube-gateway-{int(time.time())}",
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
                "discoveryUrl": cognito_discovery_url,
                "allowedClients": [cognito_client_id],
                "allowedScopes": ["youtube-gateway-resources/YouTubeTarget"]
            }
        },
        roleArn=role_arn,
        exceptionLevel="DEBUG"
    )
    
    gateway_id = response["gatewayId"]
    gateway_url = response["gatewayUrl"]
    print(f"✓ Created gateway: {gateway_id}")
    
    # Wait for gateway to be ready
    print("  Waiting for gateway to be ready...")
    while True:
        status_response = control_client.get_gateway(gatewayIdentifier=gateway_id)
        status = status_response["status"]
        if status == "READY":
            break
        time.sleep(5)
    
    print(f"  Gateway URL: {gateway_url}")
    return gateway_id, gateway_url


def create_gateway_target(control_client, gateway_id, provider_arn):
    """Create Gateway target linking OAuth provider"""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "YouTube API", "version": "v3"},
        "servers": [{"url": "https://www.googleapis.com/youtube/v3"}],
        "paths": {
            "/channels": {
                "get": {
                    "operationId": "getChannels",
                    "parameters": [
                        {"name": "part", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "mine", "in": "query", "schema": {"type": "boolean"}}
                    ],
                    "responses": {
                        "200": {"description": "Successful response"}
                    }
                }
            },
            "/subscriptions": {
                "get": {
                    "operationId": "getSubscriptions",
                    "parameters": [
                        {"name": "part", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "mine", "in": "query", "schema": {"type": "boolean"}},
                        {"name": "maxResults", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {
                        "200": {"description": "Successful response"}
                    }
                }
            }
        }
    }
    
    response = control_client.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="YouTubeTarget",
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
                    "defaultReturnUrl": CALLBACK_URL,
                    "scopes": ["https://www.googleapis.com/auth/youtube.readonly"]
                }
            }
        }]
    )
    
    target_id = response["targetId"]
    print(f"✓ Created gateway target: {target_id}")
    return target_id


def cleanup(config):
    """Delete all created resources"""
    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    cognito_client = boto3.client("cognito-idp", region_name=REGION)
    iam_client = boto3.client("iam", region_name=REGION)
    
    # Delete gateway target first
    if "gateway_id" in config and "target_id" in config:
        try:
            control_client.delete_gateway_target(
                gatewayIdentifier=config["gateway_id"],
                targetId=config["target_id"]
            )
            print(f"✓ Deleted gateway target: {config['target_id']}")
            print("  Waiting for target deletion to complete...")
            time.sleep(10)
        except Exception as e:
            print(f"✗ Failed to delete gateway target: {e}")
    
    # Delete gateway
    if "gateway_id" in config:
        try:
            control_client.delete_gateway(gatewayIdentifier=config["gateway_id"])
            print(f"✓ Deleted gateway: {config['gateway_id']}")
        except Exception as e:
            print(f"✗ Failed to delete gateway: {e}")
    
    # Delete OAuth provider
    if "provider_arn" in config:
        try:
            provider_name = config["provider_arn"].split("/")[-1]
            control_client.delete_oauth2_credential_provider(name=provider_name)
            print("✓ Deleted OAuth provider")
        except Exception as e:
            print(f"✗ Failed to delete OAuth provider: {e}")
    
    # Delete workload identity
    if "identity_arn" in config:
        try:
            # Extract name from ARN: arn:aws:bedrock-agentcore:region:account:workload-identity-directory/default/workload-identity/NAME
            identity_name = config["identity_arn"].split("/")[-1]
            control_client.delete_workload_identity(name=identity_name)
            print("✓ Deleted workload identity")
        except Exception as e:
            print(f"✗ Failed to delete workload identity: {e}")
    
    # Delete Cognito resources
    if "user_pool_id" in config:
        try:
            # Delete domain first
            domain_prefix = f"youtube-gw-{config['user_pool_id'].lower().replace('_', '-')[:20]}"
            cognito_client.delete_user_pool_domain(Domain=domain_prefix, UserPoolId=config["user_pool_id"])
            cognito_client.delete_user_pool(UserPoolId=config["user_pool_id"])
            print("✓ Deleted Cognito user pool")
        except Exception as e:
            print(f"✗ Failed to delete Cognito: {e}")
    
    # Delete IAM role
    if "role_arn" in config:
        try:
            role_name = config["role_arn"].split("/")[-1]
            iam_client.detach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/AdministratorAccess'
            )
            iam_client.delete_role(RoleName=role_name)
            print("✓ Deleted IAM role")
        except Exception as e:
            print(f"✗ Failed to delete IAM role: {e}")


def main():
    if "--cleanup" in sys.argv:
        if not os.path.exists(CONFIG_FILE):
            print("No config.json found")
            return
        
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        
        cleanup(config)
        os.remove(CONFIG_FILE)
        print("✓ Cleanup complete")
        return
    
    # Validate environment
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        print("Error: YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET required in .env")
        sys.exit(1)
    
    print("Building AgentCore components...")
    
    iam_client = boto3.client("iam", region_name=REGION)
    cognito_client = boto3.client("cognito-idp", region_name=REGION)
    control_client = boto3.client("bedrock-agentcore-control", region_name=REGION)
    
    # Build resources
    role_arn = create_gateway_role(iam_client)
    user_pool_id, cognito_client_id, cognito_discovery_url, domain_prefix = create_cognito_resources(cognito_client)
    identity_arn = create_workload_identity(control_client)
    provider_arn, oauth_callback_url = create_oauth_provider(control_client)
    gateway_id, gateway_url = create_gateway(control_client, role_arn, cognito_client_id, cognito_discovery_url)
    target_id = create_gateway_target(control_client, gateway_id, provider_arn)
    
    # Save config
    config = {
        "gateway_id": gateway_id,
        "gateway_url": gateway_url,
        "identity_arn": identity_arn,
        "user_pool_id": user_pool_id,
        "cognito_client_id": cognito_client_id,
        "cognito_discovery_url": cognito_discovery_url,
        "cognito_domain_prefix": domain_prefix,
        "provider_arn": provider_arn,
        "oauth_callback_url": oauth_callback_url,
        "role_arn": role_arn,
        "target_id": target_id
    }
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✓ Configuration saved to {CONFIG_FILE}")
    print("\n⚠️  IMPORTANT: Register this URL in Google Cloud Console:")
    print(f"   {oauth_callback_url}")
    print("   Go to: APIs & Services → Credentials → OAuth 2.0 Client ID")
    print("   Add to: Authorized redirect URIs")


if __name__ == "__main__":
    main()

"""Gateway Interceptor Lambda for OAuth token injection."""

import base64
import json
import os

import boto3


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (claims extraction only)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format")
    payload = parts[1]
    # Add padding if needed
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += "=" * padding
    return json.loads(base64.urlsafe_b64decode(payload))


def extract_google_user_id(jwt_claims: dict) -> str | None:
    """Extract Google user ID from Cognito JWT identities claim."""
    identities_str = jwt_claims.get("identities")
    if not identities_str:
        return None
    identities = json.loads(identities_str) if isinstance(identities_str, str) else identities_str
    for identity in identities:
        if identity.get("providerName") == "Google":
            return identity.get("userId")
    return None


def handler(event: dict, context) -> dict:
    """Lambda handler for Gateway interceptor."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    provider_arn = os.environ.get("OAUTH_PROVIDER_ARN", "")

    # Extract JWT from request headers
    mcp = event.get("mcp", {})
    gateway_request = mcp.get("gatewayRequest", {})
    headers = gateway_request.get("headers", {})
    auth_header = headers.get("Authorization", headers.get("authorization", ""))

    if not auth_header.startswith("Bearer "):
        return _error_response(401, "Missing or invalid Authorization header")

    jwt_token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        claims = decode_jwt_payload(jwt_token)
    except Exception as e:
        return _error_response(401, f"Invalid JWT: {e}")

    # Extract Google user ID from federated identity
    google_user_id = extract_google_user_id(claims)
    if not google_user_id:
        # Fall back to sub claim for non-federated users
        google_user_id = claims.get("sub")

    if not google_user_id:
        return _error_response(401, "Cannot determine user identity")

    # Get OAuth token from Token Vault
    client = boto3.client("bedrock-agentcore", region_name=region)
    try:
        response = client.get_resource_oauth2_token(
            oauth2CredentialProviderArn=provider_arn,
            userIdentifier=google_user_id,
        )
        access_token = response.get("accessToken")
        if access_token:
            return _inject_token_response(event, access_token)
        # Token not found - return authorization URL
        auth_url = response.get("authorizationUrl", "")
        return _auth_required_response(auth_url)
    except client.exceptions.ResourceNotFoundException:
        # No token stored - need user authorization
        try:
            response = client.get_resource_oauth2_token(
                oauth2CredentialProviderArn=provider_arn,
                userIdentifier=google_user_id,
            )
            auth_url = response.get("authorizationUrl", "")
            return _auth_required_response(auth_url)
        except Exception:
            return _error_response(500, "Failed to get authorization URL")
    except Exception as e:
        return _error_response(500, f"Token retrieval failed: {e}")


def _inject_token_response(event: dict, access_token: str) -> dict:
    """Return transformedGatewayRequest with injected Authorization header."""
    mcp = event.get("mcp", {})
    gateway_request = mcp.get("gatewayRequest", {})
    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayRequest": {
                "headers": {"Authorization": f"Bearer {access_token}"},
                "body": gateway_request.get("body", {}),
            }
        },
    }


def _auth_required_response(auth_url: str) -> dict:
    """Return transformedGatewayResponse for OAuth elicitation."""
    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayResponse": {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": {
                    "error": "authorization_required",
                    "authorizationUrl": auth_url,
                    "message": "User must authorize YouTube API access",
                },
            }
        },
    }


def _error_response(status_code: int, message: str) -> dict:
    """Return error response."""
    return {
        "interceptorOutputVersion": "1.0",
        "mcp": {
            "transformedGatewayResponse": {
                "statusCode": status_code,
                "headers": {"Content-Type": "application/json"},
                "body": {"error": message},
            }
        },
    }

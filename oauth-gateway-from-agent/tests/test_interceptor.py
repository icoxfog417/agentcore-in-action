"""Tests for Gateway Interceptor Lambda."""

import base64
import json

import pytest

from oauth_gateway_from_agent.interceptor import (
    decode_jwt_payload,
    extract_google_user_id,
    _inject_token_response,
    _auth_required_response,
)


def _make_jwt(payload: dict) -> str:
    """Create a mock JWT token with given payload."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "RS256"}).encode()).decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    sig = base64.urlsafe_b64encode(b"fake_signature").decode().rstrip("=")
    return f"{header}.{body}.{sig}"


class TestDecodeJwtPayload:
    def test_decode_valid_jwt(self):
        payload = {"sub": "user123", "email": "test@example.com"}
        token = _make_jwt(payload)
        result = decode_jwt_payload(token)
        assert result["sub"] == "user123"
        assert result["email"] == "test@example.com"

    def test_decode_invalid_jwt_format(self):
        with pytest.raises(ValueError, match="Invalid JWT format"):
            decode_jwt_payload("not.a.valid.jwt.token")


class TestExtractGoogleUserId:
    def test_extract_from_identities(self):
        claims = {
            "sub": "cognito-sub-123",
            "identities": json.dumps([
                {"providerName": "Google", "userId": "google-user-456"}
            ])
        }
        result = extract_google_user_id(claims)
        assert result == "google-user-456"

    def test_no_identities_claim(self):
        claims = {"sub": "cognito-sub-123"}
        result = extract_google_user_id(claims)
        assert result is None

    def test_no_google_provider(self):
        claims = {
            "identities": json.dumps([
                {"providerName": "Facebook", "userId": "fb-user-789"}
            ])
        }
        result = extract_google_user_id(claims)
        assert result is None


class TestInjectTokenResponse:
    def test_inject_token_response(self):
        event = {
            "mcp": {
                "gatewayRequest": {
                    "body": {"jsonrpc": "2.0", "method": "tools/call"}
                }
            }
        }
        result = _inject_token_response(event, "google-access-token-xyz")
        assert result["interceptorOutputVersion"] == "1.0"
        transformed = result["mcp"]["transformedGatewayRequest"]
        assert transformed["headers"]["Authorization"] == "Bearer google-access-token-xyz"
        assert transformed["body"]["method"] == "tools/call"


class TestAuthRequiredResponse:
    def test_auth_required_response(self):
        auth_url = "https://accounts.google.com/o/oauth2/auth?..."
        result = _auth_required_response(auth_url)
        assert result["interceptorOutputVersion"] == "1.0"
        response = result["mcp"]["transformedGatewayResponse"]
        assert response["statusCode"] == 401
        assert response["body"]["error"] == "authorization_required"
        assert response["body"]["authorizationUrl"] == auth_url

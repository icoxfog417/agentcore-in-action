# OAuth Authentication Flow Architecture

## Overview
This document describes the OAuth authentication flow for the MCP OAuth Gateway example with a custom callback server implementation.

## Flow Components

### Inbound Authentication
**Purpose**: User authenticates via Cognito (with optional Google federation) to access the agent

### Outbound Authentication (API Access)
**Purpose**: Agent accesses external APIs (e.g., YouTube) on behalf of the user

## Outbound OAuth Flow (USER_FEDERATION)

```
1. Agent calls GetResourceOauth2Token API
2. AgentCore Identity returns authorizationUrl + sessionUri
3. User navigates to authorizationUrl and grants consent
4. OAuth provider redirects to AgentCore callback URL with authorization code
5. AgentCore redirects user to application callback URL with session_id
6. Callback server verifies user session and calls CompleteResourceTokenAuth
7. AgentCore exchanges code for tokens and stores in Token Vault
8. Agent polls GetResourceOauth2Token until token available
```

## Callback URL Architecture

### AgentCore Identity Callback (OAuth Provider → AgentCore)
- **URL**: Returned by `CreateOauth2CredentialProvider` API
- **Format**: `https://bedrock-agentcore.{region}.amazonaws.com/identities/oauth2/callback/{provider-uuid}`
- **Example**: `https://bedrock-agentcore.us-east-1.amazonaws.com/identities/oauth2/callback/6c78748a-421d-4e26-b404-1a9b5861a75d`
- **Registration**: Must be registered in the OAuth provider's allowed redirect URIs

### Application Callback (AgentCore → Your Callback Server)
- **URL**: Configured via `AllowedResourceOauth2ReturnUrl` in workload identity
- **Receives**: `session_id` query parameter
- **Requirement**: Must call `CompleteResourceTokenAuth` API

## Configuration Requirements

### 1. Create OAuth2 Credential Provider
```bash
aws bedrock-agentcore-control create-oauth2-credential-provider \
  --name "MyProvider" \
  --credential-provider-vendor "GoogleOauth2" \
  --oauth2-provider-config-input '{
    "googleOauth2ProviderConfig": {
      "clientId": "...",
      "clientSecret": "..."
    }
  }'

# Response includes callbackUrl - register this with OAuth provider
```

### 2. Configure Workload Identity
```bash
aws bedrock-agentcore-control update-workload-identity \
  --name <workload-identity-name> \
  --allowed-resource-oauth2-return-urls https://your-callback-server.com/callback
```

### 3. Implement Callback Server
```python
from starlette.requests import Request
from starlette.responses import JSONResponse
import boto3

def handle_oauth_callback(request: Request) -> JSONResponse:
    # 1. Extract session_id from query params
    session_id = request.query_params.get("session_id")
    if not session_id:
        return JSONResponse(status_code=400, content={"error": "missing session_id"})
    
    # 2. Verify user session (from cookies/headers)
    user_id = get_user_id_from_session(request)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "invalid session"})
    
    # 3. Complete the token auth flow
    client = boto3.client("bedrock-agentcore", region_name="us-east-1")
    client.complete_resource_token_auth(
        sessionUri=session_id,
        userIdentifier={"userId": user_id}
    )
    
    return JSONResponse(content={"status": "success"})
```

### 4. Request Token in Agent Code
```python
from bedrock_agentcore.identity import requires_access_token

@requires_access_token(
    provider_name="MyProvider",
    scopes=["openid", "email"],
    auth_flow="USER_FEDERATION",
    callback_url="https://your-callback-server.com/callback",  # Must match workload identity
    on_auth_url=lambda url: print(f"Please authorize: {url}"),
)
async def call_external_api(*, access_token: str):
    # Token is automatically injected after user consent + callback completion
    pass
```

**Note**: The `callback_url` must match the URL registered in workload identity via `UpdateWorkloadIdentity`.

## Session Binding Security

`CompleteResourceTokenAuth` prevents authorization URL forwarding attacks:

1. User A requests token → gets authorizationUrl with sessionUri
2. User A (accidentally or maliciously) sends URL to User B
3. User B completes consent
4. Callback server receives redirect, but verifies **current browser session**
5. If session belongs to User B (not User A), callback server rejects or logs attempt

**Critical**: Always verify user identity from active browser session (cookies), not from URL parameters.

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `redirect_mismatch` | Callback URL not registered | Register AgentCore callback URL with OAuth provider |
| Token never available | `CompleteResourceTokenAuth` not called | Implement callback server correctly |
| Wrong user gets token | Session not verified | Verify user from browser cookies, not URL |
| `ValidationException` | Callback URL not in workload identity | Call `UpdateWorkloadIdentity` with callback URL |

## Necessary Changes

Based on the current implementation in `construct.py` and `oauth_gateway_infra.yaml`:

### ✅ Already Implemented
1. **Workload Identity Configuration** - `create_gateway()` calls `update_workload_identity()` with CloudFront callback URL
2. **Callback Server** - Lambda function calls `complete_resource_token_auth()` with session binding
3. **Outbound OAuth Provider** - Google provider created with `callbackUrl` returned
4. **Gateway Target** - Uses `defaultReturnUrl` pointing to CloudFront callback
5. **Cognito CallbackURLs** - Updated to use AgentCore Identity callback URL (with UUID)

### ⚠️ Manual Step: Google OAuth App Registration
Register **both** callback URLs in Google Cloud Console:

1. **Inbound (Cognito federation)**: 
   - `https://{cognito-domain}.auth.{region}.amazoncognito.com/oauth2/idpresponse`
   
2. **Outbound (AgentCore Token Vault)**:
   - `https://bedrock-agentcore.{region}.amazonaws.com/identities/oauth2/callback/{uuid}`
   - (Printed by `construct.py` as `outbound_callback_url`)

### Summary of Callback URL Flow

| Flow | OAuth Provider Callback | Final User Redirect |
|------|------------------------|---------------------|
| Inbound (user auth) | Cognito `/oauth2/idpresponse` | N/A (handled by Cognito) |
| Outbound (API access) | AgentCore `/callback/{uuid}` | CloudFront (your callback server) |

## References

- [OAuth 2.0 Authorization URL Session Binding](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/oauth2-authorization-url-session-binding.html)
- [CreateOauth2CredentialProvider API](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateOauth2CredentialProvider.html)
- [CompleteResourceTokenAuth API](https://docs.aws.amazon.com/bedrock-agentcore/latest/APIReference/API_CompleteResourceTokenAuth.html)

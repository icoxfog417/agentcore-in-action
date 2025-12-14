# MCP Server with OAuth Gateway

## Overview

This example demonstrates an **MCP server implementation that connects to AgentCore Gateway** with both **inbound OAuth authentication** (user identity) and **outbound OAuth authorization** (API access).

The MCP server exposes YouTube API tools to clients, while AgentCore Gateway handles:
- **Inbound Auth**: Validates user identity via Cognito JWT (federated with Google)
- **Outbound Auth**: Retrieves user-specific Google API tokens from Token Vault

**Key Concept: Single Google Identity, Dual Purpose**
- **Inbound**: User signs in with Google via Cognito → identifies WHO the user is
- **Outbound**: Same user's Google token from Token Vault → authorizes WHAT they can access

**Use Case**: Building MCP servers that securely access third-party APIs on behalf of authenticated users, with seamless single sign-on using Google for both authentication and authorization.

## Architecture

```mermaid
flowchart LR
    subgraph Client
        U[User/MCP Client]
    end

    subgraph Cognito[Amazon Cognito]
        CUP[User Pool]
        GF[Google Federation]
    end

    subgraph Gateway[AgentCore Gateway]
        IN[Inbound Auth<br/>CUSTOM_JWT]
        INT[Interceptor<br/>Lambda]
        OUT[Outbound Call]
    end

    subgraph Identity[AgentCore Identity]
        TV[Token Vault]
        OP[OAuth Provider<br/>Google]
    end

    subgraph External
        YT[YouTube API]
    end

    U -->|1. Sign in| CUP
    CUP -->|2. Federate| GF
    GF -->|3. JWT with<br/>Google identity| U
    U -->|4. MCP call + JWT| IN
    IN -->|5. Validate JWT| IN
    IN -->|6. Pass claims| INT
    INT -->|7. Get token<br/>for user| TV
    TV -->|8. Google token| INT
    INT -->|9. Inject header| OUT
    OUT -->|10. API call| YT
    YT -->|11. Response| U
```

## Prerequisites

- AWS account with AgentCore access
- Google OAuth App credentials (https://console.cloud.google.com/apis/credentials)
- Python 3.10+
- AWS credentials configured
- `uv` for dependency management

## Quick Start

```bash
cd mcp-server-with-oauth-gateway
cp .env.example .env
# Edit .env with GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
uv run python construct.py
# Register callback URLs in Google OAuth App
uv run python main.py
```

## Demonstration Flow

```mermaid
sequenceDiagram
    participant User
    participant MCP as MCP Server
    participant Cognito
    participant Google as Google OAuth
    participant Gateway
    participant Interceptor as Interceptor Lambda
    participant Vault as Token Vault
    participant API as YouTube API

    Note over User,API: Step 1: Unauthenticated Access → Inbound Auth
    User->>MCP: MCP request (no JWT)
    MCP->>MCP: No valid JWT detected
    MCP-->>User: Redirect to Cognito Hosted UI
    User->>Cognito: Sign in with Google
    Cognito->>Google: OAuth redirect
    Google-->>Cognito: Auth code + user info
    Cognito-->>User: Redirect with Cognito JWT

    Note over User,API: Step 2: First API Call → Outbound Auth (3LO)
    User->>MCP: MCP request + Cognito JWT
    MCP->>Gateway: API call + Cognito JWT
    Gateway->>Gateway: Validate JWT ✓
    Gateway->>Interceptor: Request + JWT claims
    Interceptor->>Vault: Get YouTube API token for user X
    Vault-->>Interceptor: No token found (authorizationUrl)
    Interceptor-->>Gateway: transformedGatewayResponse (401)
    Gateway-->>MCP: Return Google auth URL
    MCP-->>User: Authorization required + auth URL

    User->>Google: Authorize API scopes (youtube.readonly)
    Google-->>Vault: Store API token for user X
    Vault-->>User: Redirect to success page

    Note over User,API: Step 3: Subsequent Calls → Token Retrieved from Vault
    User->>MCP: MCP request (tools/call)
    MCP->>Gateway: API call + Cognito JWT
    Gateway->>Interceptor: Request + JWT claims
    Interceptor->>Vault: Get YouTube API token for user X
    Vault-->>Interceptor: Google API token ✓
    Interceptor-->>Gateway: transformedGatewayRequest (inject header)
    Gateway->>API: GET /youtube/v3/channels
    API-->>Gateway: Channel data
    Gateway-->>MCP: Response
    MCP-->>User: Tool result
```

## Construction Flow

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant Script as construct.py
    participant S3 as S3 + CloudFront
    participant Cognito as Amazon Cognito
    participant Lambda as AWS Lambda
    participant AC as AgentCore

    Dev->>Script: uv run python construct.py

    Note over Script,Lambda: CloudFormation Stack (oauth_gateway_infra.yaml)
    
    Note over Script,S3: Step 1: Static Callback Page
    Script->>S3: Create bucket + distribution
    Script->>S3: Upload callback_inbound.html, callback_outbound.html
    S3-->>Script: callback_urls

    Note over Script,Cognito: Step 2: Inbound Auth (Cognito + Google)
    Script->>Cognito: Create User Pool + Google IdP + App Client
    Cognito-->>Script: client_id, discovery_url

    Note over Script,Lambda: Step 3: Interceptor Lambda
    Script->>Lambda: Create function + IAM role
    Script->>Lambda: Deploy interceptor.py code
    Lambda-->>Script: interceptor_arn

    Note over Script,AC: Step 4: AgentCore Resources (boto3)
    Script->>AC: Create OAuth Provider (Google)
    AC-->>Script: provider_arn, google_callback_url
    Script->>Lambda: Set OAUTH_PROVIDER_ARN env var
    Note right of Lambda: Interceptor needs provider_arn<br/>to call Token Vault API:<br/>get_resource_oauth2_token(<br/>  oauth2CredentialProviderArn=...,<br/>  userIdentifier=...)
    Script->>AC: Create Gateway (CUSTOM_JWT + Interceptor)
    AC-->>Script: gateway_id
    Script->>AC: Create Gateway Target (YouTube API)
    AC-->>Script: target_id

    Script->>Dev: Save config.json
    Script->>Dev: Display callback URLs to register
```

## Specifications

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Cognito** | Federate with Google, issue JWT with user identity |
| **Gateway (Inbound)** | Validate Cognito JWT, extract user claims |
| **Interceptor Lambda** | Map user identity → Google API token |
| **Token Vault** | Store Google API tokens per user |
| **Gateway (Outbound)** | Call YouTube API with injected token |

### Interceptor Lambda

**Input (from Gateway with `passRequestHeaders: true`):**
```json
{
  "interceptorInputVersion": "1.0",
  "mcp": {
    "rawGatewayRequest": {
      "body": "<raw_request_body>"
    },
    "gatewayRequest": {
      "path": "/mcp",
      "httpMethod": "POST",
      "headers": {
        "Authorization": "Bearer <cognito_jwt_token>",
        "Content-Type": "application/json"
      },
      "body": {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "...", "arguments": {}}
      }
    }
  }
}
```

**Logic:**
1. Extract JWT from `mcp.gatewayRequest.headers.Authorization`
2. Decode JWT to get claims (including `identities` for federated Google user)
3. Extract Google user ID from decoded `identities` claim
4. Call `GetResourceOauth2Token` with user ID
5. If token exists → inject into `Authorization` header via `transformedGatewayRequest`
6. If no token → return OAuth elicitation response via `transformedGatewayResponse`

**Output (token exists - inject for outbound call):**
```json
{
  "interceptorOutputVersion": "1.0",
  "mcp": {
    "transformedGatewayRequest": {
      "headers": {
        "Authorization": "Bearer <google_api_token>"
      },
      "body": {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "...", "arguments": {}}
      }
    }
  }
}
```

**Output (no token - trigger OAuth elicitation):**
```json
{
  "interceptorOutputVersion": "1.0",
  "mcp": {
    "transformedGatewayResponse": {
      "statusCode": 401,
      "headers": {
        "Content-Type": "application/json"
      },
      "body": {
        "error": "authorization_required",
        "authorizationUrl": "<google_oauth_authorization_url>",
        "message": "User must authorize YouTube API access"
      }
    }
  }
}
```

### Gateway Configuration

```python
# Inbound: Cognito JWT validation
authorizerType="CUSTOM_JWT"
authorizerConfiguration={
    "customJWTAuthorizer": {
        "discoveryUrl": cognito_discovery_url,
        "allowedClients": [cognito_client_id]
    }
}

# Interceptor: Bridge identity to token
interceptorConfigurations=[{
    "interceptor": {"lambda": {"arn": interceptor_arn}},
    "interceptionPoints": ["REQUEST"],
    "inputConfiguration": {"passRequestHeaders": True}
}]
```

## Security Considerations

- **Token Isolation**: Each user's Google token stored separately in Token Vault
- **Identity Binding**: Token retrieval requires matching user ID from JWT
- **Least Privilege**: Interceptor only has `GetResourceOauth2Token` permission
- **No Token Exposure**: Google tokens never sent to client

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "JWT validation failed" | Check Cognito discovery URL and client ID match Gateway config |
| "No Google token found" | User needs to complete 3LO authorization via authorizationUrl |
| "Interceptor timeout" | Increase Lambda timeout, check VPC/network access to AgentCore |
| "Invalid redirect_uri" | Ensure callback URLs are registered in both Google OAuth App and Cognito |
| "Access denied on GetResourceOauth2Token" | Verify Lambda IAM role has `bedrock-agentcore:GetResourceOauth2Token` permission |

## References

### AgentCore Documentation
- [AgentCore Gateway Overview](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-gateway.html)
- [Gateway Interceptors](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-gateway-interceptors.html)
- [AgentCore Identity - Token Vault](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-identity.html)
- [OAuth 2.0 Credential Providers](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-identity-oauth.html)

### Amazon Cognito
- [User Pool Federation with Social IdPs](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-identity-federation.html)
- [Adding Social Identity Providers](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-social-idp.html)
- [Hosted UI Reference](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-app-integration.html)

### Google OAuth
- [Creating OAuth 2.0 Client IDs](https://developers.google.com/identity/protocols/oauth2/web-server#creatingcred)
- [OAuth 2.0 Scopes for Google APIs](https://developers.google.com/identity/protocols/oauth2/scopes)
- [YouTube Data API](https://developers.google.com/youtube/v3)

### MCP (Model Context Protocol)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Authentication](https://spec.modelcontextprotocol.io/specification/architecture/#authentication)

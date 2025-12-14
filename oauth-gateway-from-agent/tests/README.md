# Test Suite for Secure MCP with OAuth Gateway

## Overview
- Total: 9 | Passing: 9 | Failing: 0

## Categories

### Configuration
- test_load_env_config_with_values
  - Spec: README.md > Quick Start > Environment Setup
  - Purpose: Verify required env vars are recognized
  - Status: ✅

- test_env_example_exists
  - Spec: README.md > Quick Start > Environment Setup
  - Purpose: Verify .env.example exists with required variables
  - Status: ✅

### Interceptor Lambda
- test_decode_valid_jwt
  - Spec: README.md > Specifications > Interceptor Lambda > Logic
  - Purpose: Decode JWT payload correctly
  - Status: ✅

- test_decode_invalid_jwt_format
  - Spec: README.md > Specifications > Interceptor Lambda > Logic
  - Purpose: Reject malformed JWT tokens
  - Status: ✅

- test_extract_from_identities
  - Spec: README.md > Specifications > Interceptor Lambda > Logic
  - Purpose: Extract Google user ID from JWT sub claim
  - Status: ✅

- test_no_identities_claim
  - Spec: README.md > Specifications > Interceptor Lambda > Logic
  - Purpose: Handle missing identities claim gracefully
  - Status: ✅

- test_no_google_provider
  - Spec: README.md > Specifications > Interceptor Lambda > Logic
  - Purpose: Handle non-Google federated users
  - Status: ✅

- test_inject_token_response
  - Spec: README.md > Specifications > Interceptor Lambda > Output (token exists)
  - Purpose: Return transformedGatewayRequest with injected Authorization header
  - Status: ✅

- test_auth_required_response
  - Spec: README.md > Specifications > Interceptor Lambda > Output (no token)
  - Purpose: Return transformedGatewayResponse with 401 and authorizationUrl
  - Status: ✅

## Todo (Priority)
- [ ] test_gateway_jwt_validation (Medium) - Gateway validates Google OIDC JWT
- [ ] test_outbound_token_retrieval (Medium) - Interceptor calls GetResourceOauth2Token

## Run
```bash
uv run pytest tests/ -v
uv run pytest tests/ -v --lf
```

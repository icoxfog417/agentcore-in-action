# Test Suite for Say Hello to Authorized Customer

## Overview
- Total: 15 | Passing: 15 | Failing: 0

## Categories

### Configuration
- `test_load_env_variables`
  - Spec: README.md > Specifications > Configuration Template
  - Purpose: Verify all required environment variables load correctly
  - Status: ✅

- `test_missing_required_env_variables`
  - Spec: README.md > Security > Credential Management
  - Purpose: Graceful handling when required env vars are missing
  - Status: ✅

### OAuth2 Callback Server
- `test_callback_server_initialization`
  - Spec: README.md > Specifications > OAuth2 Callback Server
  - Purpose: Server initializes with correct region and endpoints
  - Status: ✅

- `test_get_oauth2_callback_base_url_localhost`
  - Spec: README.md > Specifications > OAuth2 Callback Server > get_oauth2_callback_base_url
  - Purpose: Returns correct localhost URL in local environment
  - Status: ✅

- `test_store_user_token_identifier`
  - Spec: README.md > Specifications > OAuth2 Callback Server > store_token_in_oauth2_callback_server
  - Purpose: User token identifier is stored correctly
  - Status: ✅

- `test_ping_endpoint`
  - Spec: README.md > Specifications > OAuth2 Callback Server > Endpoints
  - Purpose: Health check endpoint returns success
  - Status: ✅

### Gateway Configuration
- `test_create_gateway_with_oauth`
  - Spec: README.md > Specifications > Gateway Configuration > create_gateway
  - Purpose: Gateway is created with correct OAuth configuration
  - Status: ✅

- `test_gateway_oauth_scopes`
  - Spec: README.md > Specifications > Gateway Configuration > Gateway Configuration
  - Purpose: Gateway has correct OAuth scopes (profile, openid)
  - Status: ✅

- `test_delete_gateway`
  - Spec: README.md > Specifications > Gateway Configuration > delete_gateway
  - Purpose: Gateway cleanup works correctly
  - Status: ✅

### Identity Configuration
- `test_create_workload_identity`
  - Spec: README.md > Specifications > Identity Configuration > create_workload_identity
  - Purpose: Workload identity is created with callback URL
  - Status: ✅

- `test_get_user_token_identifier_from_jwt`
  - Spec: README.md > Specifications > Identity Configuration > get_user_token_identifier
  - Purpose: User identifier is extracted from JWT sub claim
  - Status: ✅

- `test_delete_workload_identity`
  - Spec: README.md > Specifications > Identity Configuration > delete_workload_identity
  - Purpose: Identity cleanup works correctly
  - Status: ✅

### Agent Implementation
- `test_create_agent_with_gateway`
  - Spec: README.md > Specifications > Agent Implementation > create_agent
  - Purpose: Agent is created with Gateway tools
  - Status: ✅

- `test_detect_elicitation_response`
  - Spec: README.md > Specifications > Agent Implementation > Behavior
  - Purpose: Agent detects elicitation URL from Gateway response
  - Status: ✅

- `test_greet_user_with_profile_name`
  - Spec: README.md > Specifications > Agent Implementation > greet_user
  - Purpose: Agent formats greeting with user's profile name
  - Status: ✅

## Todo (Priority)

All tests are passing! ✅

## Run

Run all tests:
```bash
uv run pytest tests/ -v
```

Run failed tests only:
```bash
uv run pytest tests/ -v --lf
```

Run specific category:
```bash
uv run pytest tests/test_main.py::TestConfiguration -v
```

Run with debug logging:
```bash
LOG_LEVEL=DEBUG uv run pytest tests/ -v -s
```

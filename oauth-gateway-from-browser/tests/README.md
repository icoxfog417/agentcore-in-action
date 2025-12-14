# Test Suite for Say Hello to Authorized Customer

## Overview
- Total: 14 | Passing: 14 | Failing: 0

## Categories

### Configuration (Spec: README.md > Configuration Template)
- test_load_env_variables
  - Spec: README.md > Configuration Template > Required Variables
  - Purpose: Validate .env loading and required variables
  - Status: ✅

### Construction (Spec: README.md > Construction Flow)
- test_save_config
  - Spec: README.md > Specifications > Section 6 > Output
  - Purpose: Save config.json with all resource IDs
  - Status: ✅

### Agent (Spec: README.md > Specifications > Section 1)
- test_call_gateway_tool
  - Spec: README.md > Specifications > Section 1 > Key Functions
  - Purpose: Make raw JSON-RPC call to Gateway
  - Status: ✅

- test_detect_oauth_elicitation
  - Spec: README.md > Specifications > Section 1 > OAuth Elicitation Detection
  - Purpose: Detect error code -32042 and extract elicitation URL
  - Status: ✅

- test_greet_user
  - Spec: README.md > Specifications > Section 1 > Key Functions
  - Purpose: Execute greeting flow with YouTube data
  - Status: ✅

### OAuth2 Callback Server (Spec: README.md > Specifications > Section 2)
- test_server_initialization
  - Spec: README.md > Specifications > Section 2 > Key Functions
  - Purpose: Initialize FastAPI server with config
  - Status: ✅

- test_cognito_callback_handler
  - Spec: README.md > Specifications > Section 2 > Key Functions
  - Purpose: Exchange auth code for access token
  - Status: ✅

- test_youtube_callback_handler
  - Spec: README.md > Specifications > Section 2 > Key Functions
  - Purpose: Complete OAuth session binding and retry Gateway call
  - Status: ✅

### Main Entry Point (Spec: README.md > Specifications > Section 7)
- test_load_config
  - Spec: README.md > Specifications > Section 7 > Prerequisites
  - Purpose: Load config.json
  - Status: ✅

- test_signup_mode
  - Spec: README.md > Specifications > Section 7 > Command-line Arguments
  - Purpose: Handle --signup flag with username/password
  - Status: ✅

### Integration Tests (Spec: README.md > Testing)
- test_oauth_flow_info
  - Spec: README.md > Testing > OAuth Flow
  - Purpose: Display OAuth flow information for manual testing
  - Status: ✅

- test_gateway_with_oauth_token
  - Spec: README.md > Testing > Gateway Authorization
  - Purpose: Test gateway without scope requirement
  - Status: ✅

- test_gateway_with_oauth_token_with_scope
  - Spec: README.md > Testing > Gateway Authorization
  - Purpose: Test gateway with scope requirement
  - Status: ✅

- test_gateway_with_automated_oauth
  - Spec: README.md > Testing > Automated OAuth
  - Purpose: Test complete automated OAuth flow with browser
  - Status: ✅

## Key Learnings
- OAuth elicitation uses error code **-32042** (not -32001)
- `_meta` field not required for OAuth flow
- Session binding uses `complete_resource_token_auth(sessionUri, userIdentifier)`
- `userIdentifier` format: `{"userToken": cognito_access_token}`

## Run
```bash
uv run pytest tests/ -v
uv run pytest tests/ -v --lf  # Run last failed
```



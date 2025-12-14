# Tests for MCP Server with OAuth Gateway

## Overview

This directory contains tests for the MCP Server with OAuth Gateway example.

## Test Structure

### Unit Tests
- `test_server.py`: Tests for MCP server tool implementations
- `test_oauth_handler.py`: Tests for OAuth callback handler
- `test_construct.py`: Tests for infrastructure construction

### Integration Tests
- Tests requiring live AWS resources
- OAuth flow validation
- Gateway integration tests

## Running Tests

```bash
# Install dev dependencies
uv sync --all-extras

# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_server.py

# Run with coverage
uv run pytest --cov=mcp_server_with_oauth_gateway
```

## Test Requirements

- Mock AWS services for unit tests
- Live AWS credentials for integration tests (optional)
- GitHub OAuth App credentials for OAuth tests (optional)

## Mocking Strategy

Unit tests use `moto` to mock AWS services:
- `bedrock-agentcore-control` for resource creation
- `bedrock-agentcore` for Identity operations
- IAM for role management

Integration tests can optionally use real AWS resources if credentials are provided.

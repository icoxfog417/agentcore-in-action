# Design Guidelines

This document specifies what we will create: the concrete deliverables, structures, and checklists for examples under root directory. For the rationale, principles, and workflow (why and how), see `principle.md`.

## Scope of This Document
- What to deliver (files, structure, configs)
- How deliverables are organized (directories, interfaces)
- Acceptance criteria and checklists
- Test documentation layout aligned to specifications

## Directory Structure

Each example should be self-contained within its own directory:

```
example_name/
├── README.md          # Comprehensive documentation
├── main.py            # Entry point script
├── .env.example       # Environment variable template
├── .progress          # Development iteration log
├── tests/             # Test cases based on specifications
│   ├── README.md      # Test structure overview (implementation todo list)
│   └── test_main.py
└── example_name/      # Core implementation (deployable if needed for AgentCore)
```

All dependencies should be integrated to `pyproject.toml`.

## Entry Point Requirements

### Executable Python Program
- **Command**: `cd example_directory && uv run python main.py`
- Must work immediately after cloning the repository
- Use `uv` for dependency management to ensure reproducibility
- Include clear error messages for missing dependencies or configuration

### Environment Setup
- Provide `.env.example` with all required environment variables
- Document AWS credentials requirements
- Include region configuration instructions

## README.md Structure

Each example's README must include:

### 1. Overview
- Brief description of what the example demonstrates
- Use case and practical applications
- Prerequisites (AWS account, permissions, etc.)

### 2. Quick Start
```markdown
## Quick Start

1. Navigate to the example directory: `cd example_name`
2. Copy environment variables: `cp .env.example .env`
3. Configure your credentials in `.env`
4. Run the example: `uv run python main.py`
```

### 3. Architecture
- Include a Mermaid sequence diagram showing the interaction flow
- Document all system components and their interactions

### 4. Specifications
- Document each file's purpose and key functions
- Explain configuration options
- Describe customization points

### 5. Security Considerations for Production
Must address:
- **Credential Management**: Never hardcode credentials; use AWS Secrets Manager or environment variables
- **Input Validation**: Sanitize all user inputs
- **Rate Limiting**: Implement throttling for API calls
- **Error Handling**: Avoid exposing sensitive information in error messages
- **Logging**: Log security events without exposing credentials
- **IAM Permissions**: Follow principle of least privilege
- **Network Security**: Use VPC endpoints where applicable

### 6. Troubleshooting
- Common issues and solutions
- Debug logging instructions
- Links to relevant AWS documentation

## Development Deliverables
- `README.md` (specification-first)
- `tests/README.md` (test suite overview; must correspond to `README.md` Specifications)
- `tests/*.py` (executable tests per spec)
- `main.py` and modules (`example_name/`)
- `.env.example` (configuration template)
- `.progress` (iteration log; see format below)

## Progress Logging (Format Only)
Each iteration records: Specification → Implementation → Test → Evaluation.

```markdown
## Iteration N: [YYYY-MM-DD]
### Specification
- Goal: ...
- Key decisions: ...

### Implementation
- Code changes: file + brief change

### Test
- Command: uv run pytest tests/ -v
- Result: X/Y passing

### Evaluation
- What worked / challenges
- Next iteration focus
```

## tests/README.md Structure (Aligned to Main README.md)
The `tests/README.md` must maintain direct correspondence with the Specifications section of the main `README.md`.

```markdown
# Test Suite for [Example Name]

## Overview
- Total: N | Passing: X | Failing: Y

## Categories
### Configuration
- test_load_config_success
  - Spec: README.md > Specifications > Configuration
  - Purpose: Env vars load correctly
  - Status: ✅

- test_missing_credentials
  - Spec: README.md > Security > Credential Management
  - Purpose: Graceful handling when creds missing
  - Status: ❌ (TODO)

### [Other Categories]
...

## Todo (Priority)
- [ ] test_missing_credentials (High)
- [ ] test_invalid_input (High)
- [ ] test_rate_limiting (Medium)

## Run
uv run pytest tests/ -v
uv run pytest tests/ -v --lf
```

## Testing and Validation Checklist

Before submitting an example:
- [ ] Specifications in README.md are complete and clear
- [ ] tests/README.md aligns with README.md specifications
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] Linting clean: `uv run ruff check`
- [ ] Manual run successful: `uv run python main.py`
- [ ] .progress file documents all iterations
- [ ] Fresh environment tested (no cached dependencies)
- [ ] Documentation links validated
- [ ] Mermaid diagrams render correctly
- [ ] Security considerations documented

## Reference Examples

See `.example/sample-amazon-bedrock-agentcore-onboarding` for implementations:
- `01_code_interpreter/`: Basic code execution example
- `02_agent_with_tools/`: Tool integration patterns
- `03_multi_agent/`: Complex multi-agent workflows

Each demonstrates proper structure, documentation, and security practices.

## AgentCore API Guidelines

### Boto3 Client Selection
AgentCore uses two separate boto3 clients for different operations:

| Client | Use For |
|--------|---------|
| `bedrock-agentcore-control` | Control plane: create/delete/get gateways, targets, OAuth providers, workload identities |
| `bedrock-agentcore` | Data plane: runtime operations, invoking agents |

**Common mistake**: Using `bedrock-agentcore` for control plane operations causes API errors.

### Gateway Target Configuration
When creating gateway targets with OAuth credential providers:

```python
# Required fields for AUTHORIZATION_CODE grant type
credentialProviderConfigurations=[{
    "credentialProviderType": "OAUTH",
    "credentialProvider": {
        "oauthCredentialProvider": {
            "providerArn": provider_arn,
            "grantType": "AUTHORIZATION_CODE",
            "defaultReturnUrl": callback_url,  # REQUIRED - often missed
            "scopes": ["..."]
        }
    }
}]
```

### Gateway Configuration
Include protocol configuration and exception level for better debugging:

```python
client.create_gateway(
    name=gateway_name,
    protocolType="MCP",
    protocolConfiguration={
        "mcp": {
            "supportedVersions": ["2025-11-25"],
            "searchType": "SEMANTIC"
        }
    },
    exceptionLevel="DEBUG",  # Helps with troubleshooting
    # ... other params
)
```

### Response Field Names
OAuth provider responses use different field names depending on the operation:
- `create_oauth2_credential_provider`: returns `credentialProviderArn`
- `get_oauth2_credential_provider`: may return `oauth2CredentialProviderArn`

Handle both cases when extracting ARNs from responses.
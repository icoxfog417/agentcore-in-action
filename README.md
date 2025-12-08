# 🚀 AgentCore in Action

Production-ready, script-based examples for Amazon Bedrock AgentCore integration.

## 🎯 Mission

Bridge the gap between exploration and integration. While Jupyter Notebook examples provide step-by-step understanding of new features, they can be challenging to integrate into existing applications. These examples provide working, runnable scripts that developers can adapt for production use.

## 💡 Principles

- **Clarity**: Each example is self-contained with comprehensive documentation
- **Reproducibility**: Use `uv` for dependency management; examples work immediately after cloning
- **Security**: Production-aware security considerations documented for every example
- **Specification-first**: Design from specifications, implement to satisfy tests
- **Transparency**: Document capabilities, limitations, and known issues

## 📚 Examples

| Example | Description | AgentCore Features |
|---------|-------------|-------------------|
| [say-hello-to-authorized-customer](./say-hello-to-authorized-customer/) | Personalized greetings using user's YouTube data via OAuth 2.0 | Identity, Gateway, OAuth 2.0 Authorization Code Grant |

See each example's README.md for detailed documentation, architecture diagrams, and security considerations.

## ⚡ Getting Started

Each example follows the same structure:

```bash
uv sync
cd example_name
cp .env.example .env
# Configure credentials in .env
uv run python main.py
```

## 📁 Repository Structure

```
example_name/
├── README.md          # Comprehensive documentation
├── main.py            # Entry point script
├── .env.example       # Environment variable template
├── .progress          # Development iteration log
├── tests/             # Test cases based on specifications
│   ├── README.md      # Test structure overview
│   └── test_main.py
└── example_name/      # Core implementation
```

## ✅ Requirements

- Python 3.10+
- AWS account with AgentCore access
- AWS credentials configured
- `uv` for dependency management

## 📖 Reference Materials

- `.reference/amazon-bedrock-agentcore-samples`: Jupyter Notebook examples for step-by-step learning
- `.example/sample-amazon-bedrock-agentcore-onboarding`: Reference implementations

## 🤝 Contributing

Examples follow a specification-first workflow:

1. **Specification**: Define behavior in `README.md` and `tests/README.md`
2. **Test Design**: Write executable tests reflecting specifications
3. **Implementation**: Implement minimal code to satisfy tests
4. **Validation**: Complete security checks, documentation, and troubleshooting

See `.kiro/steering/design.md` and `.kiro/steering/principle.md` for detailed guidelines.

## 🔒 Security

All examples include production security considerations:
- Credential management (AWS Secrets Manager, environment variables)
- Input validation and sanitization
- Rate limiting and throttling
- Error handling without exposing sensitive information
- IAM least privilege principles
- Network security best practices

## 📄 License

This repository is provided as-is for educational and reference purposes.

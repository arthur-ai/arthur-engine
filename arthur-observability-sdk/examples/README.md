# Arthur Observability SDK Examples

This directory contains example applications demonstrating how to use the Arthur Observability SDK with various frameworks and use cases.

## Available Examples

### [LangChain Timezone Agent](langchain-timezone-agent/)

A complete tutorial showing how to build a LangChain agent with OpenInference tracing using the Arthur Observability SDK. This example demonstrates:

- Setting up the unified `ArthurClient` for API access and automatic telemetry
- Auto-instrumenting LangChain with a single function call
- Using session and user context for tracking conversations
- Building custom tools that work with the agent
- Monitoring agent interactions in Arthur

**Key Features:**
- ✅ Automatic task creation from task names
- ✅ Full conversation tracing
- ✅ Tool usage monitoring
- ✅ Session and user tracking
- ✅ Real-time span export to Arthur

[View the LangChain Timezone Agent example →](langchain-timezone-agent/)

## Running Examples

Each example is self-contained with its own README, dependencies, and configuration. To run an example:

1. Navigate to the example directory
2. Follow the setup instructions in the example's README
3. Configure your environment variables
4. Run the example application

## Prerequisites

All examples require:
- Python 3.8 or higher
- An Arthur account with API access
- The Arthur Observability SDK installed

## Installing the SDK for Examples

Install the SDK with the appropriate framework support for your example:

```bash
# For LangChain examples
pip install -e "../../[langchain]"

# Or install all frameworks
pip install -e "../../[all]"
```

## Contributing Examples

We welcome contributions! If you've built something interesting with the Arthur Observability SDK, consider contributing an example:

1. Create a new directory under `examples/`
2. Include a comprehensive README with setup instructions
3. Provide an `env.example` file for configuration
4. Keep dependencies minimal and well-documented
5. Ensure the code follows best practices and is well-commented

## Getting Help

- Check the [main SDK README](../README.md) for installation and core concepts
- Visit [Arthur Documentation](https://docs.arthur.ai/) for platform guides
- Join our [Discord community](https://discord.gg/tdfUAtaVHz) for support
- Open an [issue](https://github.com/arthur-ai/arthur-engine/issues) for bugs or feature requests

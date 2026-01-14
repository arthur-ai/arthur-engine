# Arthur Observability SDK

> ⚠️ **Alpha Release**: This SDK is currently in alpha. PyPI packages will be released soon. For now, please install directly from the monorepo.

The official Python SDK for Arthur platform APIs and [OpenInference](https://github.com/Arize-ai/openinference) tracing. This SDK provides a unified interface for both Arthur's REST API and comprehensive observability, enabling you to manage prompts, run experiments, and monitor your LLM-powered applications in production.

This SDK is part of the [Arthur Engine](https://github.com/arthur-ai/arthur-engine) monorepo.

## Features

- **Unified Client**: Single initialization for both API access and telemetry
- **Prompt Management API**: Fetch, render, and manage prompts programmatically
- **Automatic Instrumentation**: Built-in span creation for prompt fetching with OpenInference semantic conventions
- **Multi-Framework Support**: Auto-instrumentation for OpenAI, LangChain, Anthropic, LlamaIndex, and more
- **Session & User Tracking**: Track conversations and user interactions across your application
- **Lightweight & Flexible**: Only install dependencies for the frameworks you actually use
- **Production-Ready**: Battle-tested OpenTelemetry foundation with configurable span processors

## Installation

### Prerequisites

- Python 3.8 or higher
- Git

### Install from Monorepo

Since this SDK is currently in alpha and not yet published to PyPI, you need to install it directly from the Arthur Engine monorepo:

#### Core SDK (required)

```bash
# Clone the monorepo
git clone https://github.com/arthur-ai/arthur-engine.git
cd arthur-engine/arthur-sdk

# Install the core SDK
pip install -e .
```

#### With Framework Support

Install with optional dependencies for the frameworks you use:

```bash
# After navigating to arthur-engine/arthur-sdk, install with extras

# OpenAI
pip install -e ".[openai]"

# LangChain
pip install -e ".[langchain]"

# Anthropic
pip install -e ".[anthropic]"

# LlamaIndex
pip install -e ".[llama-index]"

# Multiple frameworks
pip install -e ".[openai,langchain]"

# All supported frameworks
pip install -e ".[all]"
```

#### Alternative: Install directly via pip from GitHub

You can also install directly from GitHub without cloning:

```bash
# Core SDK
pip install "git+https://github.com/arthur-ai/arthur-engine.git#subdirectory=arthur-sdk"

# With framework support
pip install "arthur-observability-sdk[langchain] @ git+https://github.com/arthur-ai/arthur-engine.git#subdirectory=arthur-sdk"
```

### Supported Frameworks

- OpenAI (`[openai]`)
- LangChain (`[langchain]`)
- Anthropic (`[anthropic]`)
- LlamaIndex (`[llama-index]`)
- AWS Bedrock (`[bedrock]`)
- Google VertexAI (`[vertexai]`)
- MistralAI (`[mistralai]`)
- Groq (`[groq]`)

## Quick Start

Here's a complete example using the unified ArthurClient:

```python
import os
from uuid import UUID
from arthur_observability_sdk import ArthurClient, context, instrument_openai

# 1. Initialize Arthur client (handles both API and telemetry)
arthur = ArthurClient(
    task_id=os.getenv("ARTHUR_TASK_ID"),
    api_key=os.getenv("ARTHUR_API_KEY"),
    base_url=os.getenv("ARTHUR_BASE_URL", "https://app.arthur.ai"),
    service_name="my-recommendation-service"
)

# 2. Fetch and render a prompt (automatically creates a span)
prompt = arthur.client.prompts.render_saved_agentic_prompt(
    task_id=UUID(os.getenv("ARTHUR_TASK_ID")),
    prompt_name="customer_email_template",
    prompt_version="latest",
    variables={
        "customer_name": "Alice",
        "order_id": "12345"
    }
)

print(f"Rendered prompt: {prompt}")

# 3. Auto-instrument your framework (optional)
instrument_openai()

# 4. Add context for session/user tracking
with context(session_id="session-123", user_id="user-456"):
    # Your application code here
    import openai
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello!"}]
    )

# 5. Cleanup when done
arthur.shutdown()
```

## Core Concepts

### ArthurClient

The `ArthurClient` is the main entry point for the SDK. It provides:
- Access to Arthur platform APIs via `arthur.client.*`
- Automatic telemetry/tracing configuration
- Unified credential management

```python
from arthur_observability_sdk import ArthurClient

arthur = ArthurClient(
    task_id="your-task-id",
    api_key="your-api-key",
    base_url="https://app.arthur.ai",  # optional
    service_name="my-service",  # optional, auto-derived if not provided
    enable_telemetry=True,  # optional, default True
    use_simple_processor=False  # optional, for testing/debugging
)
```

### API Access

All Arthur platform APIs are accessible through `arthur.client`:

#### Prompts API

```python
from uuid import UUID

# Render a prompt with variables (creates a span automatically)
prompt = arthur.client.prompts.render_saved_agentic_prompt(
    task_id=UUID("your-task-id"),
    prompt_name="my_prompt",
    prompt_version="latest",  # or version number, tag, datetime
    variables={"var1": "value1", "var2": "value2"}
)

# Access other generated API endpoints via arthur.client.base_client
# (All endpoints are available, more high-level wrappers coming soon)
```

The `render_saved_agentic_prompt` method automatically creates an OpenInference span with:
- **Span name**: `"template prompt: {prompt_name}"`
- **Input**: JSON of variables and metadata
- **Output**: Rendered prompt messages
- **Metadata**: `{"type": "prompt_templating", "source": "arthur"}`

### Telemetry Configuration

Access the telemetry handler for advanced configuration:

```python
# Check if telemetry is active
if arthur.telemetry.is_initialized():
    print("Telemetry is running")

# Manually shutdown telemetry
arthur.telemetry.shutdown()
```

### Context Manager

Use the `context` function to add session, user, and metadata to all spans within a scope:

```python
from arthur_observability_sdk import context

with context(
    session_id="conversation-123",
    user_id="user-456",
    metadata={"environment": "production"},
    tags=["important", "customer-facing"]
):
    # All spans created here will inherit these attributes
    result = your_application_logic()
```

Available context attributes:
- `session_id`: Track conversation threads
- `user_id`: Associate actions with users
- `metadata`: Dict of custom metadata
- `tags`: List of tags for filtering
- Any additional `**kwargs` are added as custom attributes

## Framework Instrumentation

Auto-instrument your AI/LLM frameworks to capture detailed traces:

### OpenAI

```python
from arthur_observability_sdk import ArthurClient, instrument_openai
import openai

arthur = ArthurClient(...)
instrument_openai()

# All OpenAI calls are now automatically traced
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### LangChain

```python
from arthur_observability_sdk import ArthurClient, instrument_langchain
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

arthur = ArthurClient(...)
instrument_langchain()

# All LangChain operations are now automatically traced
model = ChatOpenAI(model="gpt-4")
response = model.invoke([HumanMessage(content="Hello!")])
```

### Anthropic

```python
from arthur_observability_sdk import ArthurClient, instrument_anthropic
import anthropic

arthur = ArthurClient(...)
instrument_anthropic()

# All Anthropic calls are now automatically traced
client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### LlamaIndex

```python
from arthur_observability_sdk import ArthurClient, instrument_llama_index
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

arthur = ArthurClient(...)
instrument_llama_index()

# All LlamaIndex operations are now automatically traced
documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What is the meaning of life?")
```

### Multiple Frameworks

```python
from arthur_observability_sdk import ArthurClient, instrument_all

arthur = ArthurClient(...)

# Auto-instrument all installed frameworks at once
instrument_all()
```

Or selectively:

```python
from arthur_observability_sdk import (
    ArthurClient,
    instrument_openai,
    instrument_langchain,
    instrument_anthropic
)

arthur = ArthurClient(...)
instrument_openai()
instrument_langchain()
instrument_anthropic()
```

## Complete Examples

### LangChain Agent with Session Tracking

```python
import os
from arthur_observability_sdk import ArthurClient, context, instrument_langchain
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Initialize
arthur = ArthurClient(
    task_id=os.getenv("ARTHUR_TASK_ID"),
    api_key=os.getenv("ARTHUR_API_KEY"),
    service_name="langchain-agent"
)

instrument_langchain()

# Create agent
model = ChatOpenAI(model="gpt-4")

# Simulate a conversation with session tracking
session_id = "conversation-abc-123"
user_id = "user-456"

with context(session_id=session_id, user_id=user_id, tags=["production"]):
    # First turn
    response1 = model.invoke([
        HumanMessage(content="What's the capital of France?")
    ])
    print(f"AI: {response1.content}")

    # Second turn (same session)
    response2 = model.invoke([
        HumanMessage(content="What's the capital of France?"),
        AIMessage(content=response1.content),
        HumanMessage(content="What's its population?")
    ])
    print(f"AI: {response2.content}")

arthur.shutdown()
```

### Prompt Fetching + OpenAI

```python
import os
from uuid import UUID
from arthur_observability_sdk import ArthurClient, context, instrument_openai
import openai

# Initialize
arthur = ArthurClient(
    task_id=os.getenv("ARTHUR_TASK_ID"),
    api_key=os.getenv("ARTHUR_API_KEY"),
)

instrument_openai()

# Fetch and render a prompt
task_id = UUID(os.getenv("ARTHUR_TASK_ID"))
prompt = arthur.client.prompts.render_saved_agentic_prompt(
    task_id=task_id,
    prompt_name="customer_greeting",
    prompt_version="latest",
    variables={"customer_name": "Alice", "product": "Widget Pro"}
)

# Use the rendered prompt with OpenAI
with context(session_id="greeting-flow", user_id="alice@example.com"):
    response = openai.chat.completions.create(
        model=prompt.model_name,
        messages=prompt.messages
    )
    print(response.choices[0].message.content)

arthur.shutdown()
```

### Disabling Telemetry (API-only mode)

```python
from arthur_observability_sdk import ArthurClient
from uuid import UUID

# Initialize without telemetry
arthur = ArthurClient(
    task_id="your-task-id",
    api_key="your-api-key",
    enable_telemetry=False  # No spans will be created
)

# API calls work normally, but no tracing occurs
prompt = arthur.client.prompts.render_saved_agentic_prompt(
    task_id=UUID("your-task-id"),
    prompt_name="my_prompt",
    prompt_version="latest",
    variables={"key": "value"}
)
```

### Context Manager for Automatic Cleanup

```python
from arthur_observability_sdk import ArthurClient, instrument_openai
import openai

with ArthurClient(
    task_id="your-task-id",
    api_key="your-api-key"
) as arthur:
    instrument_openai()

    # Your application code
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello!"}]
    )

# arthur.shutdown() called automatically when exiting context
```

## Environment Variables

The SDK supports configuration via environment variables for convenience:

```bash
export ARTHUR_TASK_ID="your-task-id"
export ARTHUR_API_KEY="your-api-key"
export ARTHUR_BASE_URL="https://app.arthur.ai"  # optional
```

Then initialize without parameters:

```python
from arthur_observability_sdk import ArthurClient

# Credentials loaded from environment
arthur = ArthurClient()
```

## Troubleshooting

### Verify Telemetry is Active

```python
arthur = ArthurClient(...)

if arthur.telemetry.is_initialized():
    print("✓ Telemetry is active")
else:
    print("✗ Telemetry is not active")
```

### Use Simple Processor for Testing

For immediate span export (useful in testing/debugging):

```python
arthur = ArthurClient(
    task_id="...",
    api_key="...",
    use_simple_processor=True  # Spans export immediately, not batched
)
```

### Manual Telemetry Shutdown

```python
# Ensure all spans are flushed before exit
arthur.telemetry.shutdown()
```

## API Reference

### ArthurClient

**Parameters:**
- `task_id` (str, optional): Arthur task ID. Falls back to `ARTHUR_TASK_ID` env var.
- `api_key` (str, optional): Arthur API key. Falls back to `ARTHUR_API_KEY` env var.
- `base_url` (str, optional): Arthur base URL. Falls back to `ARTHUR_BASE_URL` env var. Default: `"https://app.arthur.ai"`.
- `service_name` (str, optional): Service name for traces. Auto-derived from script name if not provided.
- `enable_telemetry` (bool, optional): Whether to enable tracing. Default: `True`.
- `use_simple_processor` (bool, optional): Use SimpleSpanProcessor for immediate export. Default: `False`.
- `resource_attributes` (dict, optional): Additional resource attributes for traces.

**Attributes:**
- `client`: Access to Arthur API client
- `telemetry`: Access to TelemetryHandler class
- `task_id`: The configured Arthur task ID

**Methods:**
- `shutdown()`: Shutdown telemetry and HTTP client

### context()

**Parameters:**
- `session_id` (str, optional): Session/conversation ID
- `user_id` (str, optional): User identifier
- `metadata` (dict, optional): Custom metadata dictionary
- `tags` (list[str], optional): List of tags
- `**kwargs`: Additional custom attributes

### Instrumentors

All instrumentor functions return an instrumentor instance that can be used to uninstrument later:

```python
from arthur_observability_sdk import instrument_openai

instrumentor = instrument_openai()

# Your code...

# Uninstrument when done
instrumentor.uninstrument()
```

Available instrumentors:
- `instrument_openai()`
- `instrument_langchain()`
- `instrument_anthropic()`
- `instrument_llama_index()`
- `instrument_bedrock()`
- `instrument_vertexai()`
- `instrument_mistralai()`
- `instrument_groq()`
- `instrument_all()`

## Generating API Client

The SDK uses `openapi-python-client` to generate Python bindings from the Arthur GenAI Engine's OpenAPI specification. To regenerate the client after API updates:

```bash
# From the arthur-sdk directory
cd arthur-sdk
./scripts/generate_client.sh
```

This script will:
1. Read the OpenAPI spec from `../genai-engine/staging.openapi.json`
2. Generate the client code in `src/arthur_observability_sdk/_generated/`

The client generation is configured via [scripts/openapi-generator-config.yaml](scripts/openapi-generator-config.yaml).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

## Support

For questions, issues, or feature requests:
- Open an issue on [GitHub](https://github.com/arthur-ai/arthur-engine/issues)
- Contact Arthur support

## Changelog

### v0.1.0 (Alpha)
- Initial alpha release
- Unified ArthurClient for API and telemetry
- Prompt management API with automatic instrumentation
- Multi-framework support for OpenAI, LangChain, Anthropic, LlamaIndex, and more
- Session and user tracking via context manager
- OpenTelemetry-based tracing with OTLP export

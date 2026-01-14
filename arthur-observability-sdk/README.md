# Arthur Observability SDK

[![PyPI version](https://badge.fury.io/py/arthur-observability-sdk.svg)](https://badge.fury.io/py/arthur-observability-sdk)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

> 🔵 **Beta Release**: This SDK is currently in beta and available on PyPI.

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

### Install from PyPI (Recommended)

The SDK is now available on PyPI and can be installed with pip:

```bash
# Core SDK only
pip install arthur-observability-sdk

# With specific framework support
pip install arthur-observability-sdk[openai]
pip install arthur-observability-sdk[langchain]
pip install arthur-observability-sdk[anthropic]
pip install arthur-observability-sdk[llama-index]

# With multiple frameworks
pip install arthur-observability-sdk[openai,langchain]

# With all supported frameworks
pip install arthur-observability-sdk[all]
```

### Install from Source (Development)

For development or to use the latest features:

```bash
# Clone the monorepo
git clone https://github.com/arthur-ai/arthur-engine.git
cd arthur-engine/arthur-observability-sdk

# Install in editable mode
pip install -e .

# Or with framework support
pip install -e ".[all]"
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

## Getting Started

### Step 1: Get Your API Token

To use the Arthur Observability SDK, you'll need an API token from the **Arthur GenAI Engine**.

**[→ GenAI Engine Installation Guide](https://github.com/arthur-ai/arthur-engine/tree/main/deployment/docker-compose/genai-engine)**

Once the GenAI Engine is running (default: `http://localhost:3030`), you can:
1. Navigate to `http://localhost:3030/docs` for API documentation
2. Generate an API key from the GenAI Engine UI or API
3. Use the key with this SDK


### Step 2: Initialize ArthurClient

The `ArthurClient` is your main entry point for both API access and automatic telemetry.

#### Recommended: Use task_name (Auto-creates if needed)

```python
import os
from arthur_observability_sdk import ArthurClient

# Initialize with a task name - will create the task if it doesn't exist
arthur = ArthurClient(
    task_name="my-llm-app",  # Task name - will auto-create if needed
    api_key=os.getenv("ARTHUR_API_KEY"),  # Your API key
    base_url=os.getenv("ARTHUR_BASE_URL", "http://localhost:3030"),
    service_name="my-llm-app"  # Name for your service in traces
)

# The client is now ready - task was automatically created/retrieved
print(f"✓ Connected to Arthur with task ID: {arthur.task_id}")
```

#### Alternative: Use task_id directly

If you already have a task ID, you can provide it directly:

```python
arthur = ArthurClient(
    task_id="550e8400-e29b-41d4-a716-446655440000",  # Existing task ID
    api_key=os.getenv("ARTHUR_API_KEY"),
    base_url=os.getenv("ARTHUR_BASE_URL", "http://localhost:3030")
)
```

**Environment Variables**: You can also configure via environment:
```bash
export ARTHUR_TASK_NAME="my-llm-app"  # Recommended - auto-creates task
# OR
export ARTHUR_TASK_ID="your-task-id"  # If you have an existing task ID

export ARTHUR_API_KEY="your-api-key"
export ARTHUR_BASE_URL="http://localhost:3030"  # GenAI Engine URL
```

### Step 3: Instrument OpenAI

Auto-instrument OpenAI to capture all LLM calls:

```python
from arthur_observability_sdk import instrument_openai
import openai

# Initialize Arthur with task name
arthur = ArthurClient(
    task_name="my-llm-app",
    api_key=os.getenv("ARTHUR_API_KEY")
)

# Instrument OpenAI - all calls are now traced
instrument_openai()

# Make OpenAI calls - automatically traced to Arthur
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello, how are you?"}]
)

print(response.choices[0].message.content)

# Cleanup
arthur.shutdown()
```

**What gets traced:**
- Model name and parameters
- Input messages
- Output responses
- Token counts and latency
- All metadata following OpenInference conventions

### Step 4: Instrument LangChain

Auto-instrument LangChain for agent and chain tracing:

```python
from arthur_observability_sdk import ArthurClient, instrument_langchain
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Initialize Arthur with task name
arthur = ArthurClient(
    task_name="my-llm-app",
    api_key=os.getenv("ARTHUR_API_KEY")
)

# Instrument LangChain
instrument_langchain()

# Create and use LangChain components - automatically traced
model = ChatOpenAI(model="gpt-4")
response = model.invoke([HumanMessage(content="What is the capital of France?")])

print(f"Response: {response.content}")

arthur.shutdown()
```

**What gets traced:**
- Chain execution steps
- LLM calls within chains
- Tool invocations
- Agent reasoning steps
- Complete execution hierarchy

### Step 5: Advanced Telemetry Configuration

Configure span processors, custom metadata, and resource attributes:

#### Using SimpleSpanProcessor for Immediate Export

Useful for debugging or testing:

```python
arthur = ArthurClient(
    task_name="my-llm-app",
    api_key=os.getenv("ARTHUR_API_KEY"),
    use_simple_processor=True  # Spans export immediately, not batched
)
```

**When to use:**
- **SimpleSpanProcessor**: Debugging, testing, or low-throughput applications
- **BatchSpanProcessor (default)**: Production environments with high throughput

#### Adding Custom Resource Attributes

Enrich traces with custom metadata about your service:

```python
arthur = ArthurClient(
    task_name="recommendation-service",
    api_key=os.getenv("ARTHUR_API_KEY"),
    service_name="recommendation-service",
    resource_attributes={
        "environment": "production",
        "version": "2.1.0",
        "datacenter": "us-west-2",
        "team": "ml-platform"
    }
)
```

These attributes will be attached to all spans as resource-level metadata.

#### Verifying Telemetry is Active

```python
# Check if telemetry initialized correctly
if arthur.telemetry.is_initialized():
    print("✓ Telemetry is active and sending traces")
else:
    print("✗ Telemetry is not active")
```

### Step 6: Session and User Tracking

Use the `context` manager to add session and user metadata:

```python
from arthur_observability_sdk import ArthurClient, context, instrument_openai
import openai

arthur = ArthurClient(
    task_name="customer-support-bot",
    api_key=os.getenv("ARTHUR_API_KEY")
)
instrument_openai()

# Track a conversation session
session_id = "conversation-abc-123"
user_id = "user-456"

with context(
    session_id=session_id,
    user_id=user_id,
    metadata={"environment": "production", "experiment": "new-prompt-v2"},
    tags=["customer-support", "priority-high"]
):
    # All spans in this block inherit the context
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "I need help with my order"}]
    )
    print(response.choices[0].message.content)

arthur.shutdown()
```

**Context Attributes:**
- `session_id`: Track conversation threads across multiple interactions
- `user_id`: Associate spans with specific users
- `metadata`: Dictionary of custom key-value pairs
- `tags`: List of tags for filtering in the Arthur dashboard
- `**kwargs`: Any additional attributes you want to track

**Use cases:**
- Track multi-turn conversations
- A/B testing with experiment metadata
- User segmentation and analysis
- Environment-specific tracking (dev/staging/prod)

### Step 7: Fetching and Using Prompts

Fetch managed prompts from Arthur and use them with automatic tracing:

```python
import os
from uuid import UUID
from arthur_observability_sdk import ArthurClient, context, instrument_openai
import openai

# Initialize with task name
arthur = ArthurClient(
    task_name="customer-support-bot",
    api_key=os.getenv("ARTHUR_API_KEY")
)
instrument_openai()

# Fetch prompt and make LLM call inside context for proper session tracking
with context(session_id="support-email-001", user_id="alice@example.com"):
    # Fetch a prompt from Arthur (automatically creates a span)
    # Use the task_id from the client (it was auto-resolved from task_name)
    prompt = arthur.client.prompts.render_saved_agentic_prompt(
        task_id=UUID(arthur.task_id),
        prompt_name="customer_email_template",
        prompt_version="latest",  # or specific version, tag, datetime
        variables={
            "customer_name": "Alice",
            "order_id": "12345",
            "issue": "delayed shipment"
        }
    )

    # Use the rendered prompt with OpenAI
    response = openai.chat.completions.create(
        model=prompt.model_name,  # Model specified in the prompt
        messages=prompt.messages,  # Pre-rendered messages with variables
        temperature=prompt.temperature  # Settings from the prompt
    )
    print(response.choices[0].message.content)

arthur.shutdown()
```

**Prompt fetching automatically:**
- Creates an OpenInference span with type `prompt_templating`
- Tracks input variables and rendered output
- Records prompt name and version
- Links to subsequent LLM calls in the trace

**Benefits of managed prompts:**
- Version control for prompts
- A/B testing different prompt versions
- Centralized prompt management
- Automatic tracking of prompt changes impact

## Additional Framework Support

Beyond OpenAI and LangChain, the SDK supports many other LLM frameworks:

### Anthropic

```python
from arthur_observability_sdk import ArthurClient, instrument_anthropic
import anthropic

arthur = ArthurClient(
    task_name="my-llm-app",
    api_key=os.getenv("ARTHUR_API_KEY")
)
instrument_anthropic()

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

arthur = ArthurClient(
    task_name="my-rag-app",
    api_key=os.getenv("ARTHUR_API_KEY")
)
instrument_llama_index()

documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What is the meaning of life?")
```

### Instrumenting All Frameworks

```python
from arthur_observability_sdk import ArthurClient, instrument_all

arthur = ArthurClient(
    task_name="my-multi-framework-app",
    api_key=os.getenv("ARTHUR_API_KEY")
)

# Automatically instruments all installed frameworks
instrument_all()
```

Available instrumentors:
- `instrument_openai()` - OpenAI
- `instrument_langchain()` - LangChain
- `instrument_anthropic()` - Anthropic
- `instrument_llama_index()` - LlamaIndex
- `instrument_bedrock()` - AWS Bedrock
- `instrument_vertexai()` - Google VertexAI
- `instrument_mistralai()` - MistralAI
- `instrument_groq()` - Groq
- `instrument_all()` - All of the above

## Complete Examples

### Multi-Turn Conversation with LangChain

Track a complete conversation session across multiple turns:

```python
import os
from arthur_observability_sdk import ArthurClient, context, instrument_langchain
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Initialize with task name
arthur = ArthurClient(
    task_name="customer-support-bot",
    api_key=os.getenv("ARTHUR_API_KEY"),
    service_name="customer-support-bot"
)
instrument_langchain()

# Simulate a multi-turn conversation
session_id = "conversation-abc-123"
user_id = "user-456"
model = ChatOpenAI(model="gpt-4")

with context(
    session_id=session_id,
    user_id=user_id,
    metadata={"channel": "web", "department": "support"},
    tags=["production", "customer-facing"]
):
    # First turn
    response1 = model.invoke([
        HumanMessage(content="What's the capital of France?")
    ])
    print(f"AI: {response1.content}")

    # Second turn (builds on first)
    response2 = model.invoke([
        HumanMessage(content="What's the capital of France?"),
        AIMessage(content=response1.content),
        HumanMessage(content="What's its population?")
    ])
    print(f"AI: {response2.content}")

arthur.shutdown()
```

### Using Context Manager for Automatic Cleanup

The SDK supports Python context managers for automatic resource cleanup:

```python
from arthur_observability_sdk import ArthurClient, instrument_openai
import openai

# Context manager automatically calls shutdown()
with ArthurClient(
    task_name="my-llm-app",
    api_key=os.getenv("ARTHUR_API_KEY")
) as arthur:
    instrument_openai()

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    print(response.choices[0].message.content)

# arthur.shutdown() called automatically when exiting
```

### API-Only Mode (Disabling Telemetry)

Use Arthur APIs without tracing:

```python
from arthur_observability_sdk import ArthurClient
from uuid import UUID

# Disable telemetry for API-only access
arthur = ArthurClient(
    task_name="my-api-project",
    api_key=os.getenv("ARTHUR_API_KEY"),
    enable_telemetry=False  # No tracing
)

# API calls work normally without creating spans
prompt = arthur.client.prompts.render_saved_agentic_prompt(
    task_id=UUID(arthur.task_id),  # Use the auto-resolved task_id
    prompt_name="my_prompt",
    prompt_version="latest",
    variables={"key": "value"}
)
```

## Examples

Check out the [`examples/`](examples/) directory for complete, runnable examples:

### [LangChain Timezone Agent](examples/langchain-timezone-agent/)

A comprehensive tutorial demonstrating:
- Setting up ArthurClient with automatic task creation
- Auto-instrumenting LangChain agents
- Building custom tools
- Session and user tracking with context
- Full conversation tracing

Each example includes its own README, dependencies, and configuration guide.

## Configuration Reference

### Environment Variables

The SDK supports configuration via environment variables:

```bash
# Required - Choose ONE of:
export ARTHUR_TASK_NAME="my-llm-app"  # Recommended - auto-creates task
# OR
export ARTHUR_TASK_ID="your-task-id"  # If you have an existing task ID

# Required
export ARTHUR_API_KEY="your-api-key"

# Optional
export ARTHUR_BASE_URL="http://localhost:3030"  # Default if not set
```

Then initialize without explicit parameters:

```python
from arthur_observability_sdk import ArthurClient

# Credentials loaded from environment (uses ARTHUR_TASK_NAME or ARTHUR_TASK_ID)
arthur = ArthurClient()
print(f"✓ Using task ID: {arthur.task_id}")
```

### ArthurClient Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_name` | str | Yes* | `ARTHUR_TASK_NAME` env | Task name (recommended) - auto-creates if doesn't exist |
| `task_id` | str | Yes* | `ARTHUR_TASK_ID` env | Task ID (alternative to task_name) |
| `api_key` | str | Yes | `ARTHUR_API_KEY` env | Your Arthur API key |
| `base_url` | str | No | `http://localhost:3030` | GenAI Engine URL |
| `service_name` | str | No | Auto-derived | Name for your service in traces |
| `enable_telemetry` | bool | No | `True` | Enable/disable OpenTelemetry tracing |
| `use_simple_processor` | bool | No | `False` | Use SimpleSpanProcessor (immediate export) |
| `resource_attributes` | dict | No | `{}` | Custom resource attributes for traces |

*Either `task_name` (recommended) or `task_id` is required

### Context Manager Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | str | Track conversation threads |
| `user_id` | str | Associate spans with users |
| `metadata` | dict | Custom metadata key-value pairs |
| `tags` | list[str] | Tags for filtering |
| `**kwargs` | any | Additional custom attributes |

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
- `task_name` (str, optional): Arthur task name (recommended). Auto-creates task if it doesn't exist. Falls back to `ARTHUR_TASK_NAME` env var. Either `task_name` or `task_id` is required.
- `task_id` (str, optional): Arthur task ID. Falls back to `ARTHUR_TASK_ID` env var. Use if you already have a task ID.
- `api_key` (str, optional): Arthur API key. Falls back to `ARTHUR_API_KEY` env var.
- `base_url` (str, optional): GenAI Engine base URL. Falls back to `ARTHUR_BASE_URL` env var. Default: `"http://localhost:3030"`.
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

### v0.1.0 (Beta) - Current

**🎉 Now available on PyPI!**

- Published to PyPI as `arthur-observability-sdk`
- Unified ArthurClient for API and telemetry
- Prompt management API with automatic instrumentation
- Multi-framework support for OpenAI, LangChain, Anthropic, LlamaIndex, AWS Bedrock, VertexAI, MistralAI, and Groq
- Session and user tracking via context manager
- OpenTelemetry-based tracing with OTLP export
- Automatic task creation from task names
- Configurable span processors (batch and simple modes)

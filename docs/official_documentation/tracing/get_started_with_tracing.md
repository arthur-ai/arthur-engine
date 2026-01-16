# Get Started with Tracing

This quickstart helps you ingest your first trace in Arthur using OpenInference.

## Host Your Own Engine

You can run Arthur Engine locally using Docker Compose. This is useful for development, testing, or self-hosted deployments.

### Quick Start with Docker

1. **Clone the repository**:
    
    ```bash
    git clone https://github.com/arthur-ai/arthur-engine.git
    cd arthur-engine/deployment/docker-compose/genai-engine
    ```
    
2. **Create environment file and start the engine**
    
    ```bash
    cp .env.template .env
    # Edit .env with your configuration
    
    docker compose up
    ```
    
3. **Access the engine**: Once the containers are running, you can access:
    - **UI**: [http://localhost:3030/](http://localhost:3030/) - Web interface for managing tasks and viewing traces
    - **API Docs**: [http://localhost:3030/docs](http://localhost:3030/docs) - Interactive Swagger/OpenAPI documentation

The Docker Compose setup includes:

- **PostgreSQL database** (port 5435)
- **GenAI Engine** (port 3030)
- All necessary dependencies and configurations

<aside>
💡

**Notes**: 

1. For production deployments, you’ll also need to configure an OpenAI-compatible GPT model for evaluation features. 
2. For more detailed deployment instructions and additional deployment options, see the [official Arthur Engine repository](https://github.com/arthur-ai/arthur-engine/tree/dev/genai-engine).
</aside>

## Get API Keys

1. **Access your self-hosted Arthur instance**:
    - **UI**: `http://localhost:3030/` - Web interface for managing tasks
    - **API Docs**: `http://localhost:3030/docs` - Interactive Swagger/OpenAPI documentation
2. **Create API credentials** via the `/auth/api_keys` endpoint:
    - Use `POST /auth/api_keys` to create a new API key
    - The endpoint requires authentication with a master/admin key (The master key can be found in the compose file)
    - Response includes the API key (store it securely - it won’t be retrievable later)

**Example API request:**

```bash
curl -X POST "http://localhost:3030/auth/api_keys/" \
  -H "Authorization: Bearer changeme_genai_engine_admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "My tracing API key",
    "roles": ["ORG-ADMIN"]
  }'
```

## Create a Task

Before you can send traces, you need to create a task in Arthur. You can do this via the UI or API.

### Option 1: Create Task via UI

1. **Log into Arthur** using your API key:
    - Navigate to `http://localhost:3030/` in your browser
    - Use your API key to authenticate
2. **Create a new task**:
    - Click “Create Task” or navigate to the tasks page
    - Enter a task name
    - Tasks created in the UI are `agentic` by default
    - Save the task and copy the task ID

### Option 2: Create Task via API

**Example API request:**

```bash
curl -X POST "http://localhost:3030/api/v2/tasks" \
  -H "Authorization: Bearer {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Tracing Task",
    "is_agentic": true
  }'
```

The response will include the task `id` - save this as your `ARTHUR_TASK_ID`.

## Ingest Your First Trace

Use OpenInference with OpenTelemetry to send traces to Arthur.

### Install Dependencies

```bash
pip install openinference-instrumentation-langchain langchain-openai langchain opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp python-dotenv
```

### Configure Environment Variables

Create a `.env` file:

```bash
# Arthur Configuration
ARTHUR_BASE_URL=http://localhost:3030
ARTHUR_API_KEY=your_api_key_here
ARTHUR_TASK_ID=your_task_id_here  # ensure task is marked as agentic: is_agentic=True
# LLM Configuration (if using LangChain)
OPENAI_API_KEY=your_openai_api_key_here
```

### Basic Setup

The simplest way to start tracing is to set up OpenTelemetry with OpenInference instrumentation:

```python
import os
from dotenv import load_dotenv
from opentelemetry import trace as trace_api
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from openinference.instrumentation.langchain import LangChainInstrumentor

load_dotenv()

def setup_tracing():
    """Set up OpenInference tracing with Arthur endpoint."""    
    arthur_base_url = os.getenv("ARTHUR_BASE_URL")
    arthur_api_key = os.getenv("ARTHUR_API_KEY")
    arthur_task_id = os.getenv("ARTHUR_TASK_ID")
    
    # Create tracer provider with Arthur task metadata    
    tracer_provider = trace_sdk.TracerProvider(
        resource=Resource.create({
            "arthur.task": arthur_task_id,
            "service.name": "my-tracing-app"        })
    )
    trace_api.set_tracer_provider(tracer_provider)
    
    # Configure OTLP exporter and add span processor    
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{arthur_base_url}/v1/traces",
                headers={"Authorization": f"Bearer {arthur_api_key}"}
            )
        )
    )
    
    # Instrument LangChain (if using LangChain)    
    LangChainInstrumentor().instrument()

# Call setup before using your LLM/Agent
setup_tracing()
```

### Example: Tracing a LangChain Agent

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Set up tracing (call this once at startup)
setup_tracing()

# Create your agent - all interactions are automatically traced
model = ChatOpenAI(model="gpt-4o", temperature=0)
agent_executor = AgentExecutor(
    agent=create_openai_tools_agent(model, tools=[], prompt=...),
    tools=[],
    verbose=True)

# Run your agent - traces are automatically sent to Arthur
result = agent_executor.invoke({"input": "Hello!"})
```

### Example: Manual Span Creation

You can also create spans manually for custom instrumentation:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def my_function():
    with tracer.start_as_current_span("my_function") as span:
        span.set_attribute("input", "some input")
        result = "Hello, world!"        
        span.set_attribute("output", result)
        return result

my_function()
```

## Key Concepts

### OpenInference Instrumentation

- **LangChainInstrumentor**: Automatically instruments LangChain components to create spans
- **Resource**: Embeds metadata (like Arthur task ID) into all traces automatically
- **OTLPSpanExporter**: Sends spans to Arthur via OTLP protocol

### Arthur Integration

- **Task ID**: Links all traces to a specific Arthur task (set via `arthur.task` resource attribute)
- **API Key**: Authenticates your application with Arthur

## View Your Traces

After running your application, traces will appear in your Arthur dashboard:

1. Navigate to `http://localhost:3030/` and select your task
2. View traces with:
    - LLM calls and responses
    - Tool invocations
    - Agent execution steps
    - Timing information
    - Input/output data

## Next Steps

- **Add more tools** to your agent and see how they appear in traces
- **Add session and user metadata** via convenient helpers like `using_session` and `using_user`
- **Scale up** to more complex agent architectures
- **Analyze traces** in the Arthur dashboard for performance insights

## Resources

- [OpenInference Documentation](https://openinference.io/)
- [Arthur Documentation](https://docs.arthur.ai/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
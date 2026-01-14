# OpenInference Tracing Tutorial with Arthur Observability SDK

A simple tutorial demonstrating how to set up OpenInference tracing with the Arthur Observability SDK using a LangChain agent. This tutorial includes timezone conversion tools to demonstrate tool usage and shows how to use the unified ArthurClient for both API access and automatic telemetry.

## What This Tutorial Covers

1. **Setting up OpenInference tracing** using the unified Arthur Observability SDK
2. **Auto-instrumenting a LangChain agent** with a single function call
3. **Using session and user context** for tracking conversations
4. **Running a chat agent with timezone tools** that automatically sends traces to Arthur

## Prerequisites

- Python 3.12+
- An Arthur account with API access
- An OpenAI API key
- **No need to pre-create a task!** The SDK will automatically create one for you based on a task name

## Setup

### 1. Install Arthur Observability SDK

First, install the Arthur Observability SDK with LangChain support from GitHub:

```bash
pip install "arthur-observability-sdk[langchain] @ git+https://github.com/arthur-ai/arthur-engine.git#subdirectory=arthur-sdk"
```

### 2. Install Tutorial Dependencies

```bash
# From the sdk_tutorial directory
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cd tutorial
cp env.example .env
```

Edit `.env` with your actual values:

```bash
# Arthur Configuration
ARTHUR_BASE_URL=https://app.arthur.ai  # or your self-hosted instance
ARTHUR_API_KEY=your_arthur_api_key_here

# Task Configuration - Option 1: Use task name (recommended)
# The SDK will automatically create this task if it doesn't exist
ARTHUR_TASK_NAME=timezone-tutorial-agent

# Task Configuration - Option 2: Use existing task ID (optional)
# ARTHUR_TASK_ID=your_task_id_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
```

**Note**: You can specify either `ARTHUR_TASK_NAME` or `ARTHUR_TASK_ID`. If you use `ARTHUR_TASK_NAME`, the SDK will:
1. Search for an existing task with that name
2. If found, use the existing task
3. If not found, automatically create a new agentic task with that name

### 4. Run the Tutorial

```bash
python app.py
```

## Available Tools

The agent comes with two timezone-related tools:

### 1. Current Time Tool
Get the current time in any timezone or city.

**Examples:**
- "What is the time in Zurich right now?"
- "What time is it in California?"
- "Current time in EST"

### 2. Timezone Conversion Tool
Convert times between different timezones.

**Examples:**
- "What is 10pm EDT in California?"
- "Convert 2:30pm EST to Tokyo time"
- "What time is 9am in London when it's 3pm in New York?"

## Supported Timezones and Cities

The tools support a wide range of timezones and cities:

**US Timezones:** EST, EDT, CST, CDT, MST, MDT, PST, PDT
**US Cities/States:** California, New York, Chicago, Denver, etc.

**International Cities:** Zurich, London, Paris, Tokyo, Beijing, Sydney, etc.
**Countries:** Japan, Germany, France, Australia, Brazil, etc.

**Common Abbreviations:** UTC, GMT, JST, IST, CET, BST, etc.

## File Structure

```
tutorial/
├── app.py                    # Main application with agent setup
├── timezone_tools.py         # Timezone functions and LangChain tools
├── timezone_shortcuts.json   # Timezone shortcuts and mappings
├── requirements.txt          # Python dependencies
├── env.example              # Environment variables template
└── README.md                # This file
```

## How It Works

### 1. Setting Up Tracing with Arthur Observability SDK

The tutorial uses the unified `ArthurClient` to set up both API access and automatic telemetry in a single initialization. The SDK now supports **automatic task creation** using task names:

```python
from arthur_observability_sdk import ArthurClient, context, instrument_langchain

def setup_arthur_client():
    """Set up Arthur client with API and telemetry."""
    global arthur

    # Initialize Arthur client with task_name (automatically creates if needed!)
    arthur = ArthurClient(
        task_name=os.getenv("ARTHUR_TASK_NAME", "timezone-tutorial-agent"),
        api_key=os.getenv("ARTHUR_API_KEY"),
        base_url=os.getenv("ARTHUR_BASE_URL"),
        service_name="multiagent-playground-tutorial",
        use_simple_processor=True  # For immediate span export
    )

    # Auto-instrument LangChain with one function call
    instrument_langchain()
```

**What Happens During Initialization:**
1. **API Client Setup**: The SDK first initializes the API client (without telemetry)
2. **Task Resolution**: If `task_name` is provided, the SDK:
   - Searches for an existing task with that name
   - If found, uses the existing task ID
   - If not found, creates a new agentic task and returns its ID
3. **Telemetry Initialization**: With the resolved task ID, the SDK initializes OpenTelemetry tracing
4. **Instrumentation**: LangChain is automatically instrumented for tracing

**Key Benefits:**
- **No Manual Task Creation**: Tasks are automatically created on first run
- **Idempotent**: Running multiple times with the same task_name reuses the existing task
- **Unified Interface**: Single client for both API and tracing
- **Automatic Configuration**: No manual OpenTelemetry setup required

### 2. Creating Tools

The tools are defined in `timezone_tools.py` using LangChain's `@tool` decorator:

```python
@tool
def get_current_time(timezone: str) -> str:
    """Get the current time in a specific timezone or city."""
    return current_time(timezone)

@tool
def convert_time_between_zones(time_str: str, from_timezone: str, to_timezone: str) -> str:
    """Convert a time from one timezone to another."""
    return convert_timezone(time_str, from_timezone, to_timezone)
```

### 3. Session and User Tracking

The SDK provides a convenient `context` manager for adding session and user metadata to traces:

```python
from arthur_observability_sdk import context

def chat_with_agent(agent_executor, message, session_id, user_id):
    """Chat with the agent with session and user tracking."""

    # Use context manager to add session and user metadata to traces
    with context(session_id=session_id, user_id=user_id):
        result = agent_executor.invoke({"input": message})

    return result["output"]
```

**What This Does:**
- Automatically adds `session_id` and `user_id` to all spans
- Enables conversation tracking across multiple interactions
- Helps analyze user-specific patterns in the Arthur dashboard

### 4. Automatic Task Management & Metadata Injection

The SDK provides intelligent task management:

**Task Resolution Flow:**
```python
# Option 1: Use task_name (recommended)
arthur = ArthurClient(task_name="my-app", api_key="...")
# SDK automatically: searches for "my-app" → creates if needed → returns task_id

# Option 2: Use task_id directly (if you already have one)
arthur = ArthurClient(task_id="uuid-here", api_key="...")
```

**Automatic Metadata Injection:**
Arthur task metadata is automatically injected by the `ArthurClient`:
- **Task ID**: Automatically resolved from task_name or directly provided
- **Service Name**: Custom name for your application
- **OpenInference Attributes**: Proper semantic conventions applied
- **OTLP Configuration**: Headers and endpoints configured automatically

**New `get_or_create_task` API:**
You can also manually use the task management API:
```python
# Get or create a task programmatically
task_id = arthur.client.tasks.get_or_create_task(
    task_name="my-custom-task",
    is_agentic=True
)
```

## Key Concepts

### Arthur Observability SDK

- **ArthurClient**: Unified client providing both API access and automatic telemetry
- **Auto-Instrumentation**: One-line instrumentation for LangChain and other frameworks
- **Context Manager**: Easy session and user tracking with the `context()` function
- **Automatic Configuration**: OpenTelemetry setup handled automatically

### OpenInference Instrumentation

- **instrument_langchain()**: Automatically instruments all LangChain components
- **Resource Attributes**: Task ID and service name automatically embedded in traces
- **OTLP Export**: Spans automatically sent to Arthur via OTLP protocol
- **Session Tracking**: Context manager adds metadata to all spans in scope

### Arthur Integration

- **Task ID**: Automatically links all traces to your Arthur task
- **Session Tracking**: Track conversation threads across multiple interactions
- **User Tracking**: Associate traces with specific users
- **Real-time**: Spans are exported to Arthur as they're created

### Tool Usage

- **Tool Calls**: Each tool invocation creates a separate span in Arthur
- **Input/Output**: Tool inputs and outputs are captured in the traces
- **Error Handling**: Tool errors are also captured and visible in Arthur

## What You'll See

1. **Console Output**: The agent will respond to your questions and use tools when needed
2. **Arthur Dashboard**: Traces will appear in your Arthur task with:
   - LLM calls and responses
   - Tool invocations (timezone conversions)
   - Agent execution steps
   - Session and user metadata
   - Timing information
   - Full conversation context

## Example Conversations

```
You: What time is it in Zurich right now?
Assistant: Let me check the current time in Zurich for you.
[Tool: get_current_time]
[Tool Result: 2024-12-19 15:30:45 ZURICH]
The current time in Zurich is 2024-12-19 15:30:45 ZURICH.

You: What is 10pm EDT in California?
Assistant: I'll convert 10pm EDT to California time for you.
[Tool: convert_time_between_zones]
[Tool Result: 2024-12-19 19:00:00 CALIFORNIA]
10pm EDT is 7:00 PM in California (PST).
```

## Troubleshooting

### Common Issues

1. **"api_key is required"**
   - Make sure your `.env` file exists and has the correct `ARTHUR_API_KEY`

2. **"Either task_id or task_name is required"**
   - Set either `ARTHUR_TASK_NAME` or `ARTHUR_TASK_ID` in your `.env` file
   - Or let the SDK use the default: `timezone-tutorial-agent`

3. **Task creation fails**
   - Verify your API key has permissions to create tasks
   - Check that your Arthur instance URL is correct
   - Ensure network connectivity

4. **"Failed to create task" errors**
   - Check the Arthur dashboard to see if the task already exists
   - Verify your API permissions
   - Check the SDK output for detailed error messages

5. **Connection errors**
   - Check that your Arthur URL is correct
   - Verify your API key is valid
   - Ensure network connectivity

6. **Tool errors**
   - Check that the timezone names are valid
   - Ensure time formats are correct (e.g., "10pm", "14:30")

## Next Steps

After running this tutorial, you can:

1. **Add more tools** to your agent and see how they appear in traces
2. **Customize metadata** to include additional context
3. **Scale up** to more complex agent architectures
4. **Analyze traces** in the Arthur dashboard for performance insights

## Additional Features of Arthur Observability SDK

The SDK provides many more features beyond this tutorial:

### Framework Support
- **OpenAI**: `instrument_openai()`
- **Anthropic**: `instrument_anthropic()`
- **LlamaIndex**: `instrument_llama_index()`
- **AWS Bedrock**: `instrument_bedrock()`
- **And more**: VertexAI, MistralAI, Groq

### API Access
Access Arthur platform APIs via `arthur.client`:

```python
# Render prompts with automatic span creation
prompt = arthur.client.prompts.render_saved_agentic_prompt(
    task_id=UUID(os.getenv("ARTHUR_TASK_ID")),
    prompt_name="my_prompt",
    prompt_version="latest",
    variables={"var1": "value1"}
)
```

### Advanced Context
Add custom metadata and tags:

```python
with context(
    session_id="session-123",
    user_id="user-456",
    metadata={"environment": "production"},
    tags=["important", "customer-facing"]
):
    # Your code here
```

### Telemetry Control
Check and manage telemetry:

```python
# Check if active
if arthur.telemetry.is_initialized():
    print("Tracing is active")

# Manually shutdown
arthur.shutdown()  # Flushes pending spans
```

## Resources

- [Arthur Observability SDK Repository](https://github.com/arthur-ai/arthur-observability-sdk)
- [OpenInference Documentation](https://openinference.io/)
- [Arthur Documentation](https://docs.arthur.ai/)
- [LangChain Documentation](https://python.langchain.com/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/) 
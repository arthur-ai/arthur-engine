# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

The Arthur Observability SDK is a unified Python SDK that combines Arthur platform API access with OpenInference-based OpenTelemetry tracing. It's part of the Arthur Engine monorepo located at `arthur-engine/arthur-observability-sdk/`.

**Core Purpose**: Provide a single `ArthurClient` that handles both:
1. API access to Arthur platform (prompts, experiments, evaluations)
2. Automatic OpenTelemetry tracing with OpenInference semantic conventions

## Development Commands

### Installation

```bash
# Install core SDK for development
pip install -e ".[dev]"

# Install with specific framework support
pip install -e ".[langchain]"    # LangChain only
pip install -e ".[openai]"       # OpenAI only
pip install -e ".[all]"          # All frameworks

# Install dev dependencies only
pip install -e ".[dev]"
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_arthur_client.py

# Run with coverage
pytest --cov=arthur_observability_sdk --cov-report=html

# Run specific test
pytest tests/test_arthur_client.py::test_arthur_client_init
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Regenerating API Client

The SDK includes auto-generated API bindings from the GenAI Engine's OpenAPI spec:

```bash
# From the arthur-observability-sdk directory
./scripts/generate_client.sh
```

**What this does:**
- Reads `../genai-engine/staging.openapi.json`
- Uses `openapi-python-client` to generate Python bindings
- Outputs to `src/arthur_observability_sdk/_generated/`
- Configuration in `scripts/openapi-generator-config.yaml`

**When to regenerate**: After any Arthur GenAI Engine API changes.

## Architecture

### Core Components

**ArthurClient** (`arthur_client.py`)
- Main entry point for SDK users
- Initializes API client and telemetry in a single call
- Can accept either `task_id` OR `task_name` (automatically fetches/creates tasks)
- Provides `arthur.client.*` for API access and `arthur.telemetry` for tracing control

**TelemetryHandler** (`telemetry.py`)
- Singleton-style handler for OpenTelemetry setup
- Configures TracerProvider with OTLP exporter pointing to Arthur
- Supports both BatchSpanProcessor (production) and SimpleSpanProcessor (debugging)
- Auto-derives service name from calling script if not provided

**InstrumentedArthurClient** (`api_client.py`)
- Wraps generated API client with automatic span creation
- Key method: `render_saved_agentic_prompt()` automatically creates OpenInference spans
- Span metadata: `{"type": "prompt_templating", "source": "arthur"}`

**Context Manager** (`context.py`)
- Provides `context(session_id=..., user_id=..., metadata=..., tags=...)`
- Uses OpenTelemetry's `using_attributes()` to inject metadata into all spans within scope
- Essential for tracking conversations and user sessions

**Instrumentors** (`instrumentors.py`)
- Thin wrappers around OpenInference instrumentors
- Each `instrument_*()` function returns the instrumentor instance for uninstrumentation
- `instrument_all()` automatically instruments all installed frameworks

### Generated Code

**`_generated/` directory**
- Auto-generated from Arthur GenAI Engine OpenAPI spec
- Contains `Client` class and all model classes
- **Never manually edit files in this directory**
- Regenerate when API changes using `./scripts/generate_client.sh`

### Key Design Patterns

**Unified Initialization Flow:**
1. User creates `ArthurClient(task_id=..., api_key=...)`
2. SDK initializes API client first (needed for task resolution)
3. If `task_name` provided instead of `task_id`, SDK calls `get_or_create_task()` API
4. With resolved `task_id`, SDK initializes telemetry with proper resource attributes
5. Returns ready-to-use client with both API access and tracing

**Automatic Span Creation:**
- API methods that fetch/render prompts automatically create spans
- Span follows OpenInference semantic conventions
- No user code required for basic tracing

**Optional Dependencies:**
- Core SDK has minimal dependencies (OpenTelemetry only)
- Framework instrumentors are optional extras (`[openai]`, `[langchain]`, etc.)
- Only installs what user actually needs

## Testing Strategy

Tests use `pytest` with `pytest-mock` for mocking:

**Key patterns:**
- Mock OpenTelemetry components to avoid actual trace export
- Mock HTTP client to avoid real API calls
- Use fixtures in `conftest.py` for common mocks
- Mock paths like `arthur_observability_sdk.telemetry.TracerProvider`

**Example test structure:**
```python
def test_arthur_client_init(mock_telemetry):
    arthur = ArthurClient(task_id="...", api_key="...")
    assert arthur.task_id == "..."
    assert arthur.telemetry.is_initialized()
```

## Common Patterns

### Adding New Instrumentor

1. Add dependency to `pyproject.toml` under `[project.optional-dependencies]`
2. Add function to `instrumentors.py`:
```python
def instrument_my_framework():
    """Auto-instrument MyFramework with OpenInference."""
    try:
        from openinference.instrumentation.myframework import MyFrameworkInstrumentor
        instrumentor = MyFrameworkInstrumentor()
        instrumentor.instrument()
        return instrumentor
    except ImportError:
        warnings.warn("myframework not installed. Install with: pip install arthur-observability-sdk[myframework]")
        return None
```
3. Export from `__init__.py`
4. Add to `instrument_all()` function

### Adding New API Wrapper

High-level API wrappers go in `api_client.py`:

1. Extend `InstrumentedArthurClient` class
2. Add method that wraps generated client method
3. Use `TraceHandler.create_span()` to add automatic tracing
4. Return result from generated client

Example:
```python
def my_new_api_method(self, task_id: UUID, name: str):
    """Call API endpoint with automatic span creation."""
    with TraceHandler.create_span(
        name=f"my_operation: {name}",
        input={"name": name},
        metadata={"type": "my_operation", "source": "arthur"}
    ) as span:
        result = self.base_client.my_endpoint.my_method(task_id=task_id, name=name)
        span.set_output(result)
        return result
```

## Monorepo Context

This SDK is part of the Arthur Engine monorepo:
- Located at: `arthur-engine/arthur-observability-sdk/`
- Sibling to `genai-engine/` (API server) and `ml-engine/`
- OpenAPI spec source: `../genai-engine/staging.openapi.json`

**When making changes:**
- SDK changes may require coordination with GenAI Engine API changes
- Always regenerate client after GenAI Engine API updates
- Examples should reference monorepo installation paths

## Package Structure for PyPI

```
arthur-observability-sdk/
├── src/
│   └── arthur_observability_sdk/    # Package code (included in distribution)
│       ├── __init__.py
│       ├── arthur_client.py
│       ├── telemetry.py
│       ├── api_client.py
│       ├── context.py
│       ├── instrumentors.py
│       ├── tracer.py
│       └── _generated/              # Auto-generated API client
├── tests/                           # Tests (NOT included in distribution)
├── examples/                        # Examples (NOT included in distribution)
├── scripts/                         # Scripts (NOT included in distribution)
├── pyproject.toml                   # Package metadata and dependencies
└── README.md                        # Package documentation
```

Only `src/arthur_observability_sdk/` is packaged for PyPI. Tests, examples, and scripts are development-only.

## Environment Variables

The SDK supports these environment variables for convenience:

- `ARTHUR_TASK_ID`: Task ID (alternative to passing `task_id` param)
- `ARTHUR_TASK_NAME`: Task name for auto-creation (alternative to `task_id`)
- `ARTHUR_API_KEY`: API key (required if not passed as param)
- `ARTHUR_BASE_URL`: Base URL (defaults to `https://app.arthur.ai`)

## Important Notes

- **Never commit API keys or task IDs to the repository**
- **Generated code (`_generated/`)**: Never manually edit; always regenerate from OpenAPI spec
- **Telemetry initialization**: Can only happen once per process (OpenTelemetry limitation)
- **Task resolution**: `task_name` is preferred over `task_id` for better UX (auto-creates if needed)
- **Framework imports**: Always wrapped in try/except with helpful import error messages

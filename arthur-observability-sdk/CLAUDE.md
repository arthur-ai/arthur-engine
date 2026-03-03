# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install
poetry install --with dev

# Test
poetry run pytest tests -v          # all tests (includes install/wheel smoke tests)
poetry run pytest tests/test_client.py::test_arthur_requires_task_or_service_name  # single test
poetry run pytest -k "telemetry"    # match expression

# Lint (all at once)
./scripts/lint.sh

# Individually
poetry run black src tests
poetry run isort src tests --profile black
poetry run autoflake --remove-all-unused-imports --in-place --recursive src tests
poetry run mypy src/arthur_observability_sdk

# Build wheel
poetry build --format wheel

# Regenerate arthur_genai_client from GenAI Engine OpenAPI spec
./scripts/generate_client.sh generate
```

## Architecture

The SDK has three layers:

**`Arthur`** (`arthur.py`) — the user-facing entrypoint. Owns the OTel `TracerProvider`, the API client, and the 32 `instrument_*` methods. At least one of `task_id`, `task_name`, or `service_name` must be provided.

**`setup_telemetry`** (`telemetry.py`) — creates a `TracerProvider` with a `BatchSpanProcessor` backed by an OTLP HTTP exporter. Passes `Authorization: Bearer {api_key}` in the exporter headers. Called by `Arthur.__init__` when `enable_telemetry=True`. Registers the provider globally via `trace.set_tracer_provider()`.

**`ArthurAPIClient`** (`_client.py`) — thin wrapper around the generated `arthur_genai_client`. Exposes `get_prompt_by_version`, `get_prompt_by_tag`, `render_prompt`, and `resolve_task_id`. All `ApiException`s are converted to `ArthurAPIError(status_code, detail)`.

## Generated Client (`arthur_genai_client`)

This package is auto-generated from `genai-engine/staging.openapi.json` using OpenAPI Generator v7. **Do not hand-edit it.** Regenerate whenever the GenAI Engine API changes:

```bash
./scripts/generate_client.sh generate
```

`ArthurAPIClient` uses only `PromptsApi` and `TasksApi`. Call the plain (non-`_with_http_info`) variants — they return typed Pydantic model instances. Convert to a plain dict with `.model_dump()`. Only reach for `*_with_http_info()` / `.raw_data` if you need HTTP headers or status codes that the typed response doesn't expose.

## Key Patterns

**Task ID resolution** is lazy: if `task_name` is given instead of `task_id`, the name is resolved to a UUID on the first prompt call via `_api_client.resolve_task_id()` and cached in `_resolved_task_id`.

**PROMPT spans** (`get_prompt`, `render_prompt`) are created manually, not via an instrumentor. Because of this they bypass the OpenInference span processor, so `_apply_openinference_context()` must be called explicitly to copy `session.id`, `user.id`, etc. from the OTel context onto the span.

**`render_prompt` span attributes** deliberately distinguish template from result:
- `llm.prompt_template` / `input.value` → original unrendered messages + variable values
- `output.value` → rendered messages with variables substituted

**Framework instrumentation** is all optional. Each `instrument_*` method calls `importlib.import_module()` and raises `ImportError` with the correct `pip install arthur-observability-sdk[{extra}]` hint if the optional dependency is absent.

**`enable_telemetry=False`** skips `TracerProvider` creation entirely — useful when only using prompt management without telemetry.

## Testing

Unit tests mock at the `OTLPSpanExporter` boundary (patch `arthur_observability_sdk.telemetry.OTLPSpanExporter`) or use `InMemorySpanExporter` with a real `TracerProvider` for span-content assertions.

The helper pattern used throughout `test_prompt_management.py` and `test_context_helpers.py`:

```python
def _make_arthur_with_in_memory_spans(task_id=TASK_ID):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    arthur = Arthur(task_id=task_id, enable_telemetry=False)
    arthur._tracer_provider = provider          # inject real provider
    arthur._api_client._prompts_api = MagicMock()
    arthur._api_client._tasks_api = MagicMock()
    return arthur, exporter
```

Mock a generated-client response:
```python
mock_resp = MagicMock()
mock_resp.model_dump.return_value = prompt_data
arthur._api_client._prompts_api.some_method.return_value = mock_resp
```

`test_install.py` builds the real wheel into a temp venv and runs subprocesses. It also starts an `HTTPServer` on port 0 (OS-assigned) that doubles as both an OTLP collector (`POST /v1/traces`) and a mock OpenAI API (`POST /v1/chat/completions`). These tests run as part of the standard `pytest tests` run.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Generate the API client first (requires Node.js + Java; python/src/arthur_genai_client/ is gitignored)
./scripts/generate_openapi_client.sh generate python

# Install (runs uv sync, which picks up the generated client)
./scripts/generate_openapi_client.sh install python

# Test (run from arthur-observability-sdk/python/)
cd python
uv run pytest tests -v          # all tests (includes install/wheel smoke tests)
uv run pytest tests/test_client.py::test_arthur_requires_task_or_service_name  # single test
uv run pytest -k "telemetry"    # match expression

# Lint (all at once, run from arthur-observability-sdk/)
./scripts/lint.sh

# Individually (run from arthur-observability-sdk/python/)
cd python
uv run black src tests
uv run isort src tests --profile black
uv run autoflake --remove-all-unused-imports --in-place --recursive src tests
uv run mypy src/arthur_observability_sdk

# Build wheel (run from arthur-observability-sdk/)
./scripts/build_sdk_wheel.sh

# Regenerate arthur_genai_client from GenAI Engine OpenAPI spec
./scripts/generate_openapi_client.sh generate python
```

## Architecture

The SDK has three layers:

**`Arthur`** (`arthur.py`) — the user-facing entrypoint. Owns the OTel `TracerProvider`, the API client, and the 32 `instrument_*` methods. At least one of `task_id`, `task_name`, or `service_name` must be provided.

**`setup_telemetry`** (`telemetry.py`) — creates a `TracerProvider` with a `BatchSpanProcessor` backed by an OTLP HTTP exporter. Passes `Authorization: Bearer {api_key}` in the exporter headers. Called by `Arthur.__init__` when `enable_telemetry=True`. Registers the provider globally via `trace.set_tracer_provider()`.

**`ArthurAPIClient`** (`_client.py`) — thin wrapper around the generated `arthur_genai_client`. Exposes `get_prompt_by_version`, `get_prompt_by_tag`, `render_prompt`, `validate_prompt`, `validate_response`, and `resolve_task_id`. All `ApiException`s are converted to `ArthurAPIError(status_code, detail)`.

## Generated Client (`arthur_genai_client`)

This package is auto-generated from `genai-engine/staging.openapi.json` using OpenAPI Generator v7 and is **gitignored** — it is not committed to the repository. It must be generated before running tests or using the SDK locally. **Do not hand-edit it.** Regenerate whenever the GenAI Engine API changes (or after a fresh clone):

```bash
./scripts/generate_openapi_client.sh generate python
```

`ArthurAPIClient` uses `PromptsApi`, `TasksApi`, and `TaskBasedValidationApi`. Two calling styles are acceptable depending on the response shape:

**Use `*_with_http_info()` + `response.raw_data`** when the response contains fields that the generated Pydantic models cannot reliably serialise:
```python
response = self._prompts_api.some_method_with_http_info(...)
return json.loads(response.raw_data)
```

**Use the plain variant and access model attributes directly** when the response fields are simple scalars (strings, ints, bools) with no serialisation concerns:
```python
result = self._tasks_api.some_method(...)
return result.some_field
```

The generated Pydantic models have three known serialisation bugs — avoid `.model_dump()` or `.to_dict()` in either case, but direct attribute access on simple fields is safe:
1. **`anyOf` wrappers** (e.g. `Content`, which represents `str | List[OpenAIMessageItem]`) — `model_dump()` returns internal wrapper fields instead of the actual value.
2. **`datetime` fields** — `model_dump()` returns a `datetime` object, not a JSON-serialisable string.
3. **`Set` fields** — `model_dump()` returns a Python `set`, which `json.dumps` cannot serialise.

Use `*_with_http_info()` + `raw_data` whenever the response includes prompts, messages, or any `anyOf`/datetime/set fields. Use the plain variant only for responses that are purely simple scalars.

## Key Patterns

**Task ID resolution** is lazy: if `task_name` is given instead of `task_id`, the name is resolved to a UUID on the first prompt call via `_api_client.resolve_task_id()` and cached in `_resolved_task_id`.

**PROMPT spans** (`get_prompt`, `render_prompt`) and **GUARDRAIL spans** (`validate_prompt`, `validate_response`) are created manually, not via an instrumentor. Because of this they bypass the OpenInference span processor, so `_apply_openinference_context()` must be called explicitly to copy `session.id`, `user.id`, etc. from the OTel context onto the span.

**`validate_prompt` / `validate_response` span attributes**:
- `openinference.span.kind` → `GUARDRAIL`
- `arthur.task.id` → resolved task UUID
- `arthur.inference.id` → from the API response (`validate_prompt`) or from the caller-supplied parameter (`validate_response`)
- `input.value` → JSON-encoded `{"prompt": ...}` or `{"response": ..., "context": ...}`
- `output.value` → JSON-encoded `ValidationResult` dict

**`render_prompt` span attributes** deliberately distinguish template from result:
- `llm.prompt_template` / `input.value` → original unrendered messages + variable values
- `output.value` → rendered messages with variables substituted

**Framework instrumentation** is all optional. Each `instrument_*` method calls `importlib.import_module()` and raises `ImportError` with the correct `pip install arthur-observability-sdk[{extra}]` hint if the optional dependency is absent.

**`enable_telemetry=False`** skips `TracerProvider` creation entirely — useful when only using prompt management without telemetry.

**Adding a new instrumentor** — four files must be updated together:

1. **`python/src/arthur_observability_sdk/arthur.py`** — add a method after the last `instrument_*` method:
   ```python
   def instrument_my_framework(self) -> Any:
       return self._instrument(
           "openinference-instrumentation-my-framework",  # PyPI package name
           "my-framework",                                 # extras key (used in pip install hint)
           "openinference.instrumentation.my_framework",  # importlib path
           "MyFrameworkInstrumentor",                      # class name
       )
   ```
2. **`python/pyproject.toml`** — two additions:
   - In `[project.optional-dependencies]`: `my-framework = ["openinference-instrumentation-my-framework"]`
   - In the `all` extra list: `"openinference-instrumentation-my-framework"`
3. **`README.md`** — add a row to the "Supported instrumentors" table.

Verify the correct module path and class name from the package's PyPI page before adding.

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

Mock a generated-client response (set `raw_data` to JSON bytes, matching what `*_with_http_info()` returns):
```python
mock_resp = MagicMock()
mock_resp.raw_data = json.dumps(prompt_data).encode()
arthur._api_client._prompts_api.some_method_with_http_info.return_value = mock_resp
```

`test_install.py` builds the real wheel into a temp venv and runs subprocesses. It also starts an `HTTPServer` on port 0 (OS-assigned) that doubles as both an OTLP collector (`POST /v1/traces`) and a mock OpenAI API (`POST /v1/chat/completions`). These tests run as part of the standard `pytest tests` run.

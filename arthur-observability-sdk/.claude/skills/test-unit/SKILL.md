---
name: test-unit
description: Run the arthur-observability-sdk unit tests. Use when you want to verify SDK logic without building a wheel or spinning up external services.
allowed-tools: Bash, Read
---

# Run Unit Tests

Unit tests cover `Arthur` initialization, env-var resolution, prompt management, context helpers, and telemetry setup. They run entirely in-process — no wheel build, no network calls.

## Prerequisites

`python/src/arthur_genai_client/` must exist (it is gitignored). If missing:

```bash
./scripts/generate_openapi_client.sh generate python
./scripts/generate_openapi_client.sh install python
```

## Run all unit tests

From the `arthur-observability-sdk/python/` directory:

```bash
uv run pytest tests -m unit_tests -v
```

## Run a specific test file or test

```bash
uv run pytest tests/test_client.py -v
uv run pytest tests/test_client.py::test_arthur_requires_task_or_service_name -v
```

## Run with keyword filter

```bash
uv run pytest tests -m unit_tests -k "env" -v
```

## Notes

- Unit tests are marked with `@pytest.mark.unit_tests` (via `pytestmark` at the module level).
- They mock at the `OTLPSpanExporter` boundary or use `InMemorySpanExporter` — no real OTLP endpoint needed.
- If tests import `arthur_genai_client` and fail with `ModuleNotFoundError`, the generated client is missing (`python/src/arthur_genai_client/`). Run the generate-client skill first.

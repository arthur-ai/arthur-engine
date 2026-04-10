---
name: test-integration
description: Run the arthur-observability-sdk integration tests. These build the SDK wheel into a fresh venv and verify OTLP telemetry delivery end-to-end. Use when you want to confirm the installable wheel works correctly.
allowed-tools: Bash, Read
---

# Run Integration Tests

Integration tests (`test_install.py`) build the real SDK wheel, install it into a fresh venv, and run subprocesses that confirm:

1. All expected imports succeed from the installed wheel.
2. A real OTLP span is delivered to a mock HTTP collector.
3. OpenAI instrumentation emits a span that reaches the collector.

The wheel build is delegated to `scripts/build_sdk_wheel.sh`, which copies the SDK to a git-free temp directory so uv includes the gitignored `python/src/arthur_genai_client/`.

## Prerequisites

- `python/src/arthur_genai_client/` must exist. If missing, run the generate-client skill first.
- `uv` must be on `PATH`.

## Run all integration tests

From the `arthur-observability-sdk/python/` directory:

```bash
uv run pytest tests -m integration_tests -v
```

## Run a specific integration test

```bash
uv run pytest tests/test_install.py::test_imports_in_fresh_venv -v
uv run pytest tests/test_install.py::test_telemetry_reaches_collector -v
uv run pytest tests/test_install.py::test_openai_instrumentation_sends_span -v
```

## Build the wheel manually (without running tests)

```bash
./scripts/build_sdk_wheel.sh            # → dist/<wheel>.whl
./scripts/build_sdk_wheel.sh /tmp/out   # → /tmp/out/<wheel>.whl
```

## Notes

- Integration tests are marked with `@pytest.mark.integration_tests`.
- The wheel build copies the SDK to a temp dir with no `.git` ancestor so that uv uses filesystem-based file discovery (not `git ls-files`). This ensures the gitignored `python/src/arthur_genai_client/` is included in the wheel.
- These tests are slower than unit tests (~1–2 min) due to the wheel build and venv creation.
- The mock server in the fixture listens on a random free port for both `POST /v1/traces` (OTLP collector) and `POST /v1/chat/completions` (fake OpenAI API).

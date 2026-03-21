# Getting Started with the Arthur Observability SDK

This guide walks through installing and wiring up the Arthur Observability SDK in a Python
application.  After following these steps you will have traces and spans flowing to your
Arthur GenAI Engine instance.

---

## Installation

```bash
pip install arthur-observability-sdk
```

To enable instrumentation for a specific framework install the matching optional extra:

```bash
pip install "arthur-observability-sdk[openai]"      # OpenAI
pip install "arthur-observability-sdk[langchain]"   # LangChain
pip install "arthur-observability-sdk[anthropic]"   # Anthropic
```

---

## Initialising Arthur

Create a single `Arthur` instance at application startup.  At least one of `task_id`,
`task_name`, or `service_name` must be provided.

```python
from arthur_observability_sdk import Arthur

arthur = Arthur(
    api_key="your-api-key",        # or set ARTHUR_API_KEY env var
    task_id="<uuid>",              # Arthur task UUID
    # task_name="my-chatbot",      # alternative: resolved lazily to a UUID
    # service_name="my-service",   # OTel service.name resource attribute
    enable_telemetry=True,         # default True; set False to skip OTel setup
)
```

### Constructor parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str \| None` | `None` | **Required.** Arthur API key. Falls back to `ARTHUR_API_KEY` env var. Raises `ValueError` if neither is set. |
| `base_url` | `str` | `"http://localhost:3030"` | Base URL of the Arthur GenAI Engine. Falls back to `ARTHUR_BASE_URL` env var. |
| `task_id` | `str \| None` | `None` | Arthur task UUID. Used for prompt fetching. |
| `task_name` | `str \| None` | `None` | Task name — resolved lazily to a UUID via the API on the first prompt call. |
| `service_name` | `str \| None` | `None` | OTel `service.name` resource attribute. Defaults to `task_name` or `task_id` when omitted. |
| `resource_attributes` | `dict \| None` | `None` | Additional OTel resource attributes merged into the `TracerProvider`. |
| `enable_telemetry` | `bool` | `True` | When `False`, no `TracerProvider` is created (useful for prompt-only usage). |
| `otlp_endpoint` | `str \| None` | `None` | OTLP HTTP traces endpoint. Defaults to `{base_url}/api/v1/traces`. |

When `enable_telemetry=True` a `BatchSpanProcessor` backed by an OTLP HTTP exporter is
configured and registered as the global `TracerProvider`.  The `api_key` is sent as a
`Authorization: Bearer` header on every OTLP request.

---

## Session context

Tag all spans created within a block with a `session.id` attribute — useful for grouping
all traces from a single conversation or request chain.

### As a context manager

```python
with arthur.session("session-abc-123"):
    response = openai_client.chat.completions.create(...)
```

### As a decorator

```python
@arthur.session("session-abc-123")
def handle_chat_request(messages):
    return openai_client.chat.completions.create(messages=messages, ...)
```

---

## User context

Tag all spans with a `user.id` attribute.

### As a context manager

```python
with arthur.user("user-42"):
    response = openai_client.chat.completions.create(...)
```

### As a decorator

```python
@arthur.user("user-42")
def handle_request(user_id, messages):
    return openai_client.chat.completions.create(messages=messages, ...)
```

---

## Combined session and user context

Use `arthur.attributes()` to set multiple OpenInference attributes at once.

```python
with arthur.attributes(session_id="session-abc-123", user_id="user-42"):
    response = openai_client.chat.completions.create(...)
```

`arthur.attributes()` also works as a decorator and accepts the full set of
OpenInference context attributes: `session_id`, `user_id`, `metadata`, `tags`,
`prompt_template`, `prompt_template_version`, `prompt_template_variables`.

---

## Wiring a framework

Call the relevant `instrument_*` method **once** after constructing `Arthur`.  The
instrumentor patches the framework's HTTP client so that every call is automatically
recorded as an OTel span.

```python
# OpenAI (requires: pip install "arthur-observability-sdk[openai]")
arthur.instrument_openai()

# LangChain (requires: pip install "arthur-observability-sdk[langchain]")
arthur.instrument_langchain()

# Anthropic (requires: pip install "arthur-observability-sdk[anthropic]")
arthur.instrument_anthropic()
```

All 32 supported frameworks follow the same pattern.  If the optional extra is not
installed the method raises `ImportError` with a `pip install` hint.

---

## Shutdown

Call `arthur.shutdown()` before your process exits to flush all pending spans:

```python
arthur.shutdown()
```

`shutdown()` calls `TracerProvider.shutdown()` (which flushes the `BatchSpanProcessor`)
and closes the underlying API client connection pool.

---

## Minimal end-to-end example

```python
import openai
from arthur_observability_sdk import Arthur

arthur = Arthur(
    api_key="your-api-key",
    task_id="<your-task-uuid>",
    service_name="my-chatbot",
)
arthur.instrument_openai()

client = openai.OpenAI()

with arthur.attributes(session_id="sess-1", user_id="user-99"):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(response.choices[0].message.content)

arthur.shutdown()
```

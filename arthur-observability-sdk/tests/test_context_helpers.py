"""Tests for Arthur.session(), Arthur.user(), Arthur.attributes()."""

from unittest.mock import MagicMock

import pytest
from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace
from opentelemetry.context import get_value
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from arthur_observability_sdk import Arthur, using_attributes, using_session, using_user

pytestmark = pytest.mark.unit_tests

TASK_ID = "task-uuid-ctx-test"


def _make_arthur() -> Arthur:
    return Arthur(task_id=TASK_ID, api_key="test-key", enable_telemetry=False)


# ---------------------------------------------------------------------------
# Package-level re-exports
# ---------------------------------------------------------------------------


def test_module_exports_using_session():
    assert callable(using_session)


def test_module_exports_using_user():
    assert callable(using_user)


def test_module_exports_using_attributes():
    assert callable(using_attributes)


# ---------------------------------------------------------------------------
# Return-value protocol: context manager + decorator
# ---------------------------------------------------------------------------


def test_session_returns_context_manager():
    arthur = _make_arthur()
    cm = arthur.session("s1")
    assert hasattr(cm, "__enter__") and hasattr(cm, "__exit__")
    arthur.shutdown()


def test_user_returns_context_manager():
    arthur = _make_arthur()
    cm = arthur.user("u1")
    assert hasattr(cm, "__enter__") and hasattr(cm, "__exit__")
    arthur.shutdown()


def test_attributes_returns_context_manager():
    arthur = _make_arthur()
    cm = arthur.attributes(session_id="s1", user_id="u1")
    assert hasattr(cm, "__enter__") and hasattr(cm, "__exit__")
    arthur.shutdown()


def test_session_is_also_a_decorator():
    arthur = _make_arthur()
    # ContextDecorator subclass: the instance itself is callable as a wrapper
    cm = arthur.session("s1")
    assert callable(cm)
    arthur.shutdown()


def test_user_is_also_a_decorator():
    arthur = _make_arthur()
    assert callable(arthur.user("u1"))
    arthur.shutdown()


def test_attributes_is_also_a_decorator():
    arthur = _make_arthur()
    assert callable(arthur.attributes(session_id="s1"))
    arthur.shutdown()


# ---------------------------------------------------------------------------
# Context manager: enters and exits cleanly
# ---------------------------------------------------------------------------


def test_session_context_manager_runs_body():
    arthur = _make_arthur()
    ran = False
    with arthur.session("session-abc"):
        ran = True
    assert ran
    arthur.shutdown()


def test_user_context_manager_runs_body():
    arthur = _make_arthur()
    ran = False
    with arthur.user("user-99"):
        ran = True
    assert ran
    arthur.shutdown()


def test_attributes_context_manager_runs_body():
    arthur = _make_arthur()
    ran = False
    with arthur.attributes(session_id="s1", user_id="u1"):
        ran = True
    assert ran
    arthur.shutdown()


# ---------------------------------------------------------------------------
# Decorator: wraps and calls the function
# ---------------------------------------------------------------------------


def test_session_as_decorator():
    arthur = _make_arthur()
    calls = []

    @arthur.session("session-xyz")
    def my_func():
        calls.append(1)

    my_func()
    assert calls == [1]
    arthur.shutdown()


def test_user_as_decorator():
    arthur = _make_arthur()
    calls = []

    @arthur.user("user-xyz")
    def my_func():
        calls.append(1)

    my_func()
    assert calls == [1]
    arthur.shutdown()


def test_attributes_as_decorator():
    arthur = _make_arthur()
    calls = []

    @arthur.attributes(session_id="s1", user_id="u1")
    def my_func():
        calls.append(1)

    my_func()
    assert calls == [1]
    arthur.shutdown()


# ---------------------------------------------------------------------------
# OTel context propagation
# The helpers use opentelemetry.context.set_value so that OpenInference
# instrumentors can read the values when creating spans.  We verify the
# values are present in context while inside the block and absent outside.
# ---------------------------------------------------------------------------


def test_session_sets_context_value():
    arthur = _make_arthur()
    with arthur.session("ctx-session-id"):
        assert get_value(SpanAttributes.SESSION_ID) == "ctx-session-id"
    # Cleaned up after exit
    assert get_value(SpanAttributes.SESSION_ID) is None
    arthur.shutdown()


def test_user_sets_context_value():
    arthur = _make_arthur()
    with arthur.user("ctx-user-id"):
        assert get_value(SpanAttributes.USER_ID) == "ctx-user-id"
    assert get_value(SpanAttributes.USER_ID) is None
    arthur.shutdown()


def test_attributes_sets_session_and_user_context_values():
    arthur = _make_arthur()
    with arthur.attributes(session_id="attr-session", user_id="attr-user"):
        assert get_value(SpanAttributes.SESSION_ID) == "attr-session"
        assert get_value(SpanAttributes.USER_ID) == "attr-user"
    assert get_value(SpanAttributes.SESSION_ID) is None
    assert get_value(SpanAttributes.USER_ID) is None
    arthur.shutdown()


def test_context_values_not_leaked_between_blocks():
    arthur = _make_arthur()
    with arthur.session("block-a"):
        assert get_value(SpanAttributes.SESSION_ID) == "block-a"

    with arthur.session("block-b"):
        assert get_value(SpanAttributes.SESSION_ID) == "block-b"

    assert get_value(SpanAttributes.SESSION_ID) is None
    arthur.shutdown()


def test_decorator_sets_context_value_during_call():
    arthur = _make_arthur()
    observed = []

    @arthur.session("decorator-session")
    def my_func():
        observed.append(get_value(SpanAttributes.SESSION_ID))

    my_func()
    assert observed == ["decorator-session"]
    arthur.shutdown()


# ---------------------------------------------------------------------------
# PROMPT span attribute propagation
# Verify that session.id / user.id set via arthur.attributes() are written
# onto PROMPT spans (get_prompt / render_prompt), which create spans manually
# and therefore need to copy values from the OTel context themselves.
# ---------------------------------------------------------------------------

_MOCK_PROMPT = {
    "name": "TestPrompt",
    "messages": [{"role": "user", "content": "Hello {{ topic }}"}],
    "model_name": "gpt-4o",
    "model_provider": "openai",
    "version": 2,
    "variables": ["topic"],
    "tags": ["latest"],
    "config": None,
    "created_at": "2025-01-01T00:00:00",
    "deleted_at": None,
}

_RENDERED_PROMPT = {**_MOCK_PROMPT, "messages": [{"role": "user", "content": "Hello AI"}]}


def _make_arthur_with_spans():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    arthur = Arthur(task_id=TASK_ID, api_key="test-key", enable_telemetry=False)
    arthur._tracer_provider = provider
    arthur._api_client._prompts_api = MagicMock()
    arthur._api_client._tasks_api = MagicMock()
    return arthur, exporter


def _mock_response(data: dict):
    m = MagicMock()
    m.model_dump.return_value = data
    return m


def test_get_prompt_span_includes_session_id():
    arthur, exporter = _make_arthur_with_spans()
    arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get.return_value = _mock_response(
        _MOCK_PROMPT,
    )

    with arthur.attributes(session_id="span-session", user_id="span-user"):
        arthur.get_prompt("TestPrompt")

    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs.get(SpanAttributes.SESSION_ID) == "span-session"
    assert attrs.get(SpanAttributes.USER_ID) == "span-user"
    arthur.shutdown()


def test_render_prompt_span_includes_session_id():
    arthur, exporter = _make_arthur_with_spans()
    api = arthur._api_client._prompts_api
    api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get.return_value = _mock_response(
        _MOCK_PROMPT,
    )
    api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post.return_value = _mock_response(
        _RENDERED_PROMPT,
    )

    with arthur.attributes(session_id="render-session", user_id="render-user"):
        arthur.render_prompt("TestPrompt", variables={"topic": "AI"})

    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs.get(SpanAttributes.SESSION_ID) == "render-session"
    assert attrs.get(SpanAttributes.USER_ID) == "render-user"
    arthur.shutdown()


def test_prompt_span_has_no_session_when_no_context():
    arthur, exporter = _make_arthur_with_spans()
    arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get.return_value = _mock_response(
        _MOCK_PROMPT,
    )

    arthur.get_prompt("TestPrompt")

    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert SpanAttributes.SESSION_ID not in attrs
    assert SpanAttributes.USER_ID not in attrs
    arthur.shutdown()

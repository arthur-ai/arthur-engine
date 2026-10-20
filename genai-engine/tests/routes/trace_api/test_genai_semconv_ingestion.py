"""Ingesting spans in the OpenTelemetry GenAI conventions (gen_ai.*), shaped like
the Claude Platform's OpenTelemetry export, and its delivery details: gzip
bodies and the x-arthur-task header."""

import gzip
import os
from datetime import datetime, timedelta

import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Span

from db_models import DatabaseSpan
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


def _kv(key, value):
    if isinstance(value, int):
        return KeyValue(key=key, value=AnyValue(int_value=value))
    return KeyValue(key=key, value=AnyValue(string_value=value))


def _span(name, attrs, kind=Span.SPAN_KIND_INTERNAL, trace_id=None, parent=None):
    span = Span()
    span.trace_id = trace_id or os.urandom(16)
    span.span_id = os.urandom(8)
    if parent is not None:
        span.parent_span_id = parent.span_id
    span.name = name
    span.kind = kind
    span.start_time_unix_nano = int(datetime.now().timestamp() * 1e9)
    span.end_time_unix_nano = int(
        (datetime.now() + timedelta(seconds=1)).timestamp() * 1e9,
    )
    span.attributes.extend(_kv(k, v) for k, v in attrs.items())
    return span


def _request(spans, resource_attrs):
    trace_request = ExportTraceServiceRequest()
    resource_span = trace_request.resource_spans.add()
    resource_span.resource.attributes.extend(
        _kv(k, v) for k, v in resource_attrs.items()
    )
    scope_span = resource_span.scope_spans.add()
    scope_span.scope.name = "com.anthropic.claude-platform"
    scope_span.spans.extend(spans)
    return trace_request.SerializeToString()


USAGE = {
    "gen_ai.request.model": "claude-sonnet-4-5",
    "gen_ai.response.model": "claude-sonnet-4-5",
    "gen_ai.usage.input_tokens": 36936,
    "gen_ai.usage.output_tokens": 2330,
    "gen_ai.usage.cache_read.input_tokens": 30000,
    "gen_ai.usage.cache_write.input_tokens": 1000,
}


def _claude_platform_request(session_id="sesn_test"):
    """One Messages API request as the API exports it: the request span (SERVER),
    one model request with the same usage, and a server tool use."""
    trace_id = os.urandom(16)
    request = _span(
        "anthropic.messages.create",
        {"gen_ai.operation.name": "chat", "gen_ai.provider.name": "anthropic", **USAGE},
        kind=Span.SPAN_KIND_SERVER,
        trace_id=trace_id,
    )
    model_request = _span(
        "anthropic.model_request",
        {**USAGE, "anthropic.session.id": session_id},
        trace_id=trace_id,
        parent=request,
    )
    tool = _span(
        "anthropic.tool_use web_search",
        {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "web_search"},
        trace_id=trace_id,
        parent=request,
    )
    return [request, model_request, tool]


def _post(client, body, **headers):
    all_headers = client.authorized_user_api_key_headers.copy()
    all_headers["Content-Type"] = "application/x-protobuf"
    all_headers.update(headers)
    return client.base_client.post("/api/v1/traces", content=body, headers=all_headers)


def _spans_for(task_id):
    db_session = override_get_db_session()
    return {
        s.span_name: s
        for s in db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.task_id == task_id)
        .all()
    }


@pytest.mark.unit_tests
def test_claude_platform_spans_get_kind_tokens_cost_and_session(
    client: GenaiEngineTestClientBase,
):
    task_id = f"claude_platform_{os.urandom(4).hex()}"
    body = _request(_claude_platform_request(), {"service.name": "claude-platform"})

    resp = _post(client, body, **{"x-arthur-task": task_id})

    assert resp.status_code == 200, resp.text
    spans = _spans_for(task_id)
    assert set(spans) == {
        "anthropic.messages.create",
        "anthropic.model_request",
        "anthropic.tool_use web_search",
    }

    # Usage is on the request span and on its model request; only the model
    # request is LLM, so it is priced once.
    model_request = spans["anthropic.model_request"]
    assert model_request.span_kind == "LLM"
    assert model_request.prompt_token_count == 36936
    assert model_request.completion_token_count == 2330
    assert model_request.total_token_cost and model_request.total_token_cost > 0
    assert model_request.session_id == "sesn_test"
    assert (
        model_request.raw_data["attributes"]["llm"]["token_count"]["prompt_details"][
            "cache_read"
        ]
        == 30000
    )

    request = spans["anthropic.messages.create"]
    assert request.span_kind == "CHAIN"
    assert request.total_token_cost is None

    assert spans["anthropic.tool_use web_search"].span_kind == "TOOL"


@pytest.mark.unit_tests
def test_sdk_request_span_is_priced(client: GenaiEngineTestClientBase):
    """Without API tracing, the SDK's request span (CLIENT) is the only usage."""
    task_id = f"claude_sdk_{os.urandom(4).hex()}"
    span = _span(
        "anthropic.messages.create",
        {"gen_ai.operation.name": "chat", **USAGE, "gen_ai.conversation.id": "conv_1"},
        kind=Span.SPAN_KIND_CLIENT,
    )
    body = _request([span], {"service.name": "my-app", "arthur.task": task_id})

    assert _post(client, body).status_code == 200

    stored = _spans_for(task_id)["anthropic.messages.create"]
    assert stored.span_kind == "LLM"
    assert stored.prompt_token_count == 36936
    assert stored.session_id == "conv_1"


@pytest.mark.unit_tests
def test_gzip_body_is_accepted(client: GenaiEngineTestClientBase):
    task_id = f"claude_gzip_{os.urandom(4).hex()}"
    body = _request(_claude_platform_request(), {"service.name": "claude-platform"})

    resp = _post(
        client,
        gzip.compress(body),
        **{"Content-Encoding": "gzip", "x-arthur-task": task_id},
    )

    assert resp.status_code == 200, resp.text
    assert len(_spans_for(task_id)) == 3


@pytest.mark.unit_tests
def test_unsupported_encoding_is_415_and_bad_gzip_is_400(
    client: GenaiEngineTestClientBase,
):
    body = _request(_claude_platform_request(), {"service.name": "claude-platform"})

    # 415 tells an OTLP exporter to resend the body uncompressed.
    assert _post(client, body, **{"Content-Encoding": "br"}).status_code == 415
    assert _post(client, b"not gzip", **{"Content-Encoding": "gzip"}).status_code == 400


@pytest.mark.unit_tests
def test_resource_arthur_task_wins_over_header(client: GenaiEngineTestClientBase):
    resource_task = f"resource_task_{os.urandom(4).hex()}"
    header_task = f"header_task_{os.urandom(4).hex()}"
    body = _request(
        _claude_platform_request(),
        {"service.name": "claude-platform", "arthur.task": resource_task},
    )

    assert _post(client, body, **{"x-arthur-task": header_task}).status_code == 200

    assert len(_spans_for(resource_task)) == 3
    assert _spans_for(header_task) == {}


@pytest.mark.unit_tests
def test_openinference_span_with_genai_keys_is_unchanged(
    client: GenaiEngineTestClientBase,
):
    """A span that sets openinference.span.kind keeps it, even with gen_ai.* keys."""
    task_id = f"openinference_{os.urandom(4).hex()}"
    span = _span(
        "ChatCompletion",
        {
            "openinference.span.kind": "LLM",
            "llm.model_name": "gpt-4o",
            "llm.token_count.prompt": 10,
            "llm.token_count.completion": 5,
            "gen_ai.usage.input_tokens": 999,
        },
    )
    body = _request([span], {"service.name": "app", "arthur.task": task_id})

    assert _post(client, body).status_code == 200

    stored = _spans_for(task_id)["ChatCompletion"]
    assert stored.span_kind == "LLM"
    assert stored.prompt_token_count == 10
    assert stored.raw_data["attributes"]["gen_ai"]["usage"]["input_tokens"] == 999

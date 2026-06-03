import json
from unittest.mock import MagicMock

import pytest
from arthur_common.models.llm_model_providers import (
    LLMTool,
    MessageRole,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
    ToolFunction,
)
from openinference.semconv.trace import (
    MessageAttributes,
    SpanAttributes,
    ToolAttributes,
    ToolCallAttributes,
)

from services.trace.internal_trace_service import InternalTraceService


def make_service() -> InternalTraceService:
    # The message-serialization methods don't touch the db_session; a mock is
    # enough to construct the service.
    return InternalTraceService(
        db_session=MagicMock(),
        task_id="task-123",
        service_name="test",
    )


def _attrs(span) -> dict:
    """Flatten a span's KeyValue attributes into a {key: value} dict."""
    out = {}
    for kv in span.attributes:
        v = kv.value
        out[kv.key] = v.string_value if v.HasField("string_value") else v.int_value
    return out


@pytest.mark.unit_tests
def test_input_messages_record_assistant_tool_calls():
    """Regression: assistant messages that only issue tool calls (content=None)
    must record their tool_calls on the span, not just the role.

    Previously set_llm_input_messages emitted only MESSAGE_ROLE for such
    messages, so the span showed a bare {"role": "assistant"}.
    """
    service = make_service()
    span = service.start_agent_span(name="agent", agent_name="chatbot")

    messages = [
        OpenAIMessage(role=MessageRole.SYSTEM, content="be concise"),
        OpenAIMessage(role=MessageRole.USER, content="what is an integral?"),
        # Assistant tool-call turn: no content, only tool calls.
        OpenAIMessage(
            role=MessageRole.AI,
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_1",
                    function=ToolCallFunction(
                        name="wikipedia_search",
                        arguments='{"query": "integral"}',
                    ),
                ),
            ],
        ),
        OpenAIMessage(
            role=MessageRole.TOOL,
            content="Integral calculus",
            tool_call_id="call_1",
        ),
    ]

    service.set_llm_input_messages(span, messages)
    attrs = _attrs(span)

    # The assistant message is index 2 in the input list.
    tc_prefix = (
        f"{SpanAttributes.LLM_INPUT_MESSAGES}.2."
        f"{MessageAttributes.MESSAGE_TOOL_CALLS}.0"
    )
    assert (
        attrs[f"{tc_prefix}.{ToolCallAttributes.TOOL_CALL_FUNCTION_NAME}"]
        == "wikipedia_search"
    )
    assert (
        attrs[f"{tc_prefix}.{ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON}"]
        == '{"query": "integral"}'
    )

    # The role is still recorded.
    assert (
        attrs[f"{SpanAttributes.LLM_INPUT_MESSAGES}.2.{MessageAttributes.MESSAGE_ROLE}"]
        == "assistant"
    )

    # The JSON blob also carries the assistant tool call rather than dropping
    # the message for having no content.
    blob = json.loads(attrs[SpanAttributes.INPUT_VALUE])
    assistant_parts = [m for m in blob["messages"] if m["role"] == "assistant"]
    assert len(assistant_parts) == 1
    assert assistant_parts[0]["tool_calls"][0]["function"] == {
        "name": "wikipedia_search",
        "arguments": '{"query": "integral"}',
    }


@pytest.mark.unit_tests
def test_input_messages_record_content_for_plain_messages():
    """System/user/tool messages with content still serialize correctly."""
    service = make_service()
    span = service.start_agent_span(name="agent", agent_name="chatbot")

    messages = [
        OpenAIMessage(role=MessageRole.USER, content="hello"),
    ]
    service.set_llm_input_messages(span, messages)
    attrs = _attrs(span)

    assert (
        attrs[
            f"{SpanAttributes.LLM_INPUT_MESSAGES}.0.{MessageAttributes.MESSAGE_CONTENT}"
        ]
        == "hello"
    )
    blob = json.loads(attrs[SpanAttributes.INPUT_VALUE])
    assert blob["messages"] == [{"role": "user", "content": "hello"}]


@pytest.mark.unit_tests
def test_set_llm_tools_records_json_schema_per_tool():
    """The tools available to the LLM are recorded under llm.tools.{i} as
    OpenInference tool.json_schema values."""
    service = make_service()
    span = service.start_agent_span(name="agent", agent_name="chatbot")

    tools = [
        LLMTool(
            function=ToolFunction(
                name="wikipedia_search",
                description="Search Wikipedia",
                parameters={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            ),
        ),
        LLMTool(
            function=ToolFunction(
                name="wikipedia_fetch",
                description="Fetch an article",
            ),
        ),
    ]
    service.set_llm_tools(span, tools)
    attrs = _attrs(span)

    schema_0 = json.loads(
        attrs[f"{SpanAttributes.LLM_TOOLS}.0.{ToolAttributes.TOOL_JSON_SCHEMA}"],
    )
    assert schema_0["type"] == "function"
    assert schema_0["function"]["name"] == "wikipedia_search"
    assert schema_0["function"]["parameters"]["properties"] == {
        "query": {"type": "string"},
    }

    schema_1 = json.loads(
        attrs[f"{SpanAttributes.LLM_TOOLS}.1.{ToolAttributes.TOOL_JSON_SCHEMA}"],
    )
    assert schema_1["function"]["name"] == "wikipedia_fetch"
    # exclude_none drops the unset parameters field.
    assert "parameters" not in schema_1["function"]


@pytest.mark.unit_tests
def test_set_llm_tools_no_tools_is_noop():
    """No tools (None or empty) records nothing."""
    service = make_service()
    span = service.start_agent_span(name="agent", agent_name="chatbot")

    service.set_llm_tools(span, None)
    service.set_llm_tools(span, [])
    attrs = _attrs(span)

    assert not any(k.startswith(SpanAttributes.LLM_TOOLS) for k in attrs)

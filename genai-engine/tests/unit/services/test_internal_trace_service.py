import hashlib
import json
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.common_schemas import KeywordsConfig
from arthur_common.models.enums import RuleResultEnum, RuleScope, RuleType
from arthur_common.models.llm_model_providers import (
    LLMTool,
    MessageRole,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
    ToolFunction,
)
from arthur_common.models.request_schemas import NewRuleRequest
from arthur_common.models.response_schemas import (
    BaseDetailsResponse,
    ExternalRuleResult,
)
from openinference.semconv.trace import (
    MessageAttributes,
    SpanAttributes,
    ToolAttributes,
    ToolCallAttributes,
)

from schemas.guardrail_span_schemas import GuardrailSpanResult
from schemas.internal_schemas import Rule, RuleEngineResult
from schemas.scorer_schemas import RuleScore
from services.trace import guardrail_span_emitter as emitter
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


# ---------------------------------------------------------------------------
# Guardrail span emission: start_guardrail_span, GuardrailSpanResult synthesis,
# and the guardrail_span context-manager lifecycle/placement (stateful validate flow).
# ---------------------------------------------------------------------------

INF = "inference-abc"


def _rule(
    result: RuleResultEnum = RuleResultEnum.PASS,
    *,
    name: str = "rule",
    message: str | None = None,
    with_details: bool = True,
) -> ExternalRuleResult:
    details = BaseDetailsResponse(message=message) if with_details else None
    return ExternalRuleResult(
        id=f"id-{name}",
        name=name,
        rule_type=RuleType.TOXICITY,
        scope=RuleScope.DEFAULT,
        result=result,
        latency_ms=1,
        details=details,
    )


def _engine_result(result: RuleResultEnum = RuleResultEnum.PASS) -> RuleEngineResult:
    """Raw rule-engine result, as the validate flow hands to set_rule_results."""
    rule = Rule._from_request_model(
        NewRuleRequest(
            name="keywords",
            type="KeywordRule",
            apply_to_prompt=True,
            apply_to_response=True,
            config=KeywordsConfig(keywords=["x"]),
        ),
        RuleScope.DEFAULT,
    )
    return RuleEngineResult(
        rule_score_result=RuleScore(
            result=result,
            prompt_tokens=1,
            completion_tokens=1,
        ),
        rule=rule,
        latency_ms=1,
    )


def _derive_trace(inf: str) -> bytes:
    return hashlib.sha256(inf.encode()).digest()[:16]


def _derive_span(inf: str, stage: str) -> bytes:
    return hashlib.sha256(f"{stage}:{inf}".encode()).digest()[:8]


@pytest.mark.unit_tests
def test_start_guardrail_span_sets_kind_ids_and_metadata():
    tid = b"\x09" * 16
    parent, own = b"\x01" * 8, b"\x02" * 8
    svc = InternalTraceService(
        db_session=MagicMock(),
        task_id="t",
        service_name="guardrail_validate",
        trace_id=tid,
    )
    span = svc.start_guardrail_span(
        name="guardrail.validate_prompt",
        parent_span_id=parent,
        span_id=own,
        user_id="u1",
        session_id="c1",
    )
    attrs = _attrs(span)
    assert attrs[SpanAttributes.OPENINFERENCE_SPAN_KIND] == "GUARDRAIL"
    assert attrs[SpanAttributes.USER_ID] == "u1"
    assert attrs[SpanAttributes.SESSION_ID] == "c1"
    assert (span.trace_id, span.span_id, span.parent_span_id) == (tid, own, parent)


@pytest.mark.unit_tests
def test_guardrail_span_result_pass_is_not_blocked():
    result = GuardrailSpanResult.from_validation("inf", [_rule(RuleResultEnum.PASS)])
    assert result.blocked is False
    assert result.blocked_reason is None


@pytest.mark.unit_tests
def test_guardrail_span_result_blocks_and_synthesizes_reason():
    rr = [
        _rule(RuleResultEnum.FAIL, name="tox", message="toxic content"),
        _rule(RuleResultEnum.FAIL, name="pii", with_details=False),
        _rule(RuleResultEnum.PASS, name="ok"),
    ]
    result = GuardrailSpanResult.from_validation("inf", rr)
    assert result.blocked is True
    # failed rule's message, then a fallback to the rule name when no message.
    assert result.blocked_reason == "toxic content; pii failed"


@pytest.mark.unit_tests
def test_guardrail_span_result_non_fail_states_do_not_block():
    rr = [
        _rule(RuleResultEnum.SKIPPED, name="s"),
        _rule(RuleResultEnum.UNAVAILABLE, name="u"),
        _rule(RuleResultEnum.MODEL_NOT_AVAILABLE, name="m"),
    ]
    result = GuardrailSpanResult.from_validation("inf", rr)
    assert result.blocked is False
    assert result.blocked_reason is None


@pytest.fixture
def mock_emitter_service():
    with patch.object(emitter, "InternalTraceService") as m:
        m.return_value.start_guardrail_span.return_value = MagicMock()
        yield m, m.return_value


def _run_guardrail_span(*, rule_results=None, raise_exc=None, **overrides):
    """Drive guardrail_span the way the validate flow does; returns the recorder
    so tests can call persist() (done after the save commits in the real flow)."""
    kwargs = dict(
        enabled=True,
        task_id="task-1",
        inference_id=INF,
        input_payload={"prompt": "hi"},
        is_response=False,
    )
    kwargs.update(overrides)
    with emitter.guardrail_span(MagicMock(), **kwargs) as gspan:
        if raise_exc is not None:
            raise raise_exc
        gspan.set_rule_results(
            rule_results if rule_results is not None else [_engine_result()],
        )
    return gspan


@pytest.mark.unit_tests
def test_span_starts_before_results_and_ends_on_success(mock_emitter_service):
    m, inst = mock_emitter_service
    gspan = _run_guardrail_span(is_response=False)
    # Span + input are set up at entry (timing starts before evaluation runs).
    inst.start_guardrail_span.assert_called_once()
    inst.set_input_json.assert_called_once()
    assert m.call_args.kwargs["trace_id"] == _derive_trace(INF)
    sg = inst.start_guardrail_span.call_args.kwargs
    assert sg["span_id"] == _derive_span(INF, "prompt")
    assert sg["parent_span_id"] is None
    assert sg["name"] == "guardrail.validate_prompt"
    # Output written and span ended, but nothing stored until persist().
    inst.set_output_json.assert_called_once()
    inst.end_span.assert_called_once()
    inst.end_span_with_error.assert_not_called()
    inst.flush.assert_not_called()
    gspan.persist()
    inst.flush.assert_called_once()


@pytest.mark.unit_tests
def test_flush_deferred_until_persist(mock_emitter_service):
    # No flush at with-exit; a failed save (no persist() call) leaves no span.
    _, inst = mock_emitter_service
    gspan = _run_guardrail_span()
    inst.flush.assert_not_called()
    gspan.persist()
    inst.flush.assert_called_once()


@pytest.mark.unit_tests
def test_response_span_nests_under_prompt_in_derived_trace(mock_emitter_service):
    m, inst = mock_emitter_service
    _run_guardrail_span(is_response=True, input_payload={"response": "r"})
    assert m.call_args.kwargs["trace_id"] == _derive_trace(INF)
    sg = inst.start_guardrail_span.call_args.kwargs
    assert sg["span_id"] == _derive_span(INF, "response")
    assert sg["parent_span_id"] == _derive_span(INF, "prompt")
    assert sg["name"] == "guardrail.validate_response"


@pytest.mark.unit_tests
def test_span_records_error_status_and_propagates(mock_emitter_service):
    _, inst = mock_emitter_service
    with pytest.raises(RuntimeError, match="evaluate blew up"):
        _run_guardrail_span(raise_exc=RuntimeError("evaluate blew up"))
    # Error span flushed immediately (no save will follow); no success-path end.
    inst.end_span_with_error.assert_called_once()
    assert inst.end_span_with_error.call_args.args[1] == "evaluate blew up"
    inst.end_span.assert_not_called()
    inst.flush.assert_called_once()


@pytest.mark.unit_tests
def test_span_honors_supplied_trace_and_parent(mock_emitter_service):
    m, inst = mock_emitter_service
    _run_guardrail_span(trace_id="ab" * 16, parent_span_id="cd" * 8)
    assert m.call_args.kwargs["trace_id"] == bytes.fromhex("ab" * 16)
    assert inst.start_guardrail_span.call_args.kwargs[
        "parent_span_id"
    ] == bytes.fromhex("cd" * 8)


@pytest.mark.unit_tests
def test_span_supplied_trace_only_is_top_level(mock_emitter_service):
    m, inst = mock_emitter_service
    _run_guardrail_span(trace_id="ab" * 16)
    assert m.call_args.kwargs["trace_id"] == bytes.fromhex("ab" * 16)
    assert inst.start_guardrail_span.call_args.kwargs["parent_span_id"] is None


@pytest.mark.unit_tests
def test_span_falls_back_to_derived_on_bad_caller_ids(mock_emitter_service):
    m, _ = mock_emitter_service
    _run_guardrail_span(trace_id="not-hex")  # malformed hex
    assert m.call_args.kwargs["trace_id"] == _derive_trace(INF)
    m.reset_mock()
    _run_guardrail_span(trace_id="abcd")  # valid hex, wrong byte length
    assert m.call_args.kwargs["trace_id"] == _derive_trace(INF)


@pytest.mark.unit_tests
def test_span_keeps_valid_trace_when_only_parent_is_malformed(mock_emitter_service):
    # A bad parent_span_id must not throw away an otherwise-valid trace_id; the
    # span stays in the caller's trace, just placed at the top level.
    m, inst = mock_emitter_service
    _run_guardrail_span(trace_id="ab" * 16, parent_span_id="not-hex")
    assert m.call_args.kwargs["trace_id"] == bytes.fromhex("ab" * 16)
    assert inst.start_guardrail_span.call_args.kwargs["parent_span_id"] is None


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "overrides",
    [{"enabled": False}, {"task_id": None}, {"inference_id": None}],
)
def test_span_is_noop_when_disabled_or_unanchored(mock_emitter_service, overrides):
    m, _ = mock_emitter_service
    _run_guardrail_span(**overrides)
    m.assert_not_called()


@pytest.mark.unit_tests
def test_span_skips_persist_when_no_results(mock_emitter_service):
    _, inst = mock_emitter_service
    gspan = _run_guardrail_span(rule_results=[])
    # No results: the span is discarded and persist() cannot resurrect it.
    inst.end_span.assert_not_called()
    gspan.persist()
    inst.flush.assert_not_called()


@pytest.mark.unit_tests
def test_span_swallows_persist_failures(mock_emitter_service):
    _, inst = mock_emitter_service
    inst.flush.side_effect = RuntimeError("boom")
    gspan = _run_guardrail_span()
    gspan.persist()  # must not raise


@pytest.mark.unit_tests
def test_span_discarded_when_finish_fails(mock_emitter_service):
    # A payload-build failure discards the span; a half-built span is never flushed.
    _, inst = mock_emitter_service
    inst.set_output_json.side_effect = RuntimeError("boom")
    gspan = _run_guardrail_span()  # must not raise
    gspan.persist()
    inst.flush.assert_not_called()


@pytest.mark.unit_tests
def test_flush_failure_rolls_back_session():
    # A failed ingestion commit must not poison the shared session.
    db_session = MagicMock()
    svc = InternalTraceService(
        db_session=db_session,
        task_id="t",
        service_name="guardrail_validate",
    )
    span = svc.start_guardrail_span(name="guardrail.validate_prompt")
    svc.end_span(span)
    with patch(
        "services.trace.internal_trace_service.TraceIngestionService",
    ) as ingestion:
        ingestion.return_value.process_trace_data.side_effect = RuntimeError("boom")
        svc.flush()  # must not raise
    db_session.rollback.assert_called_once()

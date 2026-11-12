"""How a span-scope eval picks spans and turns span verdicts into a trace verdict."""

from dataclasses import dataclass
from typing import Any, Optional

import pytest
from arthur_common.models.enums import ContinuousEvalRunStatus

from schemas.common_schemas import ContinuousEvalSpanFilter
from schemas.enums import ContinuousEvalRollupRule
from services.continuous_eval.span_scope import (
    SpanVerdict,
    decide_rollup,
    select_spans,
)

PASSED = ContinuousEvalRunStatus.PASSED
FAILED = ContinuousEvalRunStatus.FAILED
ERROR = ContinuousEvalRunStatus.ERROR
SKIPPED = ContinuousEvalRunStatus.SKIPPED
PENDING = ContinuousEvalRunStatus.PENDING
ANY_FAIL = ContinuousEvalRollupRule.ANY_FAIL
FINAL_ATTEMPT = ContinuousEvalRollupRule.FINAL_ATTEMPT


def _v(span_id, status, name="lookup_order", parent="agent", label=None):
    return SpanVerdict(
        span_id=span_id,
        parent_span_id=parent,
        span_name=name,
        status=status,
        label=label,
    )


# The retry case: the first lookup_order call errors, the second succeeds, and a
# span judge marks the first one failed.
RETRY = [_v("call-1", FAILED, label="tool_error"), _v("call-2", PASSED)]


@pytest.mark.unit_tests
def test_final_attempt_lets_a_successful_retry_pass_the_trace():
    decision = decide_rollup(RETRY, FINAL_ATTEMPT)
    assert decision.status == PASSED
    assert decision.score == 1
    assert decision.label is None
    assert "later attempts overrule failed span call-1" in decision.description


@pytest.mark.unit_tests
def test_any_fail_fails_the_trace_on_the_first_failing_span():
    decision = decide_rollup(RETRY, ANY_FAIL)
    assert decision.status == FAILED
    assert decision.score == 0
    assert decision.label == "tool_error"
    assert decision.description.startswith("Failed on span call-1 (tool_error).")


@pytest.mark.unit_tests
def test_final_attempt_still_fails_when_the_last_attempt_fails():
    verdicts = [
        _v("call-1", PASSED),
        _v("call-2", FAILED, label="wrong_args"),
        _v("refund-1", PASSED, name="refund_order"),
    ]
    decision = decide_rollup(verdicts, FINAL_ATTEMPT)
    assert (decision.status, decision.label) == (FAILED, "wrong_args")


@pytest.mark.unit_tests
def test_final_attempt_groups_by_parent_as_well_as_name():
    """Same tool name in two different turns: each turn's last call decides."""
    verdicts = [
        _v("t1-call", FAILED, parent="turn-1", label="tool_error"),
        _v("t2-call", PASSED, parent="turn-2"),
    ]
    decision = decide_rollup(verdicts, FINAL_ATTEMPT)
    assert (decision.status, decision.label) == (FAILED, "tool_error")


@pytest.mark.unit_tests
def test_no_decision_while_a_span_run_is_unfinished():
    assert (
        decide_rollup([_v("call-1", PASSED), _v("call-2", PENDING)], ANY_FAIL) is None
    )


@pytest.mark.unit_tests
def test_errors_and_skips_without_a_failure():
    errored = decide_rollup([_v("a", PASSED), _v("b", ERROR, name="x")], ANY_FAIL)
    assert errored.status == ERROR
    assert "b" in errored.description
    skipped = decide_rollup([_v("a", SKIPPED)], ANY_FAIL)
    assert skipped.status == SKIPPED
    # A failure outranks an error.
    assert (
        decide_rollup([_v("a", ERROR, name="x"), _v("b", FAILED)], ANY_FAIL).status
        == FAILED
    )


@pytest.mark.unit_tests
def test_rollup_says_how_many_matching_spans_were_not_judged():
    decision = decide_rollup([_v("a", PASSED)], ANY_FAIL, not_judged=3)
    assert "3 more matching spans past max_spans_per_trace" in decision.description


@dataclass
class _Span:
    span_id: str
    span_name: Optional[str]
    span_kind: Optional[str]
    raw_data: Any


SPANS = [
    _Span("root", "agent", "AGENT", {}),
    _Span("call-1", "lookup_order", "TOOL", {"attributes": {"status": "error"}}),
    _Span("call-2", "lookup_order", "TOOL", {"attributes": {"status": "ok"}}),
    _Span("refund", "refund_order", "TOOL", {"attributes": {"status": "ok"}}),
    _Span("llm", "lookup_order", "LLM", {}),
]


def _ids(span_filter: dict) -> list[str]:
    return [
        s.span_id
        for s in select_spans(
            SPANS,
            ContinuousEvalSpanFilter.model_validate(span_filter),
        )
    ]


@pytest.mark.unit_tests
def test_span_filter_by_name_kind_and_conditions_on_the_span_itself():
    assert _ids({"span_name": "lookup_order"}) == ["call-1", "call-2", "llm"]
    assert _ids({"span_kind": "TOOL"}) == ["call-1", "call-2", "refund"]
    assert _ids({"span_name": "lookup_order", "span_kind": "TOOL"}) == [
        "call-1",
        "call-2",
    ]
    status_ok = {
        "attribute_path": "attributes.status",
        "operator": "equals",
        "value": "ok",
    }
    assert _ids({"span_kind": "TOOL", "conditions": [status_ok]}) == [
        "call-2",
        "refund",
    ]
    # A condition naming another span never holds for this candidate, even with
    # not_equals, which on a whole trace would hold for traces without that span.
    assert (
        _ids(
            {
                "span_kind": "TOOL",
                "conditions": [
                    {
                        "span_name": "agent",
                        "attribute_path": "attributes.status",
                        "operator": "not_equals",
                        "value": "x",
                    },
                ],
            },
        )
        == []
    )

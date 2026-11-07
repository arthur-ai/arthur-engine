"""Tests for matching a trace against a continuous eval's trace filter."""

from datetime import datetime
from typing import Any, Optional

import pytest
from arthur_common.models.response_schemas import (
    NestedSpanWithMetricsResponse,
    TraceResponse,
)
from pydantic import ValidationError

from schemas.common_schemas import ContinuousEvalTraceFilterCondition
from schemas.enums import ContinuousEvalTraceFilterOperator as Op
from utils.transform_executor import trace_matches_filter

NOW = datetime(2026, 11, 6, 12, 0, 0)


def _span(
    name: str,
    attributes: dict[str, Any],
    children: Optional[list[NestedSpanWithMetricsResponse]] = None,
) -> NestedSpanWithMetricsResponse:
    return NestedSpanWithMetricsResponse(
        id=name,
        trace_id="trace-1",
        span_id=name,
        span_name=name,
        start_time=NOW,
        end_time=NOW,
        status_code="Ok",
        created_at=NOW,
        updated_at=NOW,
        raw_data={"name": name, "attributes": attributes},
        children=children or [],
    )


def _analytics_trace(plan: str, row_count: int, model: str) -> TraceResponse:
    """An analytics-agent style trace: the agent run at the root, carrying the
    app's metadata, and the SQL tool and LLM call as children."""
    root = _span(
        "dataAnalystAgent",
        {"metadata": {"plan": plan, "beta": True}, "session": {"id": "s-1"}},
        children=[
            _span("execute-sql", {"output": {"row_count": row_count}}),
            _span("llm", {"llm": {"model_name": model}}),
        ],
    )
    return TraceResponse(
        trace_id="trace-1",
        start_time=NOW,
        end_time=NOW,
        root_spans=[root],
    )


def _condition(
    path: str,
    operator: Op,
    value: Optional[str] = None,
    span_name: Optional[str] = None,
) -> ContinuousEvalTraceFilterCondition:
    return ContinuousEvalTraceFilterCondition(
        span_name=span_name,
        attribute_path=path,
        operator=operator,
        value=value,
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize("trace_filter", [None, []])
def test_no_filter_matches_every_trace(trace_filter):
    assert trace_matches_filter(_analytics_trace("free", 3, "gpt-4.1"), trace_filter)


@pytest.mark.unit_tests
def test_equals_on_root_metadata():
    paid_only = [_condition("attributes.metadata.plan", Op.EQUALS, "paid")]

    assert trace_matches_filter(_analytics_trace("paid", 3, "gpt-4.1"), paid_only)
    assert not trace_matches_filter(_analytics_trace("free", 3, "gpt-4.1"), paid_only)


@pytest.mark.unit_tests
def test_condition_reads_child_spans():
    empty_results = [
        _condition(
            "attributes.output.row_count",
            Op.EQUALS,
            "0",
            span_name="execute-sql",
        ),
    ]

    assert trace_matches_filter(_analytics_trace("paid", 0, "gpt-4.1"), empty_results)
    assert not trace_matches_filter(
        _analytics_trace("paid", 7, "gpt-4.1"),
        empty_results,
    )


@pytest.mark.unit_tests
def test_span_name_limits_which_spans_are_checked():
    # The model name sits on the "llm" span, so looking for it on the SQL tool's
    # span finds nothing.
    on_wrong_span = [
        _condition(
            "attributes.llm.model_name",
            Op.EXISTS,
            span_name="execute-sql",
        ),
    ]

    assert not trace_matches_filter(
        _analytics_trace("paid", 3, "gpt-4.1"),
        on_wrong_span,
    )


@pytest.mark.unit_tests
def test_contains():
    opus = [_condition("attributes.llm.model_name", Op.CONTAINS, "opus")]

    assert trace_matches_filter(_analytics_trace("paid", 3, "claude-opus-5-5"), opus)
    assert not trace_matches_filter(_analytics_trace("paid", 3, "gpt-4.1"), opus)


@pytest.mark.unit_tests
def test_exists():
    has_plan = [_condition("attributes.metadata.plan", Op.EXISTS)]
    has_tier = [_condition("attributes.metadata.tier", Op.EXISTS)]
    trace = _analytics_trace("free", 3, "gpt-4.1")

    assert trace_matches_filter(trace, has_plan)
    assert not trace_matches_filter(trace, has_tier)


@pytest.mark.unit_tests
def test_not_equals_keeps_traces_without_the_attribute():
    not_paid = [_condition("attributes.metadata.plan", Op.NOT_EQUALS, "paid")]
    not_tier_gold = [_condition("attributes.metadata.tier", Op.NOT_EQUALS, "gold")]

    assert trace_matches_filter(_analytics_trace("free", 3, "gpt-4.1"), not_paid)
    assert not trace_matches_filter(_analytics_trace("paid", 3, "gpt-4.1"), not_paid)
    assert trace_matches_filter(_analytics_trace("paid", 3, "gpt-4.1"), not_tier_gold)


@pytest.mark.unit_tests
def test_every_condition_must_hold():
    paid_with_empty_results = [
        _condition("attributes.metadata.plan", Op.EQUALS, "paid"),
        _condition(
            "attributes.output.row_count",
            Op.EQUALS,
            "0",
            span_name="execute-sql",
        ),
    ]

    assert trace_matches_filter(
        _analytics_trace("paid", 0, "gpt-4.1"),
        paid_with_empty_results,
    )
    assert not trace_matches_filter(
        _analytics_trace("paid", 4, "gpt-4.1"),
        paid_with_empty_results,
    )
    assert not trace_matches_filter(
        _analytics_trace("free", 0, "gpt-4.1"),
        paid_with_empty_results,
    )


@pytest.mark.unit_tests
def test_booleans_compare_as_json():
    beta = [_condition("attributes.metadata.beta", Op.EQUALS, "true")]

    assert trace_matches_filter(_analytics_trace("paid", 3, "gpt-4.1"), beta)


@pytest.mark.unit_tests
@pytest.mark.parametrize("operator", [Op.EQUALS, Op.NOT_EQUALS, Op.CONTAINS])
def test_value_is_required_unless_exists(operator):
    with pytest.raises(ValidationError, match="value is required"):
        _condition("attributes.metadata.plan", operator)


@pytest.mark.unit_tests
def test_exists_takes_no_value():
    with pytest.raises(ValidationError, match="value must be null"):
        _condition("attributes.metadata.plan", Op.EXISTS, "paid")

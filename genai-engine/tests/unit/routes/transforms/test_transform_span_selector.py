"""A transform variable's span_selector picks which of several same-named spans it reads."""

from datetime import datetime, timedelta

import pytest
from arthur_common.models.response_schemas import (
    NestedSpanWithMetricsResponse,
    TraceResponse,
)

from schemas.transform_schemas import TraceTransformDefinition
from tests.clients.base_test_client import GenaiEngineTestClientBase
from utils.transform_executor import execute_transform

T0 = datetime(2026, 11, 7, 12, 0, 0)


def _span(span_id: str, name: str, output: dict, offset_s: int, children=None):
    return NestedSpanWithMetricsResponse(
        id=span_id,
        trace_id="t1",
        span_id=span_id,
        span_name=name,
        span_kind="TOOL",
        start_time=T0 + timedelta(seconds=offset_s),
        end_time=T0 + timedelta(seconds=offset_s),
        status_code="Unset",
        created_at=T0,
        updated_at=T0,
        raw_data={"name": name, "attributes": {"output": {"value": output}}},
        children=children or [],
    )


def _retry_trace() -> TraceResponse:
    """An agent span whose lookup_order tool failed once and then succeeded."""
    failed = _span("call-1", "lookup_order", {"error": "upstream timeout"}, 1)
    retried = _span("call-2", "lookup_order", {"status": "delivered"}, 2)
    root = _span(
        "root", "support-agent", {"reply": "ok"}, 0, children=[failed, retried]
    )
    return TraceResponse(trace_id="t1", start_time=T0, end_time=T0, root_spans=[root])


def _definition(selector=None) -> TraceTransformDefinition:
    variable = {
        "variable_name": "result",
        "span_name": "lookup_order",
        "attribute_path": "attributes.output.value",
    }
    if selector:
        variable["span_selector"] = selector
    return TraceTransformDefinition.model_validate({"variables": [variable]})


@pytest.mark.unit_tests
def test_default_reads_the_first_match_as_before():
    result = execute_transform(_retry_trace(), _definition())
    assert result.variables[0].value == '{"error": "upstream timeout"}'


@pytest.mark.unit_tests
def test_last_reads_the_retried_call():
    result = execute_transform(_retry_trace(), _definition("last"))
    assert result.variables[0].value == '{"status": "delivered"}'
    assert result.missing_variables == []


@pytest.mark.unit_tests
def test_all_reads_every_call_in_start_order_with_span_ids():
    result = execute_transform(_retry_trace(), _definition("all"))
    assert result.variables[0].value == (
        '[span call-1]\n{"error": "upstream timeout"}\n\n'
        '[span call-2]\n{"status": "delivered"}'
    )


@pytest.mark.unit_tests
def test_selector_missing_attribute_uses_fallback_or_reports_missing():
    definition = TraceTransformDefinition.model_validate(
        {
            "variables": [
                {
                    "variable_name": "missing",
                    "span_name": "lookup_order",
                    "attribute_path": "attributes.nothing",
                    "span_selector": "all",
                },
            ],
        },
    )
    result = execute_transform(_retry_trace(), definition)
    assert result.missing_variables == ["missing"]


@pytest.mark.unit_tests
def test_unknown_selector_is_rejected():
    with pytest.raises(ValueError):
        _definition("middle")


@pytest.mark.unit_tests
def test_span_selector_round_trips_through_the_api(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(
        name="span_selector_round_trip", is_agentic=True
    )
    assert status_code == 200
    try:
        resp = client.base_client.post(
            f"/api/v1/tasks/{task.id}/traces/transforms",
            json={
                "name": "retried tool",
                "definition": {
                    "variables": [
                        {
                            "variable_name": "result",
                            "span_name": "lookup_order",
                            "attribute_path": "attributes.output.value",
                            "span_selector": "last",
                        },
                        {
                            "variable_name": "question",
                            "span_name": "support-agent",
                            "attribute_path": "attributes.input.value",
                        },
                    ],
                },
            },
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 200, resp.text
        transform_id = resp.json()["id"]
        variables = client.base_client.get(
            f"/api/v1/traces/transforms/{transform_id}",
            headers=client.authorized_user_api_key_headers,
        ).json()["definition"]["variables"]
        assert [v["span_selector"] for v in variables] == ["last", "first"]
    finally:
        client.delete_task(task.id)

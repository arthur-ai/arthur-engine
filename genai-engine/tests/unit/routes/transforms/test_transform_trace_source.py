"""A transform variable with source='trace' is the whole trace as judge-ready text."""

import pytest
from pydantic import ValidationError

from schemas.transform_schemas import (
    TraceTransformDefinition,
    TraceTransformVariableDefinition,
    TransformVariableSource,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.unit.routes.transforms.test_transform_span_order import (
    RETRY_TRACE,
    _definition,
    _span,
    _trace,
    add_trace,
    delete_traces,
)
from utils.span_tree import tree_order
from utils.trace_serializer import MIN_MAX_CHARS, serialize_trace
from utils.transform_executor import (
    execute_transform,
    execute_transform_on_spans,
    flatten_trace_spans,
)


def _retry_trace():
    return _trace(
        _span(
            "root",
            "agent",
            "delivered",
            0,
            kind="AGENT",
            children=[
                _span("call-1", "lookup_order", "upstream timeout", 1, parent="root"),
                _span("call-2", "lookup_order", "delivered", 2, parent="root"),
            ],
        ),
    )


def _trace_definition(**variable) -> TraceTransformDefinition:
    return TraceTransformDefinition.model_validate(
        {
            "variables": [
                {
                    "variable_name": "trace",
                    "source": "trace",
                    "attribute_path": "",
                    **variable,
                }
            ]
        },
    )


@pytest.mark.unit_tests
def test_trace_variable_needs_no_span_or_attribute_path():
    var = TraceTransformVariableDefinition.model_validate(
        {"variable_name": "trace", "source": "trace", "attribute_path": ""},
    )
    assert var.source == TransformVariableSource.TRACE
    assert var.span_name is None and var.attribute_path == ""
    assert var.max_chars is None
    assert var.describe_spans() == "the trace"


@pytest.mark.unit_tests
def test_span_variable_still_needs_a_span_name_or_kind():
    with pytest.raises(ValidationError, match="needs a span_name, a span_kind or both"):
        TraceTransformVariableDefinition.model_validate(
            {"variable_name": "x", "attribute_path": "attributes.output.value"},
        )
    var = TraceTransformVariableDefinition.model_validate(
        {
            "variable_name": "x",
            "span_name": "lookup_order",
            "attribute_path": "attributes.output.value",
        },
    )
    assert var.source == TransformVariableSource.SPAN


@pytest.mark.unit_tests
def test_max_chars_has_a_floor():
    with pytest.raises(ValidationError):
        TraceTransformVariableDefinition.model_validate(
            {
                "variable_name": "t",
                "source": "trace",
                "attribute_path": "",
                "max_chars": MIN_MAX_CHARS - 1,
            },
        )


@pytest.mark.unit_tests
def test_trace_value_is_the_serialized_trace_and_names_every_span():
    trace = _retry_trace()
    spans = flatten_trace_spans(trace)
    result = execute_transform(trace, _trace_definition())

    assert result.variables[0].value == serialize_trace(spans)[0]
    assert "[2] TOOL lookup_order" in result.variables[0].value
    assert (
        "result: upstream timeout" in result.variables[0].value
    )  # the failed call is kept
    assert result.missing_variables == [] and result.missing_spans == []
    assert result.variable_spans[0].span_ids == [s.span_id for s in tree_order(spans)]


@pytest.mark.unit_tests
def test_flat_and_tree_inputs_give_the_same_text():
    trace = _retry_trace()
    from_tree = execute_transform(trace, _trace_definition())
    from_flat = execute_transform_on_spans(
        list(reversed(flatten_trace_spans(trace))),
        _trace_definition(),
    )
    assert from_tree.variables[0].value == from_flat.variables[0].value


@pytest.mark.unit_tests
def test_max_chars_caps_the_value():
    big = _trace(
        _span(
            "root",
            "agent",
            "x" * 50_000,
            0,
            kind="AGENT",
        ),
    )
    value = (
        execute_transform(big, _trace_definition(max_chars=MIN_MAX_CHARS))
        .variables[0]
        .value
    )
    assert len(value) <= MIN_MAX_CHARS
    assert "[TRUNCATED view of 1 spans" in value


@pytest.mark.unit_tests
def test_trace_and_span_variables_in_one_transform():
    definition = TraceTransformDefinition.model_validate(
        {
            "variables": [
                {"variable_name": "trace", "source": "trace", "attribute_path": ""},
                {
                    "variable_name": "last_result",
                    "span_name": "lookup_order",
                    "attribute_path": "attributes.output.value",
                    "span_selector": "last",
                },
            ],
        },
    )
    result = execute_transform(_retry_trace(), definition)
    assert result.variables[0].value.startswith("TRACE v1 spans=3")
    assert result.variables[1].value == "delivered"
    assert result.variable_spans[1].span_ids == ["call-2"]
    # the span-selector path is unchanged
    assert (
        execute_transform(_retry_trace(), _definition(span_name="lookup_order"))
        .variables[0]
        .value
        == "upstream timeout"
    )


@pytest.mark.unit_tests
def test_extraction_route_returns_the_trace_text(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(name="trace_source", is_agentic=True)
    assert status_code == 200
    try:
        trace_id = add_trace(task.id, RETRY_TRACE)
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="whole trace",
            description="whole trace",
            definition={
                "variables": [
                    {"variable_name": "trace", "source": "trace", "attribute_path": ""},
                ],
            },
        )
        assert status_code == 200, transform
        assert transform.definition.variables[0].source == TransformVariableSource.TRACE
        resp = client.base_client.post(
            f"/api/v1/traces/{trace_id}/transforms/{transform.id}/extractions",
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        value = body["variables"][0]["value"]
        assert value.startswith("TRACE v1 spans=3 agent=1 tool=2")
        assert "[1] AGENT agent" in value and "  [3] TOOL lookup_order" in value
        assert body["variable_spans"] == [
            {"variable_name": "trace", "span_ids": ["root", "call-1", "call-2"]},
        ]
    finally:
        delete_traces(task.id)
        client.delete_task(task.id)

"""Transform variables that read a whole trace (source='trace') or every matching span.

The running example is a retry: an agent calls `search` three times. The first call
times out, the second gets an HTTP 500, the third finds flights. A judge asked "did
the run eventually succeed?" must see all three calls, not just one of them.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest
from pydantic import ValidationError

from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from schemas.transform_schemas import (
    TraceTransformDefinition,
    TraceTransformVariableDefinition,
    TransformVariableSource,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from utils.constants import DEFAULT_ORG_ID
from utils.trace_serializer import MIN_MAX_CHARS, serialize_trace
from utils.transform_executor import execute_transform_on_spans

T0 = datetime(2026, 11, 19, 9, 0, 0)

# (span_id, parent_span_id, kind, name, start offset in s, output, status)
RETRY_TRACE: list[tuple[str, Optional[str], str, str, float, str, str]] = [
    ("root", None, "AGENT", "travel-agent", 0, "Found 3 flights to Lisbon.", "Ok"),
    ("search-1", "root", "TOOL", "search", 1, "timeout after 30s", "Error"),
    ("search-2", "root", "TOOL", "search", 32, "HTTP 500 from flight API", "Error"),
    ("search-3", "root", "TOOL", "search", 34, "3 flights found", "Ok"),
]


def raw_data(span_id: str, name: str, output: str, status: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": name,
        "spanId": span_id,
        "attributes": {
            "input": {"value": '{"to": "Lisbon"}'},
            "output": {"value": output},
        },
        "arthur_span_version": "arthur_span_v1",
    }
    if status == "Error":
        data["status"] = {"message": output}
    return data


class Span:
    """The span shape transforms read; DB rows and API responses both fit it."""

    def __init__(
        self,
        span_id: str,
        parent: Optional[str],
        kind: str,
        name: str,
        offset: float,
        output: str,
        status: str = "Ok",
    ) -> None:
        self.span_id = span_id
        self.parent_span_id = parent
        self.span_kind = kind
        self.span_name = name
        self.status_code = status
        self.start_time = T0 + timedelta(seconds=offset)
        self.end_time = self.start_time + timedelta(seconds=1)
        self.raw_data = raw_data(span_id, name, output, status)


def spans(rows=RETRY_TRACE) -> list[Span]:
    return [Span(*row) for row in rows]


def definition(*variables: dict[str, Any]) -> TraceTransformDefinition:
    return TraceTransformDefinition.model_validate({"variables": list(variables)})


WHOLE_TRACE = {
    "variable_name": "trace",
    "source": "trace",
    "span_name": "",
    "attribute_path": "",
}
SEARCH_OUTPUT = {
    "variable_name": "search_output",
    "span_name": "search",
    "attribute_path": "attributes.output.value",
}


def add_trace(task_id: str, rows=RETRY_TRACE) -> str:
    """Store a trace's spans and metadata; returns the trace id."""
    db_session = override_get_db_session()
    trace_id = str(uuid.uuid4())
    for span in spans(rows):
        db_session.add(
            DatabaseSpan(
                id=str(uuid.uuid4()),
                trace_id=trace_id,
                span_id=f"{trace_id}-{span.span_id}",
                parent_span_id=(
                    f"{trace_id}-{span.parent_span_id}" if span.parent_span_id else None
                ),
                span_name=span.span_name,
                span_kind=span.span_kind,
                start_time=span.start_time,
                end_time=span.end_time,
                task_id=task_id,
                org_id=DEFAULT_ORG_ID,
                status_code=span.status_code,
                raw_data=span.raw_data,
                created_at=T0,
                updated_at=T0,
            ),
        )
    db_session.add(
        DatabaseTraceMetadata(
            task_id=task_id,
            org_id=DEFAULT_ORG_ID,
            trace_id=trace_id,
            span_count=len(rows),
            start_time=T0,
            end_time=T0 + timedelta(seconds=60),
            created_at=T0,
            updated_at=T0,
        ),
    )
    db_session.commit()
    return trace_id


def delete_traces(task_id: str) -> None:
    db_session = override_get_db_session()
    db_session.query(DatabaseSpan).filter(DatabaseSpan.task_id == task_id).delete()
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.task_id == task_id,
    ).delete()
    db_session.commit()


@pytest.mark.unit_tests
def test_whole_trace_variable_shows_every_attempt_in_one_value():
    result = execute_transform_on_spans(spans(), definition(WHOLE_TRACE))

    (value,) = [v.value for v in result.variables]
    assert value == serialize_trace(spans())[0]
    assert value.startswith("TRACE v1 spans=4 agent=1 tool=3 errors=2")
    for text in ("timeout after 30s", "HTTP 500 from flight API", "3 flights found"):
        assert text in value
    assert result.variable_spans[0].span_ids == [
        "root",
        "search-1",
        "search-2",
        "search-3",
    ]
    assert result.missing_spans == [] and result.missing_variables == []


@pytest.mark.unit_tests
def test_span_variable_with_several_matches_reads_all_of_them_in_order():
    # rows shuffled: the value still follows tree order, not row order
    result = execute_transform_on_spans(
        list(reversed(spans())),
        definition(SEARCH_OUTPUT),
    )

    assert result.variables[0].value == (
        "[span search-1]\ntimeout after 30s\n\n"
        "[span search-2]\nHTTP 500 from flight API\n\n"
        "[span search-3]\n3 flights found"
    )
    assert result.variable_spans[0].span_ids == ["search-1", "search-2", "search-3"]


@pytest.mark.unit_tests
def test_span_variable_with_one_match_is_unchanged():
    result = execute_transform_on_spans(
        spans(),
        definition({**SEARCH_OUTPUT, "span_name": "travel-agent"}),
    )
    assert result.variables[0].value == "Found 3 flights to Lisbon."
    assert result.variable_spans[0].span_ids == ["root"]


@pytest.mark.unit_tests
def test_spans_in_a_parent_cycle_are_kept():
    cyclic = RETRY_TRACE + [
        ("loop-a", "loop-b", "TOOL", "search", 40, "cycle a", "Ok"),
        ("loop-b", "loop-a", "TOOL", "search", 41, "cycle b", "Ok"),
    ]
    result = execute_transform_on_spans(
        spans(cyclic),
        definition(WHOLE_TRACE, SEARCH_OUTPUT),
    )
    trace_value, search_value = (v.value for v in result.variables)
    assert "spans=6" in trace_value and "cycle a" in trace_value
    assert "cycle b" in trace_value
    assert "[span loop-a]\ncycle a" in search_value
    assert "[span loop-b]\ncycle b" in search_value
    assert len(result.variable_spans[0].span_ids) == 6


@pytest.mark.unit_tests
def test_max_chars_caps_the_trace_and_says_what_was_cut():
    long_trace = [RETRY_TRACE[0]] + [
        (f"read-{i}", "root", "TOOL", "read_file", 1 + i, "x" * 1500, "Ok")
        for i in range(12)
    ]
    value = (
        execute_transform_on_spans(
            spans(long_trace),
            definition({**WHOLE_TRACE, "max_chars": MIN_MAX_CHARS}),
        )
        .variables[0]
        .value
    )
    assert len(value) <= MIN_MAX_CHARS
    assert "[TRUNCATED view of 13 spans" in value
    assert "[1] AGENT travel-agent" in value  # the root is never left out


@pytest.mark.unit_tests
def test_several_matches_are_joined_within_max_chars():
    """Twelve retries with long outputs: each value is cut to a share of the budget,
    head and tail kept, and the closing line says what was cut."""
    retries = [RETRY_TRACE[0]] + [
        (
            f"search-{i}",
            "root",
            "TOOL",
            "search",
            1 + i,
            f"attempt {i} " + "x" * 3000,
            "Ok",
        )
        for i in range(12)
    ]
    result = execute_transform_on_spans(
        spans(retries),
        definition({**SEARCH_OUTPUT, "max_chars": 12_000}),
    )
    value = result.variables[0].value
    assert len(value) <= 12_000
    assert value.count("[span ") == 12  # every attempt is still there
    assert "attempt 0" in value and "attempt 11" in value
    assert "chars cut]" in value
    assert value.endswith(
        "[TRUNCATED view of 12 matching spans, 36,338 chars in full: "
        "12 values shortened, 0 spans omitted]",
    )
    assert len(result.variable_spans[0].span_ids) == 12


@pytest.mark.unit_tests
def test_too_many_matches_for_the_budget_leave_out_middle_spans():
    retries = [RETRY_TRACE[0]] + [
        (
            f"search-{i}",
            "root",
            "TOOL",
            "search",
            1 + i,
            f"attempt {i} " + "x" * 500,
            "Ok",
        )
        for i in range(40)
    ]
    result = execute_transform_on_spans(
        spans(retries),
        definition({**SEARCH_OUTPUT, "max_chars": MIN_MAX_CHARS}),
    )
    value = result.variables[0].value
    assert len(value) <= MIN_MAX_CHARS
    # the first and last attempts stay; the gap is named where it is
    assert value.startswith("[span search-0]\nattempt 0")
    assert "[span search-39]\nattempt 39" in value
    assert "matching spans omitted]" in value
    assert value.endswith("spans omitted]") and "of 40 matching spans" in value
    # variable_spans lists only the spans whose blocks are in the value
    shown = result.variable_spans[0].span_ids
    assert shown[0] == "search-0" and shown[-1] == "search-39"
    assert len(shown) < 40 and all(f"[span {span_id}]" in value for span_id in shown)


@pytest.mark.unit_tests
def test_spans_whose_header_is_cut_are_not_listed():
    """Two 1,000-char span ids in a 2,000-char budget: the final cut takes part of
    the second header, so only the first span is listed."""
    first, second = "a" * 1000, "b" * 1000
    long_ids = [
        RETRY_TRACE[0],
        (first, "root", "TOOL", "search", 1, "timeout after 30s", "Error"),
        (second, "root", "TOOL", "search", 2, "3 flights found", "Ok"),
    ]
    result = execute_transform_on_spans(
        spans(long_ids),
        definition({**SEARCH_OUTPUT, "max_chars": MIN_MAX_CHARS}),
    )
    value = result.variables[0].value
    assert len(value) <= MIN_MAX_CHARS
    assert f"[span {second}]" not in value
    assert result.variable_spans[0].span_ids == [first]
    assert "1 spans omitted]" in value


@pytest.mark.unit_tests
def test_a_header_like_string_inside_a_value_does_not_count_as_shown():
    """A long first span id leaves the final cut inside the second span's header,
    while the first value starts with text that looks exactly like that header.
    The second span must not be listed."""
    first = "a" * 1650
    long_ids = [
        RETRY_TRACE[0],
        (
            first,
            "root",
            "TOOL",
            "search",
            1,
            "\n\n[span s]\nlooks real" + "y" * 1000,
            "Ok",
        ),
        ("s", "root", "TOOL", "search", 2, "3 flights found", "Ok"),
    ]
    result = execute_transform_on_spans(
        spans(long_ids),
        definition({**SEARCH_OUTPUT, "max_chars": MIN_MAX_CHARS}),
    )
    value = result.variables[0].value
    assert len(value) <= MIN_MAX_CHARS
    assert "\n\n[span s]\nlooks real" in value  # the look-alike survives the cut
    assert "3 flights found" not in value
    assert result.variable_spans[0].span_ids == [first]
    assert "1 spans omitted]" in value


@pytest.mark.unit_tests
def test_a_single_long_match_is_never_cut():
    long_answer = [("root", None, "AGENT", "travel-agent", 0, "y" * 5000, "Ok")]
    value = (
        execute_transform_on_spans(
            spans(long_answer),
            definition(
                {
                    **SEARCH_OUTPUT,
                    "span_name": "travel-agent",
                    "max_chars": MIN_MAX_CHARS,
                },
            ),
        )
        .variables[0]
        .value
    )
    assert value == "y" * 5000


@pytest.mark.unit_tests
def test_variable_source_defaults_to_span_and_max_chars_has_a_floor():
    var = TraceTransformVariableDefinition.model_validate(SEARCH_OUTPUT)
    assert var.source == TransformVariableSource.SPAN and var.max_chars is None

    var = TraceTransformVariableDefinition.model_validate(WHOLE_TRACE)
    assert var.source == TransformVariableSource.TRACE

    with pytest.raises(ValidationError):
        TraceTransformVariableDefinition.model_validate(
            {**WHOLE_TRACE, "max_chars": MIN_MAX_CHARS - 1},
        )


@pytest.mark.unit_tests
def test_extraction_route_reads_the_whole_trace_including_a_cycle(
    client: GenaiEngineTestClientBase,
):
    """The preview route reads the flat span list, so it agrees with the executor:
    the tree view of the trace leaves out spans caught in a parent cycle."""
    status_code, task = client.create_task(name="whole_trace", is_agentic=True)
    assert status_code == 200
    cyclic = RETRY_TRACE + [
        ("loop-a", "loop-b", "TOOL", "search", 40, "cycle a", "Ok"),
        ("loop-b", "loop-a", "TOOL", "search", 41, "cycle b", "Ok"),
    ]
    try:
        trace_id = add_trace(task.id, cyclic)
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="whole trace",
            definition={"variables": [WHOLE_TRACE, SEARCH_OUTPUT]},
        )
        assert status_code == 200, transform
        assert transform.definition.variables[0].source == TransformVariableSource.TRACE

        status_code, result = client.execute_transform_extraction(
            transform_id=transform.id,
            trace_id=trace_id,
        )
        assert status_code == 200
        trace_value, search_value = (v.value for v in result.variables)
        assert trace_value.startswith("TRACE v1 spans=6")
        assert "timeout after 30s" in trace_value and "cycle b" in trace_value
        assert search_value.count("[span ") == 5
        assert result.missing_spans == []
        assert [s.span_ids[:2] for s in result.variable_spans] == [
            [f"{trace_id}-root", f"{trace_id}-search-1"],
            [f"{trace_id}-search-1", f"{trace_id}-search-2"],
        ]
    finally:
        delete_traces(task.id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_matches_without_the_attribute_are_left_out_and_not_listed():
    no_output = [
        RETRY_TRACE[0],
        ("search-1", "root", "TOOL", "search", 1, "timeout after 30s", "Error"),
        ("search-2", "root", "TOOL", "search", 2, "3 flights found", "Ok"),
    ]
    rows = spans(no_output)
    del rows[1].raw_data["attributes"]["output"]  # search-1 recorded no output
    result = execute_transform_on_spans(rows, definition(SEARCH_OUTPUT))
    assert result.variables[0].value == "[span search-2]\n3 flights found"
    assert result.variable_spans[0].span_ids == ["search-2"]


@pytest.mark.unit_tests
def test_a_trace_with_no_valid_spans_is_not_found(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(name="no_valid_spans", is_agentic=True)
    assert status_code == 200
    try:
        trace_id = add_trace(task.id)
        db_session = override_get_db_session()
        for row in db_session.query(DatabaseSpan).filter(
            DatabaseSpan.trace_id == trace_id,
        ):
            row.raw_data = {**row.raw_data, "arthur_span_version": "unknown"}
        db_session.commit()
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="whole trace",
            definition={"variables": [WHOLE_TRACE]},
        )
        assert status_code == 200
        status_code, _ = client.execute_transform_extraction(
            transform_id=transform.id,
            trace_id=trace_id,
        )
        assert status_code == 404
    finally:
        delete_traces(task.id)
        client.delete_task(task.id)

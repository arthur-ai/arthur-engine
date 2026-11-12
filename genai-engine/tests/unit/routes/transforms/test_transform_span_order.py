"""first/last/all share one span order (tree order), span_kind can match alone, and
the extraction names the spans each value came from."""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest
from arthur_common.models.response_schemas import (
    NestedSpanWithMetricsResponse,
    TraceResponse,
)

from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from schemas.transform_schemas import TraceTransformDefinition
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.unit.routes.tasks.test_continuous_eval_crud_routes import (
    create_test_llm_eval,
    create_test_transform,
)
from utils.constants import (
    DEFAULT_ORG_ID,
    EXPECTED_SPAN_VERSION,
    SPAN_VERSION_KEY,
)
from utils.span_tree import tree_order
from utils.stored_value import STORED_VALUE_MAX_CHARS, cap_stored_value
from utils.transform_executor import execute_transform, execute_transform_on_spans

T0 = datetime(2026, 11, 7, 12, 0, 0)


def _span(
    span_id: str,
    name: str,
    output: Any,
    offset_s: float,
    kind: str = "TOOL",
    children=None,
    parent: Optional[str] = None,
):
    return NestedSpanWithMetricsResponse(
        id=span_id,
        trace_id="t1",
        span_id=span_id,
        parent_span_id=parent,
        span_name=name,
        span_kind=kind,
        start_time=T0 + timedelta(seconds=offset_s),
        end_time=T0 + timedelta(seconds=offset_s),
        status_code="Unset",
        created_at=T0,
        updated_at=T0,
        raw_data={"name": name, "attributes": {"output": {"value": output}}},
        children=children or [],
    )


def _trace(*roots) -> TraceResponse:
    return TraceResponse(trace_id="t1", start_time=T0, end_time=T0, root_spans=roots)


def _definition(**variable) -> TraceTransformDefinition:
    return TraceTransformDefinition.model_validate(
        {
            "variables": [
                {
                    "variable_name": "result",
                    "attribute_path": "attributes.output.value",
                    **variable,
                },
            ],
        },
    )


@dataclass
class _FlatSpan:
    """A DB-row-like span: only the flat fields, no children."""

    span_id: str
    parent_span_id: Optional[str]
    start_time: datetime
    span_name: Optional[str] = "lookup_order"
    span_kind: Optional[str] = "TOOL"
    raw_data: Any = None


@pytest.mark.unit_tests
def test_siblings_with_the_same_start_time_order_by_span_id():
    """Two calls logged in the same millisecond: first/last are decided by span id,
    not by the order the tree happened to list them."""
    root = _span(
        "root",
        "agent",
        "ok",
        0,
        kind="AGENT",
        children=[
            _span("call-b", "lookup_order", "second", 1, parent="root"),
            _span("call-a", "lookup_order", "first", 1, parent="root"),
        ],
    )
    trace = _trace(root)
    first = execute_transform(trace, _definition(span_name="lookup_order"))
    last = execute_transform(
        trace,
        _definition(span_name="lookup_order", span_selector="last"),
    )
    assert first.variables[0].value == "first"
    assert last.variables[0].value == "second"


@pytest.mark.unit_tests
def test_last_is_the_mirror_of_first_in_tree_order_not_latest_start():
    """Branch A's call starts later than branch B's, but B comes after A in the
    tree, so 'last' is B's call: first and last are the two ends of one order."""
    branch_a = _span(
        "a",
        "plan",
        "a",
        0,
        kind="CHAIN",
        parent="root",
        children=[_span("a-call", "lookup_order", "from A", 5, parent="a")],
    )
    branch_b = _span(
        "b",
        "plan",
        "b",
        1,
        kind="CHAIN",
        parent="root",
        children=[_span("b-call", "lookup_order", "from B", 2, parent="b")],
    )
    trace = _trace(
        _span("root", "agent", "ok", 0, kind="AGENT", children=[branch_a, branch_b]),
    )
    last = execute_transform(
        trace,
        _definition(span_name="lookup_order", span_selector="last"),
    )
    every = execute_transform(
        trace,
        _definition(span_name="lookup_order", span_selector="all"),
    )
    assert last.variables[0].value == "from B"
    assert every.variables[0].value == "[span a-call]\nfrom A\n\n[span b-call]\nfrom B"


@pytest.mark.unit_tests
def test_child_that_starts_before_its_parent_still_comes_after_it():
    child = _span("llm", "llm-call", "child", 0, kind="LLM", parent="root")
    root = _span("root", "agent", "root", 0.06, kind="AGENT", children=[child])
    result = execute_transform(
        _trace(root),
        _definition(span_kind="AGENT", span_selector="all"),
    )
    assert result.variable_spans[0].span_ids == ["root"]
    assert [s.span_id for s in tree_order([child, root])] == ["root", "llm"]


@pytest.mark.unit_tests
def test_span_kind_alone_matches_every_span_of_that_kind():
    root = _span(
        "root",
        "agent",
        "ok",
        0,
        kind="AGENT",
        children=[
            _span("t1", "lookup_order", "found", 1, parent="root"),
            _span("t2", "refund_order", "refunded", 2, parent="root"),
            _span("l1", "llm", "text", 3, kind="LLM", parent="root"),
        ],
    )
    result = execute_transform(
        _trace(root),
        _definition(span_kind="TOOL", span_selector="all"),
    )
    assert result.variables[0].value == "[span t1]\nfound\n\n[span t2]\nrefunded"
    assert result.variable_spans[0].span_ids == ["t1", "t2"]


@pytest.mark.unit_tests
def test_span_kind_narrows_span_name():
    root = _span(
        "root",
        "agent",
        "ok",
        0,
        kind="AGENT",
        children=[
            _span("x-llm", "lookup_order", "llm", 1, kind="LLM", parent="root"),
            _span("x-tool", "lookup_order", "tool", 2, parent="root"),
        ],
    )
    result = execute_transform(
        _trace(root),
        _definition(span_name="lookup_order", span_kind="TOOL"),
    )
    assert result.variables[0].value == "tool"


@pytest.mark.unit_tests
def test_a_variable_needs_span_name_or_span_kind():
    with pytest.raises(ValueError, match="span_name, a span_kind or both"):
        _definition()


@pytest.mark.unit_tests
def test_spans_in_a_parent_cycle_or_with_a_missing_parent_are_still_read():
    """The flat list is the source: an orphan and two spans that name each other as
    parent become roots instead of disappearing."""
    spans = [
        _FlatSpan("orphan", "gone", T0 + timedelta(seconds=3), raw_data={"v": 3}),
        _FlatSpan("cyc-1", "cyc-2", T0 + timedelta(seconds=1), raw_data={"v": 1}),
        _FlatSpan("cyc-2", "cyc-1", T0 + timedelta(seconds=2), raw_data={"v": 2}),
        _FlatSpan("self", "self", T0, raw_data={"v": 0}),
    ]
    assert [s.span_id for s in tree_order(spans)] == [
        "self",
        "cyc-1",
        "cyc-2",
        "orphan",
    ]
    result = execute_transform_on_spans(
        spans,
        TraceTransformDefinition.model_validate(
            {
                "variables": [
                    {
                        "variable_name": "v",
                        "span_name": "lookup_order",
                        "attribute_path": "v",
                        "span_selector": "all",
                    },
                ],
            },
        ),
    )
    assert result.variable_spans[0].span_ids == ["self", "cyc-1", "cyc-2", "orphan"]


@pytest.mark.unit_tests
def test_missing_span_is_named_once_and_by_kind_when_no_name():
    definition = TraceTransformDefinition.model_validate(
        {
            "variables": [
                {"variable_name": "a", "span_name": "nope", "attribute_path": "x"},
                {"variable_name": "b", "span_name": "nope", "attribute_path": "y"},
                {"variable_name": "c", "span_kind": "RETRIEVER", "attribute_path": "z"},
            ],
        },
    )
    result = execute_transform(_trace(_span("root", "agent", "ok", 0)), definition)
    assert result.missing_spans == ["nope", "any RETRIEVER span"]
    assert [v.span_ids for v in result.variable_spans] == [[], [], []]


@pytest.mark.unit_tests
def test_stored_value_cap_keeps_head_tail_and_a_verifiable_marker():
    short = "x" * STORED_VALUE_MAX_CHARS
    assert cap_stored_value(short) == short

    value = "H" * 6_000 + "M" * 10_000 + "T" * 6_000
    capped = cap_stored_value(value)
    assert len(capped) <= STORED_VALUE_MAX_CHARS
    assert capped.startswith("H" * 3_000)
    assert capped.endswith("T" * 3_000)
    digest = hashlib.sha256(value.encode()).hexdigest()
    assert f"sha256={digest}, len={len(value)}]" in capped
    kept = len(capped) - len(capped[capped.index("\n[cut") : capped.index("]\n") + 2])
    assert f"[cut {len(value) - kept} chars," in capped


def add_trace(task_id: str, spans: list[dict]) -> str:
    """Store a trace as span rows (plus its metadata row); each dict gives span_id,
    parent_span_id, span_name, span_kind, offset_s and output. Returns the trace id."""
    db_session = override_get_db_session()
    trace_id = uuid.uuid4().hex
    starts = [T0 + timedelta(seconds=s["offset_s"]) for s in spans]
    db_session.add(
        DatabaseTraceMetadata(
            task_id=task_id,
            org_id=DEFAULT_ORG_ID,
            trace_id=trace_id,
            span_count=len(spans),
            start_time=min(starts),
            end_time=max(starts),
            created_at=T0,
            updated_at=T0,
        ),
    )
    for spec, start in zip(spans, starts):
        db_session.add(
            DatabaseSpan(
                id=uuid.uuid4().hex,
                trace_id=trace_id,
                span_id=spec["span_id"],
                parent_span_id=spec.get("parent_span_id"),
                span_name=spec["span_name"],
                span_kind=spec.get("span_kind", "TOOL"),
                start_time=start,
                end_time=start,
                task_id=task_id,
                org_id=DEFAULT_ORG_ID,
                raw_data={
                    SPAN_VERSION_KEY: EXPECTED_SPAN_VERSION,
                    "name": spec["span_name"],
                    "attributes": {"output": {"value": spec.get("output")}},
                },
            ),
        )
    db_session.commit()
    return trace_id


def delete_traces(task_id: str) -> None:
    db_session = override_get_db_session()
    db_session.query(DatabaseSpan).filter(DatabaseSpan.task_id == task_id).delete(
        synchronize_session=False,
    )
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.task_id == task_id,
    ).delete(synchronize_session=False)
    db_session.commit()


RETRY_TRACE = [
    {"span_id": "root", "span_name": "agent", "span_kind": "AGENT", "offset_s": 0},
    {
        "span_id": "call-1",
        "parent_span_id": "root",
        "span_name": "lookup_order",
        "offset_s": 1,
        "output": "upstream timeout",
    },
    {
        "span_id": "call-2",
        "parent_span_id": "root",
        "span_name": "lookup_order",
        "offset_s": 2,
        "output": "delivered",
    },
]


@pytest.mark.unit_tests
def test_extraction_route_returns_the_spans_each_value_came_from(
    client: GenaiEngineTestClientBase,
):
    """The UI preview validates columns from these ids instead of re-matching spans,
    so it shows the span the worker would judge ('last' here, not the first match)."""
    status_code, task = client.create_task(name="preview_span_ids", is_agentic=True)
    assert status_code == 200
    try:
        trace_id = add_trace(task.id, RETRY_TRACE)
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="preview",
            description="preview",
            definition={
                "variables": [
                    {
                        "variable_name": "retried",
                        "span_kind": "TOOL",
                        "attribute_path": "attributes.output.value",
                        "span_selector": "last",
                    },
                    {
                        "variable_name": "every",
                        "span_name": "lookup_order",
                        "attribute_path": "attributes.output.value",
                        "span_selector": "all",
                    },
                ],
            },
        )
        assert status_code == 200, transform
        resp = client.base_client.post(
            f"/api/v1/traces/{trace_id}/transforms/{transform.id}/extractions",
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["variables"][0]["value"] == "delivered"
        assert body["variable_spans"] == [
            {"variable_name": "retried", "span_ids": ["call-2"]},
            {"variable_name": "every", "span_ids": ["call-1", "call-2"]},
        ]
    finally:
        delete_traces(task.id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_new_transform_version_restarts_the_pricing_window(
    client: GenaiEngineTestClientBase,
):
    """A new definition changes what the judge reads (an 'all' value can be many
    times longer), so evals following the latest version are priced afresh."""
    status_code, task = client.create_task(name="transform_window", is_agentic=True)
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "window_eval")
    assert status_code == 200
    status_code, transform = create_test_transform(client, task.id)
    assert status_code == 200
    status_code, continuous_eval = client.save_continuous_eval(
        task_id=task.id,
        continuous_eval_data={
            "name": "window",
            "llm_eval_name": llm_eval.name,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "test_variable",
                    "eval_variable": "test_variable",
                },
            ],
        },
    )
    assert status_code == 200

    def changed_at():
        db_session = override_get_db_session()
        row = db_session.get(DatabaseContinuousEval, continuous_eval.id)
        db_session.refresh(row)
        return row.judge_changed_at

    try:
        assert changed_at() is None
        status_code, _ = client.update_transform(str(transform.id), description="docs")
        assert status_code == 200
        assert changed_at() is None

        status_code, _ = client.update_transform(
            str(transform.id),
            definition={
                "variables": [
                    {
                        "variable_name": "test_variable",
                        "span_name": "test_span",
                        "attribute_path": "test_attribute",
                        "span_selector": "all",
                    },
                ],
            },
        )
        assert status_code == 200
        first_reset = changed_at()
        assert first_reset is not None

        # Pinning the eval to a version is a transform change too.
        versions = client.base_client.get(
            f"/api/v1/traces/transforms/{transform.id}/versions",
            headers=client.authorized_user_api_key_headers,
        ).json()["versions"]
        status_code, _ = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={"transform_version_id": versions[-1]["id"]},
        )
        assert status_code == 200
        assert changed_at() > first_reset
    finally:
        client.delete_continuous_eval(continuous_eval.id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_a_new_variable_mapping_reprices_the_eval(
    client: GenaiEngineTestClientBase,
):
    """Mapping the judge's variable to another transform variable changes what the
    judge reads, so spend is priced afresh; sending the same mapping again does not."""
    status_code, task = client.create_task(name="mapping_window", is_agentic=True)
    assert status_code == 200
    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id, "mapping_eval")
        assert status_code == 200
        variable = {"span_name": "test_span", "attribute_path": "test_attribute"}
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="two variables",
            description="short and long",
            definition={
                "variables": [
                    {"variable_name": "short", **variable},
                    {"variable_name": "long", "span_selector": "all", **variable},
                ],
            },
        )
        assert status_code == 200

        def mapping(transform_variable: str) -> list[dict]:
            return [
                {
                    "transform_variable": transform_variable,
                    "eval_variable": "test_variable",
                },
            ]

        status_code, continuous_eval = client.save_continuous_eval(
            task_id=task.id,
            continuous_eval_data={
                "name": "mapping",
                "llm_eval_name": llm_eval.name,
                "transform_id": str(transform.id),
                "transform_variable_mapping": mapping("short"),
            },
        )
        assert status_code == 200

        def changed_at():
            db_session = override_get_db_session()
            row = db_session.get(DatabaseContinuousEval, continuous_eval.id)
            db_session.refresh(row)
            return row.judge_changed_at

        for transform_variable, reset in (("short", False), ("long", True)):
            status_code, _ = client.update_continuous_eval(
                continuous_eval_id=continuous_eval.id,
                continuous_eval_data={
                    "transform_variable_mapping": mapping(transform_variable),
                },
            )
            assert status_code == 200
            assert (changed_at() is not None) == reset

        # Each eval variable takes one value: two mappings onto it are refused.
        status_code, _ = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={
                "transform_variable_mapping": mapping("short") + mapping("long"),
            },
        )
        assert status_code == 400
    finally:
        client.delete_task(task.id)

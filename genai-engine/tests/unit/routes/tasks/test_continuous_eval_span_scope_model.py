"""The span-scope data model: eval scope settings, run levels on agentic_annotations,
the span-run unique indexes, and trace-level reads that count rollups only."""

import uuid
from datetime import datetime, timedelta
from typing import Optional

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from sqlalchemy.exc import IntegrityError

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.telemetry_models import DatabaseTraceMetadata
from schemas.enums import ContinuousEvalRunLevel
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.unit.routes.tasks.test_continuous_eval_crud_routes import (
    create_test_llm_eval,
    create_test_transform,
)
from tests.unit.routes.transforms.test_transform_span_order import (
    RETRY_TRACE,
    add_trace,
    delete_traces,
)
from utils.constants import DEFAULT_ORG_ID

SPAN_SCOPE = {
    "scope": "span",
    "span_filter": {"span_name": "lookup_order"},
    "rollup_rule": "final_attempt",
}


def _eval_body(transform_id: str, llm_eval_name: str, **extra) -> dict:
    return {
        "name": f"span_scope_{uuid.uuid4().hex[:6]}",
        "llm_eval_name": llm_eval_name,
        "transform_id": transform_id,
        "transform_variable_mapping": [
            {"transform_variable": "test_variable", "eval_variable": "test_variable"},
        ],
        **extra,
    }


def _setup(client: GenaiEngineTestClientBase, name: str):
    status_code, task = client.create_task(name=name, is_agentic=True)
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "span_judge")
    assert status_code == 200
    status_code, transform = create_test_transform(client, task.id)
    assert status_code == 200
    return task, llm_eval, str(transform.id)


def _post_eval(client, task_id, body):
    return client.base_client.post(
        f"/api/v1/tasks/{task_id}/continuous_evals",
        json=body,
        headers=client.authorized_user_api_key_headers,
    )


def _patch_eval(client, eval_id, body):
    return client.base_client.patch(
        f"/api/v1/continuous_evals/{eval_id}",
        json=body,
        headers=client.authorized_user_api_key_headers,
    )


def _add_run(
    continuous_eval_id,
    trace_id: str,
    run_level: ContinuousEvalRunLevel,
    status: ContinuousEvalRunStatus,
    span_id: Optional[str] = None,
    cost: Optional[float] = None,
    test_run_id=None,
) -> uuid.UUID:
    db_session = override_get_db_session()
    row = DatabaseAgenticAnnotation(
        id=uuid.uuid4(),
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL.value,
        trace_id=trace_id,
        continuous_eval_id=continuous_eval_id,
        run_status=status.value,
        annotation_score=(
            1
            if status == ContinuousEvalRunStatus.PASSED
            else 0 if status == ContinuousEvalRunStatus.FAILED else None
        ),
        run_level=run_level.value,
        span_id=span_id,
        cost=cost,
        test_run_id=test_run_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        org_id=DEFAULT_ORG_ID,
    )
    db_session.add(row)
    db_session.commit()
    return row.id


def _delete_runs(continuous_eval_id) -> None:
    db_session = override_get_db_session()
    db_session.query(DatabaseAgenticAnnotation).filter(
        DatabaseAgenticAnnotation.continuous_eval_id == continuous_eval_id,
    ).delete(synchronize_session=False)
    db_session.commit()


@pytest.mark.unit_tests
def test_span_scope_settings_round_trip_and_are_validated(
    client: GenaiEngineTestClientBase,
):
    task, llm_eval, transform_id = _setup(client, "span_scope_settings")
    try:
        # Span scope needs a span filter and an explicit rollup rule.
        for missing in ("span_filter", "rollup_rule"):
            body = _eval_body(transform_id, llm_eval.name, **SPAN_SCOPE)
            body.pop(missing)
            resp = _post_eval(client, task.id, body)
            assert resp.status_code in (400, 422), resp.text
            assert missing in resp.text
        # A trace-scope eval does not accept span settings that would do nothing.
        resp = _post_eval(
            client,
            task.id,
            _eval_body(transform_id, llm_eval.name, span_filter={"span_kind": "TOOL"}),
        )
        assert resp.status_code in (400, 422), resp.text
        # An empty span filter matches nothing on purpose, so it is refused.
        resp = _post_eval(
            client,
            task.id,
            _eval_body(
                transform_id,
                llm_eval.name,
                scope="span",
                span_filter={},
                rollup_rule="any_fail",
            ),
        )
        assert resp.status_code in (400, 422), resp.text

        resp = _post_eval(
            client,
            task.id,
            _eval_body(
                transform_id,
                llm_eval.name,
                max_spans_per_trace=5,
                **SPAN_SCOPE,
            ),
        )
        assert resp.status_code == 200, resp.text
        created = resp.json()
        assert created["scope"] == "span"
        assert created["span_filter"]["span_name"] == "lookup_order"
        assert created["span_filter"]["conditions"] == []
        assert created["rollup_rule"] == "final_attempt"
        assert created["max_spans_per_trace"] == 5

        # Switching back to trace scope drops the span settings.
        resp = _patch_eval(client, created["id"], {"scope": "trace"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["scope"] == "trace"
        # None fields are left out of continuous eval responses.
        assert resp.json().get("span_filter") is None
        assert resp.json().get("rollup_rule") is None
        # And switching to span scope again needs them back.
        resp = _patch_eval(client, created["id"], {"scope": "span"})
        assert resp.status_code == 400, resp.text
        resp = _patch_eval(
            client,
            created["id"],
            {
                "scope": "span",
                "span_filter": {"span_kind": "TOOL"},
                "rollup_rule": "any_fail",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["span_filter"]["span_kind"] == "TOOL"

        # Existing and new trace-scope evals read as trace scope with defaults.
        resp = _post_eval(client, task.id, _eval_body(transform_id, llm_eval.name))
        assert resp.status_code == 200, resp.text
        assert resp.json()["scope"] == "trace"
        assert resp.json()["max_spans_per_trace"] == 20
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_a_span_gets_one_live_run_and_one_per_test_run(
    client: GenaiEngineTestClientBase,
):
    """The partial unique indexes make a retried fan-out safe: a second live span
    run for the same (eval, trace, span) is refused, while rollups, trace runs,
    human labels and test-run span runs are not affected."""
    task, llm_eval, transform_id = _setup(client, "span_scope_unique")
    resp = _post_eval(
        client,
        task.id,
        _eval_body(transform_id, llm_eval.name, **SPAN_SCOPE),
    )
    assert resp.status_code == 200, resp.text
    eval_id = uuid.UUID(resp.json()["id"])
    trace_id = add_trace(task.id, RETRY_TRACE)
    pending = ContinuousEvalRunStatus.PENDING
    try:
        _add_run(eval_id, trace_id, ContinuousEvalRunLevel.SPAN, pending, "call-1")
        with pytest.raises(IntegrityError):
            _add_run(eval_id, trace_id, ContinuousEvalRunLevel.SPAN, pending, "call-1")
        override_get_db_session().rollback()

        _add_run(eval_id, trace_id, ContinuousEvalRunLevel.SPAN, pending, "call-2")
        for _ in range(2):
            _add_run(eval_id, trace_id, ContinuousEvalRunLevel.SPAN_ROLLUP, pending)
            _add_run(eval_id, trace_id, ContinuousEvalRunLevel.TRACE, pending)
    finally:
        _delete_runs(eval_id)
        delete_traces(task.id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_trace_level_reads_count_the_rollup_not_each_span_run(
    client: GenaiEngineTestClientBase,
):
    """A retried call: span run call-1 failed, call-2 passed, the final_attempt
    rollup passed. The trace shows one passing verdict; the failed span run is
    still listed as a span run, and its judge cost still counts."""
    task, llm_eval, transform_id = _setup(client, "span_scope_reads")
    resp = _post_eval(
        client,
        task.id,
        _eval_body(transform_id, llm_eval.name, **SPAN_SCOPE),
    )
    assert resp.status_code == 200, resp.text
    eval_id = uuid.UUID(resp.json()["id"])
    trace_id = add_trace(task.id, RETRY_TRACE)
    db_session = override_get_db_session()
    db_session.get(DatabaseTraceMetadata, trace_id).start_time = datetime.now()
    db_session.commit()
    other_eval_id = None
    try:
        _add_run(
            eval_id,
            trace_id,
            ContinuousEvalRunLevel.SPAN,
            ContinuousEvalRunStatus.FAILED,
            "call-1",
            cost=0.003,
        )
        _add_run(
            eval_id,
            trace_id,
            ContinuousEvalRunLevel.SPAN,
            ContinuousEvalRunStatus.PASSED,
            "call-2",
            cost=0.002,
        )
        rollup_id = _add_run(
            eval_id,
            trace_id,
            ContinuousEvalRunLevel.SPAN_ROLLUP,
            ContinuousEvalRunStatus.PASSED,
        )

        # The trace's annotations relationship holds the rollup only.
        db_session = override_get_db_session()
        db_session.expire_all()
        trace = db_session.get(DatabaseTraceMetadata, trace_id)
        assert [a.id for a in trace.annotations] == [rollup_id]

        # Filtering traces by a failing eval result does not match on a span run.
        status_code, listed = client.trace_api_list_traces_metadata(
            task_ids=[task.id],
            annotation_score=0,
        )
        assert status_code == 200
        assert trace_id not in [t.trace_id for t in listed.traces]
        status_code, listed = client.trace_api_list_traces_metadata(
            task_ids=[task.id],
            annotation_score=1,
        )
        assert trace_id in [t.trace_id for t in listed.traces]

        # Daily analytics: one verdict (the rollup), both judge calls' cost.
        now = datetime.now()
        resp = client.base_client.get(
            f"/api/v1/tasks/{task.id}/continuous_evals/analytics/daily",
            params={
                "start_time": (now - timedelta(days=1)).isoformat(),
                "end_time": (now + timedelta(days=1)).isoformat(),
            },
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 200, resp.text
        (day,) = resp.json()["stats"]
        assert (day["total_count"], day["passed_count"], day["failed_count"]) == (
            1,
            1,
            0,
        )
        assert day["total_cost"] == pytest.approx(0.005)

        # The results list carries run levels and can be narrowed to them.
        resp = client.base_client.get(
            f"/api/v1/tasks/{task.id}/continuous_evals/results",
            params={"run_levels": ["span"]},
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 200, resp.text
        runs = resp.json()["annotations"]
        assert sorted((r["span_id"], r["run_status"]) for r in runs) == [
            ("call-1", "failed"),
            ("call-2", "passed"),
        ]
        assert {r["run_level"] for r in runs} == {"span"}

        # The eval page's request: one eval's trace verdicts. A second eval that
        # judged the same trace stays out, so the trace is listed once.
        resp = _post_eval(client, task.id, _eval_body(transform_id, llm_eval.name))
        assert resp.status_code == 200, resp.text
        other_eval_id = uuid.UUID(resp.json()["id"])
        other_run_id = _add_run(
            other_eval_id,
            trace_id,
            ContinuousEvalRunLevel.TRACE,
            ContinuousEvalRunStatus.PASSED,
        )
        for listed_eval_id, expected_ids in (
            (eval_id, [str(rollup_id)]),
            (other_eval_id, [str(other_run_id)]),
        ):
            resp = client.base_client.get(
                f"/api/v1/tasks/{task.id}/continuous_evals/results",
                params={
                    "continuous_eval_ids": [str(listed_eval_id)],
                    "run_levels": ["trace", "span_rollup"],
                    "page": 0,
                    "page_size": 10,
                },
                headers=client.authorized_user_api_key_headers,
            )
            assert resp.status_code == 200, resp.text
            assert [r["id"] for r in resp.json()["annotations"]] == expected_ids
    finally:
        _delete_runs(eval_id)
        if other_eval_id is not None:
            _delete_runs(other_eval_id)
        delete_traces(task.id)
        client.delete_task(task.id)

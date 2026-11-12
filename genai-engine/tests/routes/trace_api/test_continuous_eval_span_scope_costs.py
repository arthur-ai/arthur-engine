"""Cost paths for span-scope continuous evals: the spend estimate, the daily cap
and reruns. Same retry trace as test_continuous_eval_span_scope: call-1 timed out
and the mocked judge fails it, call-2 succeeded and passes."""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from litellm.types.utils import ModelResponse

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.telemetry_models import DatabaseTraceMetadata
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from schemas.enums import ContinuousEvalRunLevel
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.test_continuous_eval_execution import (
    mock_get_db_session_generator,
)
from tests.routes.trace_api.test_continuous_eval_span_scope import (
    WORKER,
    SyncQueue,
    _cleanup,
    _judge_reply,
    _runs,
    _setup_eval,
)
from tests.unit.routes.transforms.test_transform_span_order import (
    RETRY_TRACE,
    add_trace,
)
from utils.constants import DEFAULT_ORG_ID

SPAN = ContinuousEvalRunLevel.SPAN
ROLLUP = ContinuousEvalRunLevel.SPAN_ROLLUP


def _judge_passes_everything(*args, **kwargs):
    response = MagicMock(spec=ModelResponse)
    response.choices = [MagicMock()]
    response.choices[0].message = {
        "content": json.dumps({"reason": "Fine now.", "score": 1, "label": None}),
    }
    return response


def _recent_trace(task_id: str) -> str:
    """The retry trace, started now so it falls inside the estimate window."""
    trace_id = add_trace(task_id, RETRY_TRACE)
    db_session = override_get_db_session()
    db_session.get(DatabaseTraceMetadata, trace_id).start_time = datetime.now()
    db_session.commit()
    return trace_id


def _add_run(eval_id, trace_id, level, status, span_id=None, cost=None):
    db_session = override_get_db_session()
    db_session.add(
        DatabaseAgenticAnnotation(
            id=uuid.uuid4(),
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL.value,
            trace_id=trace_id,
            continuous_eval_id=eval_id,
            run_status=status.value,
            run_level=level.value,
            span_id=span_id,
            cost=cost,
            created_at=datetime.now() - timedelta(hours=1),
            updated_at=datetime.now() - timedelta(hours=1),
            org_id=DEFAULT_ORG_ID,
        ),
    )
    db_session.commit()


def _enqueue(task_id: str, trace_id: str) -> None:
    ContinuousEvalsRepository(
        override_get_db_session(),
    )._enqueue_continuous_evals_for_trace(trace_id, task_id, delay_seconds=0)


@pytest.mark.unit_tests
def test_live_estimate_prices_span_runs_and_counts_traces_by_rollup(
    client: GenaiEngineTestClientBase,
):
    """3 traces in 7 days, 2 rollups judged and 1 skipped (judged share 2/3),
    4 span runs at $0.01 (2 judged spans per judged trace):
    3/7 traces/day x 1.0 x 2/3 x 2 x $0.01. The rollups are not unpriced runs."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        traces = [_recent_trace(task.id) for _ in range(3)]
        for trace_id in traces[:2]:
            _add_run(eval_id, trace_id, ROLLUP, ContinuousEvalRunStatus.PASSED)
            for span_id in ("call-1", "call-2"):
                _add_run(
                    eval_id,
                    trace_id,
                    SPAN,
                    ContinuousEvalRunStatus.PASSED,
                    span_id,
                    cost=0.01,
                )
        _add_run(eval_id, traces[2], ROLLUP, ContinuousEvalRunStatus.SKIPPED)

        status_code, spend = client.get_continuous_eval_spend(str(eval_id))
        assert status_code == 200
        assert spend.last_24h_run_count == 4
        assert spend.last_24h_cost == pytest.approx(0.04)
        estimate = spend.estimate
        assert estimate.run_count == 4
        assert estimate.unpriced_run_count == 0
        assert estimate.average_run_cost == pytest.approx(0.01)
        assert estimate.judged_share == pytest.approx(2 / 3)
        assert estimate.spans_per_trace == pytest.approx(2.0)
        assert estimate.estimated_daily_cost == pytest.approx(3 / 7 * 2 / 3 * 2 * 0.01)
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
def test_new_span_scope_estimate_multiplies_by_matching_spans_per_trace(
    client: GenaiEngineTestClientBase,
):
    """Priced at $0.01 a judge call from the evaluator's existing runs. Two recent
    retry traces have 2 lookup_order spans each, a third has none: 4/3 spans per
    trace, or 2/3 when max_spans_per_trace is 1."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        traces = [_recent_trace(task.id) for _ in range(2)]
        other = add_trace(
            task.id,
            [
                {
                    "span_id": "root",
                    "span_name": "agent",
                    "span_kind": "AGENT",
                    "offset_s": 0,
                },
            ],
        )
        db_session = override_get_db_session()
        db_session.get(DatabaseTraceMetadata, other).start_time = datetime.now()
        db_session.commit()
        _add_run(eval_id, traces[0], ROLLUP, ContinuousEvalRunStatus.PASSED)
        _add_run(
            eval_id,
            traces[0],
            SPAN,
            ContinuousEvalRunStatus.PASSED,
            "call-1",
            0.01,
        )

        def estimate(**params):
            resp = client.base_client.get(
                f"/api/v1/tasks/{task.id}/continuous_evals/spend_estimate",
                params={"llm_eval_name": "tool_call_judge", **params},
                headers=client.authorized_user_api_key_headers,
            )
            assert resp.status_code == 200, resp.text
            return resp.json()

        span_filter = json.dumps({"span_name": "lookup_order"})
        body = estimate(span_filter=span_filter)
        assert body["average_run_cost"] == pytest.approx(0.01)
        assert body["unpriced_run_count"] == 0
        assert body["spans_per_trace"] == pytest.approx(4 / 3)
        assert body["filter_traces_checked"] == 3
        assert body["estimated_daily_cost"] == pytest.approx(3 / 7 * 4 / 3 * 0.01)

        capped = estimate(span_filter=span_filter, max_spans_per_trace=1)
        assert capped["spans_per_trace"] == pytest.approx(2 / 3)

        resp = client.base_client.get(
            f"/api/v1/tasks/{task.id}/continuous_evals/spend_estimate",
            params={"llm_eval_name": "tool_call_judge", "span_filter": "{}"},
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 400, resp.text
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_cap_reached_skips_the_whole_trace_at_fan_out(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    task, eval_id = _setup_eval(client, "any_fail", daily_cost_cap_usd=0.01)
    queue = SyncQueue()
    try:
        spent = _recent_trace(task.id)
        _add_run(eval_id, spent, SPAN, ContinuousEvalRunStatus.PASSED, "call-1", 0.02)
        db_session = override_get_db_session()
        db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.continuous_eval_id == eval_id,
        ).update({"updated_at": datetime.now()})
        db_session.commit()

        trace_id = _recent_trace(task.id)
        _enqueue(task.id, trace_id)
        assert queue.drain() == 1
        runs = _runs(eval_id, trace_id)
        assert runs["span"] == []
        assert runs["span_rollup"][0].run_status == "skipped"
        assert "Daily spend cap" in runs["span_rollup"][0].annotation_description
        mock_completion.assert_not_called()
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch("services.continuous_eval.span_scope.SPAN_SCOPE_CAP_CHECK_AT", "span_run")
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_cap_checked_before_each_span_run_stops_mid_trace(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """The alternative behind the seam: a $0.001 cap lets the first span run
    ($0.002) through and skips the second; the judged failure still decides."""
    task, eval_id = _setup_eval(client, "final_attempt", daily_cost_cap_usd=0.001)
    queue = SyncQueue()
    try:
        trace_id = _recent_trace(task.id)
        _enqueue(task.id, trace_id)
        assert queue.drain() == 3
        call_1, call_2 = _runs(eval_id, trace_id)["span"]
        assert (call_1.run_status, call_2.run_status) == ("failed", "skipped")
        assert mock_completion.call_count == 1
        rollup = _runs(eval_id, trace_id)["span_rollup"][0]
        assert (rollup.run_status, rollup.label) == ("failed", "tool_error")
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_rerun_a_span_run_redecides_its_rollup(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        trace_id = _recent_trace(task.id)
        _enqueue(task.id, trace_id)
        queue.drain()
        call_1 = _runs(eval_id, trace_id)["span"][0]
        assert _runs(eval_id, trace_id)["span_rollup"][0].run_status == "failed"

        # The tool's failure turns out to be the judge's mistake; rerun it.
        mock_completion.side_effect = _judge_passes_everything
        status_code, _ = client.rerun_continuous_eval(str(call_1.id))
        assert status_code == 200
        rollup = _runs(eval_id, trace_id)["span_rollup"][0]
        assert rollup.run_status == "running"
        assert queue.drain() == 1
        runs = _runs(eval_id, trace_id)
        assert [r.run_status for r in runs["span"]] == ["passed", "passed"]
        assert runs["span"][0].cost == pytest.approx(0.004)
        assert (runs["span_rollup"][0].run_status, runs["span_rollup"][0].label) == (
            "passed",
            None,
        )
        assert mock_completion.call_count == 3
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_rerun_a_rollup_rejudges_only_the_span_runs_that_did_not_pass(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        trace_id = _recent_trace(task.id)
        _enqueue(task.id, trace_id)
        queue.drain()
        rollup = _runs(eval_id, trace_id)["span_rollup"][0]
        assert rollup.run_status == "failed"

        mock_completion.side_effect = _judge_passes_everything
        status_code, _ = client.rerun_continuous_eval(str(rollup.id))
        assert status_code == 200
        # The rollup job, then the one span run that failed.
        assert queue.drain() == 2
        runs = _runs(eval_id, trace_id)
        assert [r.run_status for r in runs["span"]] == ["passed", "passed"]
        assert runs["span_rollup"][0].run_status == "passed"
        assert mock_completion.call_count == 3
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_rerun_in_a_test_run_moves_the_trace_between_counters(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        trace_id = _recent_trace(task.id)
        status_code, test_run = client.create_test_run(str(eval_id), [trace_id])
        assert status_code == 200
        queue.drain()
        status_code, test_run = client.get_test_run(str(test_run.id))
        assert (test_run.completed_count, test_run.failed_count) == (1, 1)

        db_session = override_get_db_session()
        call_1 = (
            db_session.query(DatabaseAgenticAnnotation)
            .filter(
                DatabaseAgenticAnnotation.test_run_id == test_run.id,
                DatabaseAgenticAnnotation.span_id == "call-1",
            )
            .one()
        )
        mock_completion.side_effect = _judge_passes_everything
        status_code, _ = client.rerun_continuous_eval(str(call_1.id))
        assert status_code == 200
        queue.drain()
        status_code, test_run = client.get_test_run(str(test_run.id))
        assert (
            test_run.completed_count,
            test_run.passed_count,
            test_run.failed_count,
        ) == (1, 1, 0)
        assert test_run.status == "completed"
    finally:
        _cleanup(client, task, eval_id, queue)


def _judge_fails_everything(*args, **kwargs):
    response = MagicMock(spec=ModelResponse)
    response.choices = [MagicMock()]
    response.choices[0].message = {
        "content": json.dumps({"reason": "Broken.", "score": 0, "label": None}),
    }
    return response


def _patch_eval(client: GenaiEngineTestClientBase, eval_id: uuid.UUID, body: dict):
    resp = client.base_client.patch(
        f"/api/v1/continuous_evals/{eval_id}",
        json=body,
        headers=client.authorized_user_api_key_headers,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch(
    "clients.llm.llm_client.litellm.completion",
    side_effect=_judge_fails_everything,
)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_rerun_after_lowering_max_spans_skips_the_span_runs_past_it(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Both calls failed and the rerun reopens both, but the eval now judges one
    span per trace. The other span run is skipped, not left pending, so the
    rollup finishes."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        trace_id = _recent_trace(task.id)
        _enqueue(task.id, trace_id)
        queue.drain()
        rollup = _runs(eval_id, trace_id)["span_rollup"][0]
        assert rollup.run_status == "failed"

        _patch_eval(client, eval_id, {"max_spans_per_trace": 1})
        status_code, _ = client.rerun_continuous_eval(str(rollup.id))
        assert status_code == 200
        # The rollup job, then call-1's span run only.
        assert queue.drain() == 2
        call_1, call_2 = _runs(eval_id, trace_id)["span"]
        assert call_1.run_status == "failed"
        assert call_2.run_status == "skipped"
        assert "no longer among those the eval judges" in (
            call_2.annotation_description
        )
        rollup = _runs(eval_id, trace_id)["span_rollup"][0]
        assert rollup.run_status == "failed"
        assert mock_completion.call_count == 3
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch(
    "clients.llm.llm_client.litellm.completion",
    side_effect=_judge_fails_everything,
)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_rerun_after_the_trace_filter_stops_matching_skips_the_span_runs(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """The rollup is skipped by the new trace filter, and so are the span runs the
    rerun reopened: none is left pending for the stale sweep to judge later."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        trace_id = _recent_trace(task.id)
        _enqueue(task.id, trace_id)
        queue.drain()
        rollup = _runs(eval_id, trace_id)["span_rollup"][0]

        _patch_eval(
            client,
            eval_id,
            {
                "trace_filter": [
                    {
                        "attribute_path": "attributes.metadata.plan",
                        "operator": "equals",
                        "value": "paid",
                    },
                ],
            },
        )
        status_code, _ = client.rerun_continuous_eval(str(rollup.id))
        assert status_code == 200
        assert queue.drain() == 1
        runs = _runs(eval_id, trace_id)
        assert runs["span_rollup"][0].run_status == "skipped"
        assert [r.run_status for r in runs["span"]] == ["skipped", "skipped"]
        assert mock_completion.call_count == 2
    finally:
        _cleanup(client, task, eval_id, queue)

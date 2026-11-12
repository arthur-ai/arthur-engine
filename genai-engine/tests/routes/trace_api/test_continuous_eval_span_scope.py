"""A span-scope continuous eval end to end in the worker: fan-out to one span run
per matching span, one judge call each, and the rollup decided by the eval's rule.

The trace is the retry case: lookup_order fails with a timeout (call-1), the agent
calls it again and it succeeds (call-2). The mocked judge fails any call whose
output is the timeout.
"""

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import ContinuousEvalRunStatus
from litellm.types.utils import ModelResponse

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseSpan
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from schemas.enums import ContinuousEvalRunLevel
from services.continuous_eval import (
    ContinuousEvalJob,
    get_continuous_eval_queue_service,
    initialize_continuous_eval_queue_service,
    shutdown_continuous_eval_queue_service,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.test_continuous_eval_execution import (
    cleanup_model_provider,
    mock_get_db_session_generator,
)
from tests.unit.routes.transforms.test_transform_span_order import (
    RETRY_TRACE,
    add_trace,
    delete_traces,
)

WORKER = "services.continuous_eval.continuous_eval_queue_service"
UNFINISHED = (
    ContinuousEvalRunStatus.PENDING.value,
    ContinuousEvalRunStatus.RUNNING.value,
)


def _judge_reply(*args, **kwargs):
    """Fails a tool call whose output is the upstream timeout, passes the rest."""
    prompt = json.dumps(kwargs.get("messages", ""))
    failed = "upstream timeout" in prompt
    response = MagicMock(spec=ModelResponse)
    response.choices = [MagicMock()]
    response.choices[0].message = {
        "content": json.dumps(
            {
                "reason": "The call timed out." if failed else "The call worked.",
                "score": 0 if failed else 1,
                "label": "tool_error" if failed else None,
            },
        ),
    }
    return response


def _setup_eval(client: GenaiEngineTestClientBase, rollup_rule: str, **extra):
    status_code, task = client.create_task(
        name=f"span_scope_{rollup_rule}",
        is_agentic=True,
    )
    assert status_code == 200
    try:
        response = client.base_client.put(
            "/api/v1/model_providers/openai",
            json={"api_key": "test-key"},
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 201
        status_code, _ = client.save_llm_eval(
            task_id=task.id,
            llm_eval_name="tool_call_judge",
            llm_eval_data={
                "model_name": "gpt-4o",
                "model_provider": "openai",
                "instructions": "Did this tool call work? {{tool_output}}",
            },
        )
        assert status_code == 200
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="judged span",
            description="the tool call being judged",
            definition={
                "variables": [
                    {
                        "variable_name": "tool_output",
                        "attribute_path": "attributes.output.value",
                        "span_selector": "current",
                    },
                ],
            },
        )
        assert status_code == 200, transform
        resp = client.base_client.post(
            f"/api/v1/tasks/{task.id}/continuous_evals",
            json={
                "name": "tool calls",
                "llm_eval_name": "tool_call_judge",
                "llm_eval_version": 1,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "tool_output",
                        "eval_variable": "tool_output",
                    },
                ],
                "scope": "span",
                "span_filter": {"span_name": "lookup_order"},
                "rollup_rule": rollup_rule,
                **extra,
            },
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 200, resp.text
        eval_id = uuid.UUID(resp.json()["id"])
    except BaseException:
        # A failed step leaves no task or provider behind for later tests.
        client.delete_task(task.id)
        cleanup_model_provider(client)
        raise
    return task, eval_id


def _runs(
    eval_id: uuid.UUID,
    trace_id: str,
) -> dict[str, list[DatabaseAgenticAnnotation]]:
    db_session = override_get_db_session()
    db_session.expire_all()
    rows = (
        db_session.query(DatabaseAgenticAnnotation)
        .filter(
            DatabaseAgenticAnnotation.continuous_eval_id == eval_id,
            DatabaseAgenticAnnotation.trace_id == trace_id,
        )
        .all()
    )
    by_level: dict[str, list[DatabaseAgenticAnnotation]] = {
        level.value: [] for level in ContinuousEvalRunLevel
    }
    for row in rows:
        by_level[row.run_level].append(row)
    by_level["span"].sort(key=lambda r: r.span_id)
    return by_level


class SyncQueue:
    """Collects the jobs the code under test enqueues and runs them one by one on
    the test thread: the SQLite test session must not be shared across threads."""

    def __init__(self):
        initialize_continuous_eval_queue_service(
            num_workers=1,
            override_execution_delay=0,
        )
        self.service = get_continuous_eval_queue_service()
        self.jobs: list[ContinuousEvalJob] = []
        self._patch = patch.object(self.service, "enqueue", side_effect=self._enqueue)
        self._patch.start()

    def _enqueue(self, job):
        self.jobs.append(job)
        return True, None

    def drain(self) -> int:
        ran = 0
        while self.jobs:
            self.service._execute_job(self.jobs.pop(0))
            ran += 1
        return ran

    def close(self):
        self._patch.stop()
        shutdown_continuous_eval_queue_service()


def _finished_rollup(eval_id: uuid.UUID, trace_id: str) -> DatabaseAgenticAnnotation:
    (rollup,) = _runs(eval_id, trace_id)["span_rollup"]
    assert rollup.run_status not in UNFINISHED, rollup.annotation_description
    return rollup


def _cleanup(client, task, eval_id, queue):
    db_session = override_get_db_session()
    # A failed setup step may have left the shared session in a failed transaction.
    db_session.rollback()
    db_session.query(DatabaseAgenticAnnotation).filter(
        DatabaseAgenticAnnotation.continuous_eval_id == eval_id,
    ).delete(synchronize_session=False)
    db_session.commit()
    delete_traces(task.id)
    client.delete_task(task.id)
    queue.close()
    cleanup_model_provider(client)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("rollup_rule", "rollup_status", "rollup_label"),
    [
        # The retry recovered, so the trace passes; the failed call keeps its verdict.
        ("final_attempt", "passed", None),
        # Any failing call fails the trace (e.g. a PII check).
        ("any_fail", "failed", "tool_error"),
    ],
)
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_span_scope_judges_each_call_and_rolls_up_by_rule(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    rollup_rule,
    rollup_status,
    rollup_label,
    client: GenaiEngineTestClientBase,
):
    task, eval_id = _setup_eval(client, rollup_rule)
    queue = SyncQueue()
    trace_id = add_trace(task.id, RETRY_TRACE)
    expected_jobs = 3
    try:
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        # The rollup job, then one job per span run it queued.
        assert queue.drain() == expected_jobs
        rollup = _finished_rollup(eval_id, trace_id)
        runs = _runs(eval_id, trace_id)

        # One judge call per lookup_order span, none for the agent span or rollup.
        assert mock_completion.call_count == 2
        assert runs["trace"] == []
        call_1, call_2 = runs["span"]
        assert (call_1.span_id, call_1.run_status, call_1.label) == (
            "call-1",
            "failed",
            "tool_error",
        )
        assert (call_2.span_id, call_2.run_status, call_2.label) == (
            "call-2",
            "passed",
            None,
        )
        # Each span run read its own span through the 'current' selector.
        assert call_1.input_variables == [
            {"name": "tool_output", "value": "upstream timeout"},
        ]
        assert call_2.input_variables == [{"name": "tool_output", "value": "delivered"}]
        assert call_1.cost == call_2.cost == pytest.approx(0.002)
        assert call_1.judged_span_count == call_2.judged_span_count == 3

        assert rollup.run_status == rollup_status
        assert rollup.label == rollup_label
        assert rollup.cost is None
        assert rollup.span_id is None
        assert rollup.judged_span_count == 3
        assert "1 of 2 judged spans passed" in rollup.annotation_description
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_a_repeated_fan_out_reuses_span_runs_and_judges_nothing_twice(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    task, eval_id = _setup_eval(client, "final_attempt")
    queue = SyncQueue()
    trace_id = add_trace(task.id, RETRY_TRACE)
    expected_jobs = 3
    try:
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        # The rollup job, then one job per span run it queued.
        assert queue.drain() == expected_jobs
        rollup = _finished_rollup(eval_id, trace_id)
        assert mock_completion.call_count == 2

        # A stale-run recovery or retry runs the rollup job again.
        db_session = override_get_db_session()
        db_session.get(DatabaseAgenticAnnotation, rollup.id).run_status = "pending"
        db_session.commit()
        queue.service._execute_job(
            ContinuousEvalJob(
                annotation_id=rollup.id,
                trace_id=trace_id,
                continuous_eval_id=eval_id,
                task_id=task.id,
                delay_seconds=0,
            ),
        )
        # Both span runs are already judged, so nothing new is queued.
        assert queue.drain() == 0
        runs = _runs(eval_id, trace_id)
        assert [r.span_id for r in runs["span"]] == ["call-1", "call-2"]
        assert runs["span_rollup"][0].run_status == "passed"
        assert mock_completion.call_count == 2
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 60)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_fan_out_waits_while_the_trace_is_still_receiving_spans(
    mock_get_db_session,
    mock_completion,
    client: GenaiEngineTestClientBase,
):
    """Spans stored just now: the rollup job asks to run again once the trace has
    been quiet for the idle window, and creates no span runs yet."""
    task, eval_id = _setup_eval(client, "final_attempt")
    queue = SyncQueue()
    trace_id = add_trace(task.id, RETRY_TRACE)
    try:
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=3600)
        (rollup,) = _runs(eval_id, trace_id)["span_rollup"]
        job = ContinuousEvalJob(
            annotation_id=rollup.id,
            trace_id=trace_id,
            continuous_eval_id=eval_id,
            task_id=task.id,
            delay_seconds=0,
        )
        queue.service._execute_job(job)
        assert 0 < job.requeue_in <= 60
        runs = _runs(eval_id, trace_id)
        assert runs["span"] == []
        assert runs["span_rollup"][0].run_status == "pending"
        mock_completion.assert_not_called()
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_max_spans_per_trace_judges_the_first_spans_in_tree_order(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    task, eval_id = _setup_eval(client, "any_fail", max_spans_per_trace=1)
    queue = SyncQueue()
    trace_id = add_trace(task.id, RETRY_TRACE)
    expected_jobs = 2
    try:
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        # The rollup job, then one job per span run it queued.
        assert queue.drain() == expected_jobs
        rollup = _finished_rollup(eval_id, trace_id)
        assert [r.span_id for r in _runs(eval_id, trace_id)["span"]] == ["call-1"]
        assert mock_completion.call_count == 1
        assert rollup.run_status == "failed"
        assert "1 more matching spans past max_spans_per_trace" in (
            rollup.annotation_description
        )
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 3600)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_a_test_run_counts_each_trace_once_through_its_rollup(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Two span runs, one trace: the test run counts one finished trace. A test
    run picks finished traces, so it skips the idle window (set to an hour here)."""
    task, eval_id = _setup_eval(client, "final_attempt")
    queue = SyncQueue()
    trace_id = add_trace(task.id, RETRY_TRACE)
    try:
        status_code, test_run = client.create_test_run(str(eval_id), [trace_id])
        assert status_code == 200, test_run
        assert queue.drain() == 3
        status_code, test_run = client.get_test_run(str(test_run.id))
        assert (
            test_run.total_count,
            test_run.completed_count,
            test_run.passed_count,
            test_run.failed_count,
        ) == (1, 1, 1, 0)
        assert test_run.status == "completed"
        assert mock_completion.call_count == 2
        # The test run's results list the trace once, through its rollup.
        resp = client.base_client.get(
            f"/api/v1/continuous_evals/test_runs/{test_run.id}/results",
            headers=client.authorized_user_api_key_headers,
        )
        assert resp.status_code == 200, resp.text
        assert [a["run_level"] for a in resp.json()["annotations"]] == ["span_rollup"]
        assert resp.json()["count"] == 1
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_a_span_stored_twice_is_judged_once(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """An exporter re-sent call-1, so the spans table has two rows for it. The
    fan-out still makes one span run per span id and decides the trace."""
    task, eval_id = _setup_eval(client, "final_attempt")
    queue = SyncQueue()
    try:
        trace_id = add_trace(task.id, RETRY_TRACE)
        db_session = override_get_db_session()
        original = (
            db_session.query(DatabaseSpan)
            .filter(
                DatabaseSpan.trace_id == trace_id,
                DatabaseSpan.span_id == "call-1",
            )
            .one()
        )
        db_session.add(
            DatabaseSpan(
                id=uuid.uuid4().hex,
                trace_id=trace_id,
                span_id="call-1",
                parent_span_id=original.parent_span_id,
                span_name=original.span_name,
                span_kind=original.span_kind,
                start_time=original.start_time,
                end_time=original.end_time,
                task_id=task.id,
                org_id=original.org_id,
                raw_data=original.raw_data,
            ),
        )
        db_session.commit()
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        assert queue.drain() == 3
        runs = _runs(eval_id, trace_id)
        assert [r.span_id for r in runs["span"]] == ["call-1", "call-2"]
        assert runs["span_rollup"][0].run_status == "passed"
        assert mock_completion.call_count == 2
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_a_transform_that_stops_reading_the_judged_span_skips_the_trace(
    mock_get_db_session,
    mock_completion,
    client: GenaiEngineTestClientBase,
):
    """An eval following the latest transform version can lose its 'current'
    variable after it was created. Every span run would then send the judge the
    same input, so the trace is skipped and no span run is made."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        _point_eval_at_a_fixed_span_transform(client, task.id, eval_id)
        trace_id = add_trace(task.id, RETRY_TRACE)
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        assert queue.drain() == 1
        runs = _runs(eval_id, trace_id)
        assert runs["span"] == []
        (rollup,) = runs["span_rollup"]
        assert rollup.run_status == "skipped"
        assert "reads the judged span" in rollup.annotation_description
        assert mock_completion.call_count == 0
    finally:
        _cleanup(client, task, eval_id, queue)


def _point_eval_at_a_fixed_span_transform(client, task_id, eval_id) -> None:
    """Bypasses the API's check, as a later transform edit would."""
    status_code, same_for_every_span = client.create_transform(
        task_id=task_id,
        name="last tool call",
        description="reads one fixed span",
        definition={
            "variables": [
                {
                    "variable_name": "tool_output",
                    "span_name": "lookup_order",
                    "span_selector": "last",
                    "attribute_path": "attributes.output.value",
                },
            ],
        },
    )
    assert status_code == 200
    db_session = override_get_db_session()
    db_session.get(DatabaseContinuousEval, eval_id).transform_id = (
        same_for_every_span.id
    )
    db_session.commit()


@pytest.mark.unit_tests
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_worker_start_requeues_rollups_waiting_for_their_trace(
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """A rollup waiting out the idle window lives in the in-memory scheduler,
    which a restart empties. The worker re-queues pending rollups when it starts,
    whatever their age; the hourly sweep only takes runs older than 15 minutes."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        trace_id = add_trace(task.id, RETRY_TRACE)
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        (rollup,) = _runs(eval_id, trace_id)["span_rollup"]
        queue.jobs.clear()  # the restart dropped it

        queue.service._check_stale_annotations()
        assert queue.jobs == []

        queue.service._check_stale_annotations(include_pending_rollups=True)
        assert [job.annotation_id for job in queue.jobs] == [rollup.id]
        queue.jobs.clear()

        # The background thread does this one idle window after it starts,
        # before its first hourly wait.
        with (
            patch(f"{WORKER}.STARTUP_SWEEP_DELAY_SECONDS", 0),
            patch.object(
                queue.service,
                "_check_stale_annotations",
                side_effect=lambda **_: queue.service.shutdown_event.set(),
            ) as sweep,
        ):
            queue.service._background_loop()
        sweep.assert_called_once_with(include_pending_rollups=True)
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_another_tasks_span_under_the_same_trace_id_is_not_judged(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """A lookup_order span stored under the same trace id by another task matches
    the span filter, but it is not this eval's to judge or send to the judge."""
    task, eval_id = _setup_eval(client, "final_attempt")
    queue = SyncQueue()
    status_code, other_task = client.create_task(
        name="span_scope_other_task",
        is_agentic=True,
    )
    assert status_code == 200
    try:
        trace_id = add_trace(task.id, RETRY_TRACE)
        db_session = override_get_db_session()
        call_2 = (
            db_session.query(DatabaseSpan)
            .filter(
                DatabaseSpan.trace_id == trace_id,
                DatabaseSpan.span_id == "call-2",
            )
            .one()
        )
        db_session.add(
            DatabaseSpan(
                id=uuid.uuid4().hex,
                trace_id=trace_id,
                span_id="other-task-call",
                parent_span_id=call_2.parent_span_id,
                span_name=call_2.span_name,
                span_kind=call_2.span_kind,
                start_time=call_2.start_time,
                end_time=call_2.end_time,
                task_id=other_task.id,
                org_id=call_2.org_id,
                raw_data=call_2.raw_data,
            ),
        )
        db_session.commit()
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        assert queue.drain() == 3
        runs = _runs(eval_id, trace_id)
        assert [r.span_id for r in runs["span"]] == ["call-1", "call-2"]
        assert runs["span_rollup"][0].judged_span_count == 3
        assert mock_completion.call_count == 2
    finally:
        db_session = override_get_db_session()
        db_session.rollback()
        db_session.query(DatabaseSpan).filter(
            DatabaseSpan.task_id == other_task.id,
        ).delete(synchronize_session=False)
        db_session.commit()
        client.delete_task(other_task.id)
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 0)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_span_runs_queued_before_the_transform_changed_are_skipped(
    mock_get_db_session,
    mock_completion,
    client: GenaiEngineTestClientBase,
):
    """The fan-out checked the transform and queued both span runs; then the
    transform stopped reading the judged span. Each span run checks again and is
    skipped instead of judging the wrong span."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    try:
        trace_id = add_trace(task.id, RETRY_TRACE)
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        queue.service._execute_job(queue.jobs.pop(0))  # the fan-out
        assert len(queue.jobs) == 2

        _point_eval_at_a_fixed_span_transform(client, task.id, eval_id)
        assert queue.drain() == 2
        runs = _runs(eval_id, trace_id)
        assert [r.run_status for r in runs["span"]] == ["skipped", "skipped"]
        assert all(
            "reads the judged span" in r.annotation_description for r in runs["span"]
        )
        assert runs["span_rollup"][0].run_status == "skipped"
        assert mock_completion.call_count == 0
    finally:
        _cleanup(client, task, eval_id, queue)


@pytest.mark.unit_tests
@patch(f"{WORKER}.SPAN_SCOPE_IDLE_SECONDS", 60)
@patch("clients.llm.llm_client.completion_cost", return_value=0.002)
@patch("clients.llm.llm_client.litellm.completion", side_effect=_judge_reply)
@patch(f"{WORKER}.get_db_session", side_effect=mock_get_db_session_generator)
def test_idle_wait_and_span_run_order_ignore_other_tasks_and_query_order(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """The trace's own spans arrived an hour ago; another task just stored a span
    under the same trace id. The trace is idle for this eval, so it fans out now,
    and span runs come back in the order of the spans asked for."""
    task, eval_id = _setup_eval(client, "any_fail")
    queue = SyncQueue()
    status_code, other_task = client.create_task(
        name="span_scope_other_idle",
        is_agentic=True,
    )
    assert status_code == 200
    try:
        trace_id = add_trace(task.id, RETRY_TRACE)
        db_session = override_get_db_session()
        db_session.query(DatabaseSpan).filter(
            DatabaseSpan.trace_id == trace_id,
        ).update(
            {"created_at": datetime.now() - timedelta(hours=1)},
            synchronize_session=False,
        )
        agent = (
            db_session.query(DatabaseSpan)
            .filter(DatabaseSpan.trace_id == trace_id, DatabaseSpan.span_id == "root")
            .one()
        )
        db_session.add(
            DatabaseSpan(
                id=uuid.uuid4().hex,
                trace_id=trace_id,
                span_id="other-task-root",
                span_name=agent.span_name,
                start_time=agent.start_time,
                end_time=agent.end_time,
                task_id=other_task.id,
                org_id=agent.org_id,
                raw_data=agent.raw_data,
            ),
        )
        db_session.commit()
        ContinuousEvalsRepository(
            override_get_db_session(),
        )._enqueue_continuous_evals_for_trace(trace_id, task.id, delay_seconds=0)
        rollup_job = queue.jobs.pop(0)
        queue.service._execute_job(rollup_job)
        assert rollup_job.requeue_in is None
        assert len(queue.jobs) == 2

        (rollup,) = _runs(eval_id, trace_id)["span_rollup"]
        spans = queue.service._load_spans(db_session, trace_id, task.id)
        lookups = [span for span in spans if span.span_name == "lookup_order"]
        for order in (lookups, lookups[::-1]):
            runs = queue.service._ensure_span_runs(db_session, rollup, order)
            assert [r.span_id for r in runs] == [span.span_id for span in order]
    finally:
        db_session = override_get_db_session()
        db_session.rollback()
        db_session.query(DatabaseSpan).filter(
            DatabaseSpan.task_id == other_task.id,
        ).delete(synchronize_session=False)
        db_session.commit()
        client.delete_task(other_task.id)
        _cleanup(client, task, eval_id, queue)

import json
import uuid
from datetime import datetime, timedelta
from typing import Optional

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from repositories.continuous_eval_spend_repository import (
    ContinuousEvalSpendRepository,
)
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from schemas.enums import SpendEstimateUnavailableReason
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.unit.routes.tasks.test_continuous_eval_crud_routes import (
    create_test_llm_eval,
    create_test_transform,
)
from utils.constants import (
    AGENT_EXPERIMENT_SESSION_PREFIX,
    DEFAULT_ORG_ID,
    EXPECTED_SPAN_VERSION,
    SPAN_VERSION_KEY,
)


def _create_continuous_eval(
    client: GenaiEngineTestClientBase,
    task_id: str,
    llm_eval_name: str,
    sample_rate: Optional[float],
    transform_id: Optional[str] = None,
):
    if transform_id is None:
        status_code, transform = create_test_transform(client, task_id)
        assert status_code == 200
        transform_id = str(transform.id)
    data = {
        "name": f"spend_{llm_eval_name}",
        "llm_eval_name": llm_eval_name,
        "transform_id": transform_id,
        "transform_variable_mapping": [
            {"transform_variable": "test_variable", "eval_variable": "test_variable"},
        ],
    }
    if sample_rate is not None:
        data["sample_rate"] = sample_rate
    status_code, continuous_eval = client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data=data,
    )
    assert status_code == 200
    return continuous_eval, transform_id


def _add_traces(
    task_id: str,
    start_times: list[datetime],
    session_id: Optional[str] = None,
) -> list[str]:
    db_session = override_get_db_session()
    trace_ids = []
    for start_time in start_times:
        trace_id = uuid.uuid4().hex
        db_session.add(
            DatabaseTraceMetadata(
                task_id=task_id,
                org_id=DEFAULT_ORG_ID,
                trace_id=trace_id,
                session_id=session_id,
                span_count=1,
                start_time=start_time,
                end_time=start_time,
                created_at=start_time,
                updated_at=start_time,
            ),
        )
        trace_ids.append(trace_id)
    db_session.commit()
    return trace_ids


def _add_run(
    continuous_eval_id: uuid.UUID,
    trace_id: str,
    run_status: ContinuousEvalRunStatus,
    cost: Optional[float],
    created_at: datetime,
    test_run_id: Optional[uuid.UUID] = None,
) -> None:
    db_session = override_get_db_session()
    db_session.add(
        DatabaseAgenticAnnotation(
            id=uuid.uuid4(),
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL.value,
            trace_id=trace_id,
            continuous_eval_id=continuous_eval_id,
            run_status=run_status.value,
            cost=cost,
            test_run_id=test_run_id,
            created_at=created_at,
            updated_at=created_at,
            org_id=DEFAULT_ORG_ID,
        ),
    )
    db_session.commit()


def _cleanup(client: GenaiEngineTestClientBase, task_id: str, eval_ids: list) -> None:
    db_session = override_get_db_session()
    db_session.query(DatabaseAgenticAnnotation).filter(
        DatabaseAgenticAnnotation.continuous_eval_id.in_(eval_ids),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.task_id == task_id,
    ).delete(synchronize_session=False)
    db_session.commit()
    for eval_id in eval_ids:
        client.delete_continuous_eval(eval_id)
    client.delete_task(task_id)


@pytest.mark.unit_tests
def test_continuous_eval_spend_last_24h_and_estimate(
    client: GenaiEngineTestClientBase,
):
    status_code, task = client.create_task(name="spend_formula", is_agentic=True)
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "spend_eval")
    assert status_code == 200
    continuous_eval, _ = _create_continuous_eval(client, task.id, llm_eval.name, 0.5)

    try:
        now = datetime.now()
        # 14 traces in the last 7 days -> 2 traces/day. A trace older than the
        # window and an agent experiment trace (never evaluated) don't count.
        trace_ids = _add_traces(
            task.id,
            [now - timedelta(hours=11 * i + 1) for i in range(14)],
        )
        _add_traces(task.id, [now - timedelta(days=8)])
        _add_traces(
            task.id,
            [now - timedelta(hours=1)],
            session_id=f"{AGENT_EXPERIMENT_SESSION_PREFIX}-{uuid.uuid4()}",
        )

        recent = now - timedelta(hours=2)
        _add_run(
            continuous_eval.id,
            trace_ids[0],
            ContinuousEvalRunStatus.PASSED,
            0.02,
            recent,
        )
        _add_run(
            continuous_eval.id,
            trace_ids[1],
            ContinuousEvalRunStatus.FAILED,
            0.04,
            recent,
        )
        # Counted in the last 24h but not in the average: they never reached the LLM
        # or have no cost yet.
        _add_run(
            continuous_eval.id,
            trace_ids[2],
            ContinuousEvalRunStatus.ERROR,
            None,
            recent,
        )
        _add_run(
            continuous_eval.id,
            trace_ids[3],
            ContinuousEvalRunStatus.SKIPPED,
            None,
            recent,
        )
        _add_run(
            continuous_eval.id,
            trace_ids[4],
            ContinuousEvalRunStatus.PENDING,
            None,
            recent,
        )
        # In the 7-day average, not the last 24h.
        _add_run(
            continuous_eval.id,
            trace_ids[5],
            ContinuousEvalRunStatus.PASSED,
            0.06,
            now - timedelta(days=3),
        )
        # Outside the window entirely.
        _add_run(
            continuous_eval.id,
            trace_ids[6],
            ContinuousEvalRunStatus.PASSED,
            1.0,
            now - timedelta(days=8),
        )
        # Test runs are not live runs.
        _add_run(
            continuous_eval.id,
            trace_ids[7],
            ContinuousEvalRunStatus.PASSED,
            5.0,
            recent,
            test_run_id=uuid.uuid4(),
        )

        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert status_code == 200
        assert spend.continuous_eval_id == continuous_eval.id
        assert spend.last_24h_run_count == 5
        assert spend.last_24h_cost == pytest.approx(0.06)

        estimate = spend.estimate
        assert estimate.window_days == 7
        assert estimate.trace_count == 14
        assert estimate.traces_per_day == pytest.approx(2.0)
        assert estimate.sample_rate == 0.5
        assert estimate.run_count == 3
        assert estimate.average_run_cost == pytest.approx(0.04)
        # 2 traces/day * 0.5 * $0.04
        assert estimate.estimated_daily_cost == pytest.approx(0.04)
        assert estimate.unavailable_reason is None

        # The create form estimate prices from the same evaluator's live runs.
        status_code, form_estimate = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
            sample_rate=0.25,
        )
        assert status_code == 200
        assert form_estimate.sample_rate == 0.25
        assert form_estimate.run_count == 3
        assert form_estimate.estimated_daily_cost == pytest.approx(0.02)

        # No sample rate means every trace.
        status_code, form_estimate = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
        )
        assert status_code == 200
        assert form_estimate.sample_rate == 1.0
        assert form_estimate.estimated_daily_cost == pytest.approx(0.08)
    finally:
        _cleanup(client, task.id, [continuous_eval.id])


@pytest.mark.unit_tests
def test_continuous_eval_spend_without_traces_or_runs(
    client: GenaiEngineTestClientBase,
):
    status_code, task = client.create_task(name="spend_empty", is_agentic=True)
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "spend_eval")
    assert status_code == 200
    # Unset sample rate: every trace is evaluated.
    continuous_eval, _ = _create_continuous_eval(client, task.id, llm_eval.name, None)

    try:
        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert status_code == 200
        assert spend.last_24h_run_count == 0
        assert spend.last_24h_cost == 0.0
        assert spend.estimate.trace_count == 0
        assert spend.estimate.sample_rate == 1.0
        assert spend.estimate.run_count == 0
        assert spend.estimate.average_run_cost is None
        assert spend.estimate.estimated_daily_cost is None
        assert (
            spend.estimate.unavailable_reason
            == SpendEstimateUnavailableReason.NO_TRACES
        )

        # Traffic but no run that called the LLM yet.
        now = datetime.now()
        trace_ids = _add_traces(task.id, [now - timedelta(hours=1)] * 7)
        _add_run(
            continuous_eval.id,
            trace_ids[0],
            ContinuousEvalRunStatus.SKIPPED,
            None,
            now - timedelta(minutes=30),
        )

        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert status_code == 200
        assert spend.last_24h_run_count == 1
        assert spend.estimate.traces_per_day == pytest.approx(1.0)
        assert spend.estimate.estimated_daily_cost is None
        assert (
            spend.estimate.unavailable_reason == SpendEstimateUnavailableReason.NO_RUNS
        )

        # A passed run with no recorded cost prices at zero.
        _add_run(
            continuous_eval.id,
            trace_ids[1],
            ContinuousEvalRunStatus.PASSED,
            None,
            now - timedelta(minutes=20),
        )
        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert status_code == 200
        assert spend.estimate.run_count == 1
        assert spend.estimate.average_run_cost == 0.0
        assert spend.estimate.estimated_daily_cost == 0.0
        assert spend.estimate.unavailable_reason is None
    finally:
        _cleanup(client, task.id, [continuous_eval.id])


def _add_root_span(
    task_id: str,
    trace_id: str,
    attributes: dict,
    span_version: str = EXPECTED_SPAN_VERSION,
) -> None:
    db_session = override_get_db_session()
    now = datetime.now()
    db_session.add(
        DatabaseSpan(
            id=uuid.uuid4().hex,
            trace_id=trace_id,
            span_id=uuid.uuid4().hex,
            span_name="agent",
            start_time=now,
            end_time=now,
            task_id=task_id,
            org_id=DEFAULT_ORG_ID,
            raw_data={
                "name": "agent",
                "attributes": attributes,
                SPAN_VERSION_KEY: span_version,
            },
        ),
    )
    db_session.commit()


@pytest.mark.unit_tests
def test_spend_estimate_scales_by_the_filter_match_share(
    client: GenaiEngineTestClientBase,
):
    status_code, task = client.create_task(name="spend_filter", is_agentic=True)
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "filtered_eval")
    assert status_code == 200
    continuous_eval, _ = _create_continuous_eval(client, task.id, llm_eval.name, None)
    paid_only = json.dumps(
        [
            {
                "attribute_path": "attributes.metadata.plan",
                "operator": "equals",
                "value": "paid",
            },
        ],
    )

    try:
        now = datetime.now()
        # 8 traces in the window: 2 from paid users, 5 from free ones, and one
        # paid trace whose only span has a version the worker can't read.
        trace_ids = _add_traces(task.id, [now - timedelta(hours=3)] * 8)
        for i, trace_id in enumerate(trace_ids[:7]):
            _add_root_span(
                task.id,
                trace_id,
                {"metadata": {"plan": "paid" if i < 2 else "free"}},
            )
        _add_root_span(
            task.id,
            trace_ids[7],
            {"metadata": {"plan": "paid"}},
            span_version="arthur_span_v0",
        )
        _add_run(
            continuous_eval.id,
            trace_ids[0],
            ContinuousEvalRunStatus.PASSED,
            0.07,
            now - timedelta(hours=1),
        )

        status_code, unfiltered = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
        )
        assert status_code == 200
        assert unfiltered.filter_match_share is None
        # 8 traces / 7 days * $0.07
        assert unfiltered.estimated_daily_cost == pytest.approx(0.08)

        status_code, filtered = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
            trace_filter=paid_only,
        )
        assert status_code == 200
        # The unreadable trace isn't checked, so 2 of 7 match.
        assert filtered.filter_traces_checked == 7
        assert filtered.filter_match_share == pytest.approx(2 / 7)
        assert filtered.estimated_daily_cost == pytest.approx(0.08 * 2 / 7)

        status_code, not_paid = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
            trace_filter=paid_only.replace('"equals"', '"not_equals"'),
        )
        assert status_code == 200
        assert not_paid.filter_traces_checked == 7
        assert not_paid.filter_match_share == pytest.approx(5 / 7)

        status_code, _ = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
            trace_filter='[{"attribute_path": "attributes.metadata.plan"}]',
        )
        assert status_code == 400
    finally:
        db_session = override_get_db_session()
        db_session.query(DatabaseSpan).filter(
            DatabaseSpan.task_id == task.id,
        ).delete(synchronize_session=False)
        db_session.commit()
        _cleanup(client, task.id, [continuous_eval.id])


@pytest.mark.unit_tests
def test_spend_estimate_uses_only_the_named_evaluator(
    client: GenaiEngineTestClientBase,
):
    status_code, task = client.create_task(name="spend_estimate", is_agentic=True)
    assert status_code == 200
    status_code, cheap = create_test_llm_eval(client, task.id, "cheap_eval")
    assert status_code == 200
    status_code, pricey = create_test_llm_eval(client, task.id, "pricey_eval")
    assert status_code == 200
    status_code, unused = create_test_llm_eval(client, task.id, "unused_eval")
    assert status_code == 200
    cheap_eval, transform_id = _create_continuous_eval(
        client,
        task.id,
        cheap.name,
        None,
    )
    pricey_eval, _ = _create_continuous_eval(
        client,
        task.id,
        pricey.name,
        None,
        transform_id,
    )

    try:
        now = datetime.now()
        trace_ids = _add_traces(task.id, [now - timedelta(hours=3)] * 7)
        recent = now - timedelta(hours=1)
        _add_run(
            cheap_eval.id, trace_ids[0], ContinuousEvalRunStatus.PASSED, 0.01, recent
        )
        _add_run(
            cheap_eval.id, trace_ids[1], ContinuousEvalRunStatus.FAILED, 0.03, recent
        )
        _add_run(
            pricey_eval.id, trace_ids[0], ContinuousEvalRunStatus.PASSED, 1.0, recent
        )

        status_code, estimate = client.estimate_continuous_eval_spend(
            task.id,
            cheap.name,
            sample_rate=0.5,
        )
        assert status_code == 200
        assert estimate.run_count == 2
        assert estimate.average_run_cost == pytest.approx(0.02)
        # 1 trace/day * 0.5 * $0.02
        assert estimate.estimated_daily_cost == pytest.approx(0.01)

        # An evaluator no continuous eval has run yet can't be priced.
        status_code, estimate = client.estimate_continuous_eval_spend(
            task.id,
            unused.name,
        )
        assert status_code == 200
        assert estimate.trace_count == 7
        assert estimate.estimated_daily_cost is None
        assert estimate.unavailable_reason == SpendEstimateUnavailableReason.NO_RUNS

        status_code, _ = client.estimate_continuous_eval_spend(task.id, "missing")
        assert status_code == 404

        for bad_rate in (0.0, 1.5):
            status_code, _ = client.estimate_continuous_eval_spend(
                task.id,
                cheap.name,
                sample_rate=bad_rate,
            )
            assert status_code == 400
    finally:
        _cleanup(client, task.id, [cheap_eval.id, pricey_eval.id])


@pytest.mark.unit_tests
def test_continuous_eval_spend_not_found(client: GenaiEngineTestClientBase):
    status_code, _ = client.get_continuous_eval_spend(str(uuid.uuid4()))
    assert status_code == 404

    status_code, _ = client.estimate_continuous_eval_spend(
        str(uuid.uuid4()),
        "any_eval",
    )
    assert status_code == 404


@pytest.mark.unit_tests
def test_spend_windows_are_relative_to_now(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(name="spend_windows", is_agentic=True)
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "spend_eval")
    assert status_code == 200
    continuous_eval, _ = _create_continuous_eval(client, task.id, llm_eval.name, None)

    try:
        now = datetime(2026, 1, 8, 12, 0, 0)
        # Window start is inclusive; traces stamped at or after `now` are not yet in it.
        trace_ids = _add_traces(
            task.id,
            [now - timedelta(days=7), now - timedelta(seconds=1), now],
        )
        _add_run(
            continuous_eval.id,
            trace_ids[0],
            ContinuousEvalRunStatus.PASSED,
            0.7,
            now - timedelta(days=1),
        )
        _add_run(
            continuous_eval.id,
            trace_ids[1],
            ContinuousEvalRunStatus.PASSED,
            0.1,
            now - timedelta(days=7, seconds=1),
        )

        db_session = override_get_db_session()
        ce = ContinuousEvalsRepository(db_session).get_continuous_eval_by_id(
            continuous_eval.id,
        )
        spend = ContinuousEvalSpendRepository(db_session).get_continuous_eval_spend(
            ce,
            now=now,
        )
        assert spend.last_24h_run_count == 1
        assert spend.last_24h_cost == pytest.approx(0.7)
        assert spend.estimate.trace_count == 2
        assert spend.estimate.run_count == 1
        assert spend.estimate.average_run_cost == pytest.approx(0.7)
        assert spend.estimate.estimated_daily_cost == pytest.approx(2 / 7 * 0.7)
    finally:
        _cleanup(client, task.id, [continuous_eval.id])

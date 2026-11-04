import uuid
from datetime import datetime, timedelta
from typing import Optional

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.telemetry_models import DatabaseTraceMetadata
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
from utils.constants import AGENT_EXPERIMENT_SESSION_PREFIX, DEFAULT_ORG_ID


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
        # or have no cost yet. The skipped run also lowers the share of sampled
        # traces that reach the judge; the errored and pending ones don't count.
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
        # 3 of the 4 finished runs in the window reached the judge.
        assert estimate.judged_share == pytest.approx(0.75)
        # 2 traces/day * 0.5 sampled * 0.75 judged * $0.04
        assert estimate.estimated_daily_cost == pytest.approx(0.03)
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
        # 2 traces/day * 0.25 * 0.75 judged * $0.04
        assert form_estimate.estimated_daily_cost == pytest.approx(0.015)

        # No sample rate means every trace.
        status_code, form_estimate = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
        )
        assert status_code == 200
        assert form_estimate.sample_rate == 1.0
        assert form_estimate.estimated_daily_cost == pytest.approx(0.06)
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

        # A passed run with no recorded cost (a model without a price) is left out of
        # the average rather than pricing it at zero.
        _add_run(
            continuous_eval.id,
            trace_ids[1],
            ContinuousEvalRunStatus.PASSED,
            None,
            now - timedelta(minutes=20),
        )
        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert status_code == 200
        assert spend.estimate.run_count == 0
        assert spend.estimate.unpriced_run_count == 1
        assert spend.estimate.average_run_cost is None
        assert spend.estimate.estimated_daily_cost is None
        assert (
            spend.estimate.unavailable_reason == SpendEstimateUnavailableReason.NO_RUNS
        )
    finally:
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


@pytest.mark.unit_tests
def test_spend_estimate_prices_only_the_current_evaluator(
    client: GenaiEngineTestClientBase,
):
    """After a judge switch the average uses only runs from the new evaluator, so an
    eval moved from an expensive judge to a cheap one is priced at the cheap one."""
    status_code, task = client.create_task(
        name="test_spend_estimate_judge_switch",
        is_agentic=True,
    )
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "switch_eval")
    assert status_code == 200
    continuous_eval, _ = _create_continuous_eval(client, task.id, llm_eval.name, None)
    try:
        now = datetime.now()
        trace_ids = _add_traces(
            task.id, [now - timedelta(hours=h) for h in range(1, 8)]
        )
        # Three expensive runs from the original evaluator.
        for i in range(3):
            _add_run(
                continuous_eval.id,
                trace_ids[i],
                ContinuousEvalRunStatus.PASSED,
                0.10,
                now - timedelta(hours=5),
            )

        # Switch to a new version of the evaluator.
        status_code, _ = client.save_llm_eval(
            task_id=task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_data={
                "model_name": "gpt-4o-mini",
                "model_provider": "openai",
                "instructions": "Cheaper judge {{test_variable}}",
            },
        )
        assert status_code == 200
        status_code, updated = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": 2,
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200

        # Before any run from the new evaluator there is nothing to price it from.
        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert status_code == 200
        assert spend.estimate.priced_since is not None
        assert spend.estimate.run_count == 0
        assert (
            spend.estimate.unavailable_reason == SpendEstimateUnavailableReason.NO_RUNS
        )

        _add_run(
            continuous_eval.id,
            trace_ids[3],
            ContinuousEvalRunStatus.PASSED,
            0.01,
            datetime.now(),
        )
        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert status_code == 200
        assert spend.estimate.run_count == 1
        assert spend.estimate.average_run_cost == pytest.approx(0.01)
        # 7 traces/7 days * 1.0 * 1.0 * $0.01, not the $0.0775 a mixed average gives.
        assert spend.estimate.estimated_daily_cost == pytest.approx(0.01)

        # Editing anything other than the evaluator keeps the pricing window.
        status_code, _ = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={"description": "renamed only"},
        )
        assert status_code == 200
        status_code, spend = client.get_continuous_eval_spend(str(continuous_eval.id))
        assert spend.estimate.run_count == 1
    finally:
        _cleanup(client, task.id, [continuous_eval.id])


@pytest.mark.unit_tests
def test_spend_estimate_ignores_other_versions_and_ml_evals(
    client: GenaiEngineTestClientBase,
):
    """A new eval is priced from the evaluator's latest version only, and an ML
    eval's runs (no LLM call, no cost) never count as unpriced LLM calls."""
    status_code, task = client.create_task(
        name="test_spend_estimate_versions",
        is_agentic=True,
    )
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "versioned_eval")
    assert status_code == 200
    old_version_eval, transform_id = _create_continuous_eval(
        client, task.id, llm_eval.name, None
    )
    status_code, _ = client.save_llm_eval(
        task_id=task.id,
        llm_eval_name=llm_eval.name,
        llm_eval_data={
            "model_name": "gpt-4o-mini",
            "model_provider": "openai",
            "instructions": "Cheaper judge {{test_variable}}",
        },
    )
    assert status_code == 200
    latest_eval, _ = _create_continuous_eval(
        client, task.id, llm_eval.name, None, transform_id
    )
    try:
        now = datetime.now()
        trace_ids = _add_traces(task.id, [now - timedelta(hours=3)] * 7)
        recent = now - timedelta(hours=1)
        # The eval still on version 1 is ten times pricier.
        _add_run(
            old_version_eval.id,
            trace_ids[0],
            ContinuousEvalRunStatus.PASSED,
            0.10,
            recent,
        )
        _add_run(
            latest_eval.id, trace_ids[1], ContinuousEvalRunStatus.PASSED, 0.01, recent
        )

        status_code, estimate = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
        )
        assert status_code == 200
        assert estimate.run_count == 1
        assert estimate.average_run_cost == pytest.approx(0.01)

        # Picking version 1 in the form prices from the version 1 eval instead.
        status_code, estimate = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
            llm_eval_version="1",
        )
        assert status_code == 200
        assert estimate.run_count == 1
        assert estimate.average_run_cost == pytest.approx(0.10)

        # A version the evaluator doesn't have is a 404.
        status_code, _ = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
            llm_eval_version="9",
        )
        assert status_code == 404

        # Turn the version 1 eval into an ML eval: its finished runs have no cost.
        db_session = override_get_db_session()
        db_session.query(DatabaseContinuousEval).filter(
            DatabaseContinuousEval.id == old_version_eval.id,
        ).update({"eval_type": "ml_eval"})
        db_session.commit()
        _add_run(
            old_version_eval.id,
            trace_ids[2],
            ContinuousEvalRunStatus.PASSED,
            None,
            recent,
        )
        status_code, spend = client.get_continuous_eval_spend(str(old_version_eval.id))
        assert status_code == 200
        assert spend.estimate.unpriced_run_count == 0
        assert spend.estimate.run_count == 0
        assert (
            spend.estimate.unavailable_reason == SpendEstimateUnavailableReason.NO_RUNS
        )
    finally:
        _cleanup(client, task.id, [old_version_eval.id, latest_eval.id])


@pytest.mark.unit_tests
def test_spend_estimate_ignores_errored_runs_in_judged_share(
    client: GenaiEngineTestClientBase,
):
    """Runs that error (out of credits, a provider outage) don't lower the share of
    traces that reach the judge, so a bad day doesn't make the estimate look cheap."""
    status_code, task = client.create_task(
        name="test_spend_estimate_errors",
        is_agentic=True,
    )
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "erroring_eval")
    assert status_code == 200
    continuous_eval, _ = _create_continuous_eval(client, task.id, llm_eval.name, None)
    try:
        now = datetime.now()
        # 70 traces in 7 days -> 10 traces/day.
        trace_ids = _add_traces(task.id, [now - timedelta(hours=2)] * 70)
        recent = now - timedelta(hours=1)
        for trace_id in trace_ids[:8]:
            _add_run(
                continuous_eval.id,
                trace_id,
                ContinuousEvalRunStatus.ERROR,
                None,
                recent,
            )
        for trace_id in trace_ids[8:10]:
            _add_run(
                continuous_eval.id,
                trace_id,
                ContinuousEvalRunStatus.PASSED,
                0.01,
                recent,
            )

        status_code, estimate = client.estimate_continuous_eval_spend(
            task.id,
            llm_eval.name,
        )
        assert status_code == 200
        assert estimate.judged_share == pytest.approx(1.0)
        # 10 traces/day * 1.0 sampled * 1.0 judged * $0.01
        assert estimate.estimated_daily_cost == pytest.approx(0.1)
    finally:
        _cleanup(client, task.id, [continuous_eval.id])

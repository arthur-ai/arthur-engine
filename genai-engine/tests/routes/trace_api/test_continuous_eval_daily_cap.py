import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from litellm.types.utils import ModelResponse

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.continuous_eval_test_run_models import DatabaseContinuousEvalTestRun
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
    cleanup_test_data,
    create_mock_annotation,
    delete_mock_annotation,
    mock_get_db_session_generator,
    setup_test_data,
)

CAP = 0.01


def _create_capped_eval(client: GenaiEngineTestClientBase, cap=CAP):
    status_code, task = client.create_task(name="test_daily_cap", is_agentic=True)
    assert status_code == 200
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201
    status_code, _ = client.save_llm_eval(
        task_id=task.id,
        llm_eval_name="capped_llm_eval",
        llm_eval_data={
            "model_name": "gpt-4o",
            "model_provider": "openai",
            "instructions": "Test instructions {{model_name}}",
        },
    )
    assert status_code == 200
    status_code, transform = client.create_transform(
        task_id=task.id,
        name="capped_transform",
        description="",
        definition={
            "variables": [
                {
                    "variable_name": "model_name",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "attributes.input.value.context",
                },
            ],
        },
    )
    assert status_code == 200
    status_code, continuous_eval = client.save_continuous_eval(
        task_id=task.id,
        continuous_eval_data={
            "name": "capped_continuous_eval",
            "llm_eval_name": "capped_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {"transform_variable": "model_name", "eval_variable": "model_name"},
            ],
            "daily_cost_cap_usd": cap,
        },
    )
    assert status_code == 200
    return task, continuous_eval


def _add_spent_run(trace_id, continuous_eval_id, cost, created_at=None, judged_at=None):
    run = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval_id,
        run_status=ContinuousEvalRunStatus.PASSED,
        created_at=created_at,
        updated_at=judged_at or created_at,
    )
    db_session = override_get_db_session()
    db_run = db_session.get(DatabaseAgenticAnnotation, run.id)
    db_run.cost = cost
    db_session.commit()
    return run


def _run_one_job(trace_id, continuous_eval_id, task_id):
    pending = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval_id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )
    get_continuous_eval_queue_service()._execute_job(
        ContinuousEvalJob(
            annotation_id=pending.id,
            trace_id=trace_id,
            continuous_eval_id=continuous_eval_id,
            task_id=task_id,
            delay_seconds=0,
        ),
    )
    return override_get_db_session().get(DatabaseAgenticAnnotation, pending.id)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "spent_today, spent_yesterday, expect_skip",
    [
        (0.0, 0.0, False),  # nothing spent: runs
        (0.009, 0.0, False),  # just under the cap: runs
        (0.01, 0.0, True),  # at the cap: skipped
        (0.0, 0.05, False),  # spend judged yesterday doesn't count
        (0.0, "queued_yesterday_judged_today", True),  # counts on the day it's judged
    ],
)
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_worker_skips_judge_call_once_daily_cap_is_reached(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
    spent_today,
    spent_yesterday,
    expect_skip,
):
    test_data = setup_test_data()
    response = MagicMock(spec=ModelResponse)
    response.choices = [MagicMock()]
    response.choices[0].message = {"content": '{"reason": "ok", "score": 1}'}
    mock_completion.return_value = response
    mock_completion_cost.return_value = 0.002
    initialize_continuous_eval_queue_service(num_workers=1, override_execution_delay=0)
    task, continuous_eval = _create_capped_eval(client)
    created = []
    try:
        if spent_today:
            created.append(
                _add_spent_run(test_data["trace_id"], continuous_eval.id, spent_today)
            )
        if spent_yesterday == "queued_yesterday_judged_today":
            created.append(
                _add_spent_run(
                    test_data["trace_id"],
                    continuous_eval.id,
                    0.02,
                    created_at=datetime.now() - timedelta(days=1, hours=1),
                    judged_at=datetime.now(),
                ),
            )
        elif spent_yesterday:
            created.append(
                _add_spent_run(
                    test_data["trace_id"],
                    continuous_eval.id,
                    spent_yesterday,
                    created_at=datetime.now() - timedelta(days=1, hours=1),
                ),
            )

        run = _run_one_job(test_data["trace_id"], continuous_eval.id, task.id)
        created.append(run)

        if expect_skip:
            assert run.run_status == ContinuousEvalRunStatus.SKIPPED.value
            assert "Daily spend cap of $0.01 reached" in run.annotation_description
            mock_completion.assert_not_called()
        else:
            assert run.run_status == ContinuousEvalRunStatus.PASSED.value
            mock_completion.assert_called_once()
    finally:
        for r in created:
            delete_mock_annotation(r.id)
        client.delete_task(task.id)
        shutdown_continuous_eval_queue_service()
        cleanup_model_provider(client)
        cleanup_test_data(test_data)


@pytest.mark.unit_tests
def test_daily_cap_round_trips_and_shows_in_spend(client: GenaiEngineTestClientBase):
    test_data = setup_test_data()
    task, continuous_eval = _create_capped_eval(client, cap=2.5)
    created = []
    try:
        assert continuous_eval.daily_cost_cap_usd == 2.5

        status_code, updated = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={"description": "cap untouched"},
        )
        assert status_code == 200
        assert updated.daily_cost_cap_usd == 2.5

        created.append(_add_spent_run(test_data["trace_id"], continuous_eval.id, 3.0))
        response = client.base_client.get(
            f"/api/v1/continuous_evals/{continuous_eval.id}/spend",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200
        spend = response.json()
        assert spend["spent_today"] == pytest.approx(3.0)
        assert spend["daily_cost_cap_usd"] == 2.5
        assert spend["cap_reached"] is True

        status_code, updated = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={"daily_cost_cap_usd": None},
        )
        assert status_code == 200
        assert updated.daily_cost_cap_usd is None
        response = client.base_client.get(
            f"/api/v1/continuous_evals/{continuous_eval.id}/spend",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.json()["cap_reached"] is False

        # NaN would never compare >= spend, so the cap would silently never trip.
        for bad_cap in (0, "NaN", "Infinity"):
            status_code, _ = client.update_continuous_eval(
                continuous_eval_id=continuous_eval.id,
                continuous_eval_data={"daily_cost_cap_usd": bad_cap},
            )
            assert status_code == 400, bad_cap
    finally:
        for r in created:
            delete_mock_annotation(r.id)
        client.delete_task(task.id)
        cleanup_model_provider(client)
        cleanup_test_data(test_data)


def _run_job_for(annotation_id, trace_id, continuous_eval_id, task_id):
    get_continuous_eval_queue_service()._execute_job(
        ContinuousEvalJob(
            annotation_id=annotation_id,
            trace_id=trace_id,
            continuous_eval_id=continuous_eval_id,
            task_id=task_id,
            delay_seconds=0,
        ),
    )
    return override_get_db_session().get(DatabaseAgenticAnnotation, annotation_id)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_cap_holds_back_neither_test_runs_nor_claimed_runs(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    test_data = setup_test_data()
    response = MagicMock(spec=ModelResponse)
    response.choices = [MagicMock()]
    response.choices[0].message = {"content": '{"reason": "ok", "score": 1}'}
    mock_completion.return_value = response
    mock_completion_cost.return_value = 0.002
    initialize_continuous_eval_queue_service(num_workers=1, override_execution_delay=0)
    task, continuous_eval = _create_capped_eval(client)
    created = []
    db_session = override_get_db_session()
    test_run = DatabaseContinuousEvalTestRun(
        id=uuid.uuid4(),
        continuous_eval_id=continuous_eval.id,
        task_id=task.id,
        status="running",
        total_count=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(test_run)
    db_session.commit()
    try:
        created.append(_add_spent_run(test_data["trace_id"], continuous_eval.id, 0.05))

        # A test run of a capped eval still calls the judge.
        test_annotation = create_mock_annotation(
            trace_id=test_data["trace_id"],
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            continuous_eval_id=continuous_eval.id,
            run_status=ContinuousEvalRunStatus.PENDING,
        )
        db_annotation = db_session.get(DatabaseAgenticAnnotation, test_annotation.id)
        db_annotation.test_run_id = test_run.id
        db_session.commit()
        created.append(test_annotation)
        run = _run_job_for(
            test_annotation.id,
            test_data["trace_id"],
            continuous_eval.id,
            task.id,
        )
        assert run.run_status == ContinuousEvalRunStatus.PASSED.value
        mock_completion.assert_called_once()

        # Race: another worker claims this pending run after this worker loaded it
        # but before the cap check skips it. The skip must not overwrite the claim.
        raced = create_mock_annotation(
            trace_id=test_data["trace_id"],
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            continuous_eval_id=continuous_eval.id,
            run_status=ContinuousEvalRunStatus.PENDING,
        )
        created.append(raced)

        def claimed_meanwhile(*args, **kwargs):
            other = override_get_db_session()
            other.get(DatabaseAgenticAnnotation, raced.id).run_status = (
                ContinuousEvalRunStatus.RUNNING.value
            )
            other.commit()
            return 1.0

        with patch(
            "services.continuous_eval.continuous_eval_queue_service."
            "ContinuousEvalSpendRepository.spent_today",
            side_effect=claimed_meanwhile,
        ):
            run = _run_job_for(
                raced.id, test_data["trace_id"], continuous_eval.id, task.id
            )
        override_get_db_session().expire_all()
        run = override_get_db_session().get(DatabaseAgenticAnnotation, raced.id)
        assert run.run_status == ContinuousEvalRunStatus.RUNNING.value
    finally:
        for r in created:
            delete_mock_annotation(r.id)
        db_session.query(DatabaseContinuousEvalTestRun).filter(
            DatabaseContinuousEvalTestRun.id == test_run.id,
        ).delete()
        db_session.commit()
        client.delete_task(task.id)
        shutdown_continuous_eval_queue_service()
        cleanup_model_provider(client)
        cleanup_test_data(test_data)

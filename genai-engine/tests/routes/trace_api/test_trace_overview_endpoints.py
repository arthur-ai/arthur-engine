import uuid
from datetime import datetime, timedelta
from typing import Optional

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.telemetry_models import DatabaseTraceMetadata
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from utils.constants import DEFAULT_ORG_ID


def create_mock_annotation(
    trace_id: str,
    annotation_type: AgenticAnnotationType,
    annotation_score: Optional[int] = None,
    continuous_eval_id: Optional[uuid.UUID] = None,
    run_status: Optional[ContinuousEvalRunStatus] = None,
) -> DatabaseAgenticAnnotation:
    db_session = override_get_db_session()
    db_annotation = DatabaseAgenticAnnotation(
        id=uuid.uuid4(),
        annotation_type=annotation_type.value,
        trace_id=trace_id,
        annotation_score=annotation_score,
        continuous_eval_id=continuous_eval_id,
        run_status=run_status.value if run_status else None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        org_id=DEFAULT_ORG_ID,
    )
    db_session.add(db_annotation)
    db_session.commit()
    db_session.refresh(db_annotation)
    return db_annotation


def delete_mock_annotation(annotation_id: uuid.UUID) -> None:
    db_session = override_get_db_session()
    db_annotation = (
        db_session.query(DatabaseAgenticAnnotation)
        .filter(DatabaseAgenticAnnotation.id == annotation_id)
        .first()
    )
    if not db_annotation:
        return
    db_session.delete(db_annotation)
    db_session.commit()


def create_mock_trace(
    trace_id: str,
    task_id: str,
    start_time: datetime,
    end_time: datetime,
    total_token_count: Optional[int] = None,
    total_token_cost: Optional[float] = None,
) -> None:
    db_session = override_get_db_session()
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=trace_id,
            task_id=task_id,
            org_id=DEFAULT_ORG_ID,
            start_time=start_time,
            end_time=end_time,
            created_at=start_time,
            updated_at=end_time,
            span_count=1,
            total_token_count=total_token_count,
            total_token_cost=total_token_cost,
        ),
    )
    db_session.commit()


def delete_mock_trace(trace_id: str) -> None:
    db_session = override_get_db_session()
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id == trace_id,
    ).delete()
    db_session.commit()


@pytest.mark.unit_tests
def test_traces_overview_aggregates_per_task(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(
        name="test_traces_overview_aggregates_per_task",
        is_agentic=True,
    )
    assert status_code == 200

    now = datetime.now()
    trace_id_1 = str(uuid.uuid4())
    trace_id_2 = str(uuid.uuid4())
    passed_annotation = None
    failed_annotation = None

    try:
        create_mock_trace(
            trace_id_1,
            task.id,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1) + timedelta(seconds=5),
            total_token_count=100,
            total_token_cost=0.5,
        )
        create_mock_trace(
            trace_id_2,
            task.id,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2) + timedelta(seconds=5),
            total_token_count=50,
            total_token_cost=0.25,
        )
        passed_annotation = create_mock_annotation(
            trace_id=trace_id_1,
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            continuous_eval_id=uuid.uuid4(),
            run_status=ContinuousEvalRunStatus.PASSED,
        )
        failed_annotation = create_mock_annotation(
            trace_id=trace_id_2,
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            continuous_eval_id=uuid.uuid4(),
            run_status=ContinuousEvalRunStatus.FAILED,
        )

        status_code, data = client.trace_api_get_traces_overview(
            start_time=now - timedelta(days=7),
            end_time=now,
            task_ids=[task.id],
        )
        assert status_code == 200

        overview = next((o for o in data.overviews if o.task_id == task.id), None)
        assert overview is not None
        assert overview.trace_count == 2
        assert overview.trace_token_count == 150
        assert overview.trace_token_cost == 0.75
        assert overview.eval_count == 2
        # 1 of 2 continuous evals passed.
        assert overview.continuous_eval_success_rate == 0.5
        assert overview.last_active is not None
    finally:
        if passed_annotation:
            delete_mock_annotation(passed_annotation.id)
        if failed_annotation:
            delete_mock_annotation(failed_annotation.id)
        delete_mock_trace(trace_id_1)
        delete_mock_trace(trace_id_2)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_traces_overview_success_rate_defaults_to_one_without_evals(
    client: GenaiEngineTestClientBase,
):
    status_code, task = client.create_task(
        name="test_traces_overview_no_evals",
        is_agentic=True,
    )
    assert status_code == 200

    now = datetime.now()
    trace_id = str(uuid.uuid4())

    try:
        create_mock_trace(
            trace_id,
            task.id,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1) + timedelta(seconds=5),
            total_token_count=10,
            total_token_cost=0.1,
        )

        status_code, data = client.trace_api_get_traces_overview(
            start_time=now - timedelta(days=7),
            end_time=now,
            task_ids=[task.id],
        )
        assert status_code == 200

        overview = next((o for o in data.overviews if o.task_id == task.id), None)
        assert overview is not None
        assert overview.trace_count == 1
        assert overview.eval_count == 0
        assert overview.continuous_eval_success_rate == 1.0
    finally:
        delete_mock_trace(trace_id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_traces_timeseries_buckets_by_day(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(
        name="test_traces_timeseries_buckets_by_day",
        is_agentic=True,
    )
    assert status_code == 200

    now = datetime.now()
    window_start = now - timedelta(days=7)
    trace_id_a = str(uuid.uuid4())
    trace_id_b = str(uuid.uuid4())
    trace_id_c = str(uuid.uuid4())

    try:
        # One trace on day 1, two traces on day 3 (same bucket).
        create_mock_trace(
            trace_id_a,
            task.id,
            start_time=window_start + timedelta(days=1),
            end_time=window_start + timedelta(days=1, seconds=5),
            total_token_count=100,
            total_token_cost=0.5,
        )
        create_mock_trace(
            trace_id_b,
            task.id,
            start_time=window_start + timedelta(days=3),
            end_time=window_start + timedelta(days=3, seconds=5),
            total_token_count=20,
            total_token_cost=0.1,
        )
        create_mock_trace(
            trace_id_c,
            task.id,
            start_time=window_start + timedelta(days=3, hours=2),
            end_time=window_start + timedelta(days=3, hours=2, seconds=5),
            total_token_count=30,
            total_token_cost=0.2,
        )

        status_code, data = client.trace_api_get_traces_timeseries(
            task_id=task.id,
            start_time=window_start,
            end_time=now,
            bucket_size="day",
        )
        assert status_code == 200
        assert data.task_id == task.id
        # 7-day window bucketed by day.
        assert len(data.points) == 7

        assert sum(p.trace_count for p in data.points) == 3
        assert sum(p.trace_token_count for p in data.points) == 150

        # Both day-3 traces land in the same bucket.
        busiest_bucket = max(data.points, key=lambda p: p.trace_count)
        assert busiest_bucket.trace_count == 2
        assert busiest_bucket.trace_token_count == 50
    finally:
        delete_mock_trace(trace_id_a)
        delete_mock_trace(trace_id_b)
        delete_mock_trace(trace_id_c)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_traces_timeseries_unknown_task_returns_404(
    client: GenaiEngineTestClientBase,
):
    now = datetime.now()
    status_code, _ = client.trace_api_get_traces_timeseries(
        task_id=str(uuid.uuid4()),
        start_time=now - timedelta(days=7),
        end_time=now,
        bucket_size="day",
    )
    assert status_code == 404

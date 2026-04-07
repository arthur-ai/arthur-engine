"""Unit tests for trace retention repository."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db_models import (
    DatabaseAgenticAnnotation,
    DatabaseMetric,
    DatabaseMetricResult,
    DatabaseResourceMetadata,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTraceMetadata,
)
from repositories.trace_retention_repository import (
    DEFAULT_TRACE_RETENTION_BATCH_SIZE,
    delete_trace_batch,
    get_expired_trace_ids,
)
from tests.clients.base_test_client import override_get_db_session


def _cleanup_trace_data(
    db_session: Session,
    *,
    task_ids: list[str] | None = None,
    trace_ids: list[str] | None = None,
    span_ids: list[str] | None = None,
    resource_ids: list[str] | None = None,
    metric_ids: list[str] | None = None,
    annotation_ids: list[uuid.UUID] | None = None,
) -> None:
    """Delete test data in FK-safe order and close the session."""
    if annotation_ids:
        db_session.execute(
            delete(DatabaseAgenticAnnotation).where(
                DatabaseAgenticAnnotation.id.in_(annotation_ids)
            )
        )
    if metric_ids or span_ids:
        if span_ids:
            db_session.execute(
                delete(DatabaseMetricResult).where(
                    DatabaseMetricResult.span_id.in_(span_ids)
                )
            )
        if metric_ids:
            db_session.execute(
                delete(DatabaseMetric).where(DatabaseMetric.id.in_(metric_ids))
            )
    if span_ids:
        db_session.execute(
            delete(DatabaseSpan).where(DatabaseSpan.id.in_(span_ids))
        )
    if trace_ids:
        db_session.execute(
            delete(DatabaseTraceMetadata).where(
                DatabaseTraceMetadata.trace_id.in_(trace_ids)
            )
        )
    if resource_ids:
        db_session.execute(
            delete(DatabaseResourceMetadata).where(
                DatabaseResourceMetadata.id.in_(resource_ids)
            )
        )
    if task_ids:
        db_session.execute(
            delete(DatabaseTask).where(DatabaseTask.id.in_(task_ids))
        )
    db_session.commit()
    db_session.close()


def _make_task(session: Session) -> str:
    """Create a task and return its id."""
    task_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    task = DatabaseTask(
        id=task_id,
        name=f"trace_retention_test_{task_id[:8]}",
        created_at=now,
        updated_at=now,
        is_agentic=False,
        archived=False,
    )
    session.add(task)
    session.commit()
    return task_id


@pytest.mark.unit_tests
def test_get_expired_trace_ids_returns_only_expired_and_respects_batch_size() -> None:
    """get_expired_trace_ids returns only trace_ids with end_time < cutoff, capped by batch_size."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)

    # Insert trace_metadata: two expired, one not expired
    expired_1 = str(uuid.uuid4())
    expired_2 = str(uuid.uuid4())
    not_expired = str(uuid.uuid4())
    for trace_id, end_time in [
        (expired_1, now - timedelta(days=2)),
        (expired_2, now - timedelta(days=3)),
        (not_expired, now + timedelta(days=1)),
    ]:
        db_session.add(
            DatabaseTraceMetadata(
                trace_id=trace_id,
                task_id=task_id,
                start_time=end_time - timedelta(seconds=10),
                end_time=end_time,
                span_count=0,
            )
        )
    db_session.commit()

    try:
        result = get_expired_trace_ids(db_session, cutoff, batch_size=10)
        assert set(result) == {expired_1, expired_2}
        assert not_expired not in result

        # Respect batch_size; ORDER BY end_time ASC means oldest first
        result_cap = get_expired_trace_ids(db_session, cutoff, batch_size=1)
        assert len(result_cap) == 1
        assert result_cap[0] == expired_2
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[expired_1, expired_2, not_expired],
        )


@pytest.mark.unit_tests
def test_delete_trace_batch_removes_trace_and_orphan_resource_metadata_only() -> None:
    """delete_trace_batch deletes trace, spans, and only resource_metadata orphaned by this batch."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    trace_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Resource used only by this batch (should be deleted)
    resource_id_batch = str(uuid.uuid4())
    db_session.add(
        DatabaseResourceMetadata(
            id=resource_id_batch,
            service_name="batch-service",
            resource_attributes={},
        )
    )
    # Resource used by another trace (should remain)
    resource_id_other = str(uuid.uuid4())
    db_session.add(
        DatabaseResourceMetadata(
            id=resource_id_other,
            service_name="other-service",
            resource_attributes={},
        )
    )
    db_session.commit()

    # Trace and span for this batch (reference resource_id_batch)
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=trace_id,
            task_id=task_id,
            root_span_resource_id=resource_id_batch,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            span_count=1,
        )
    )
    span_id = str(uuid.uuid4())
    db_session.add(
        DatabaseSpan(
            id=span_id,
            trace_id=trace_id,
            span_id=span_id,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            task_id=task_id,
            resource_id=resource_id_batch,
            raw_data={},
            status_code="Unset",
        )
    )
    # Another trace that references resource_id_other (so it stays)
    other_trace_id = str(uuid.uuid4())
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=other_trace_id,
            task_id=task_id,
            root_span_resource_id=resource_id_other,
            start_time=now,
            end_time=now,
            span_count=0,
        )
    )
    db_session.commit()

    try:
        delete_trace_batch(db_session, [trace_id])
        db_session.commit()

        # Batch trace and span gone
        assert (
            db_session.execute(
                select(DatabaseTraceMetadata).where(
                    DatabaseTraceMetadata.trace_id == trace_id
                )
            ).scalar_one_or_none()
            is None
        )
        assert (
            db_session.execute(
                select(DatabaseSpan).where(DatabaseSpan.id == span_id)
            ).scalar_one_or_none()
            is None
        )
        # Orphan resource (only referenced by deleted batch) is deleted
        assert (
            db_session.execute(
                select(DatabaseResourceMetadata).where(
                    DatabaseResourceMetadata.id == resource_id_batch
                )
            ).scalar_one_or_none()
            is None
        )
        # Resource still referenced by other trace remains
        assert (
            db_session.execute(
                select(DatabaseResourceMetadata).where(
                    DatabaseResourceMetadata.id == resource_id_other
                )
            ).scalar_one_or_none()
            is not None
        )
        assert (
            db_session.execute(
                select(DatabaseTraceMetadata).where(
                    DatabaseTraceMetadata.trace_id == other_trace_id
                )
            ).scalar_one_or_none()
            is not None
        )
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[trace_id, other_trace_id],
            span_ids=[span_id],
            resource_ids=[resource_id_batch, resource_id_other],
        )


@pytest.mark.unit_tests
def test_get_expired_trace_ids_returns_nothing_when_no_traces_expired() -> None:
    """get_expired_trace_ids returns empty when cutoff is older than all traces."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)
    trace_id = str(uuid.uuid4())
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=trace_id,
            task_id=task_id,
            start_time=now,
            end_time=now,
            span_count=0,
        )
    )
    db_session.commit()
    cutoff = now - timedelta(days=1)

    try:
        result = get_expired_trace_ids(
            db_session, cutoff, batch_size=DEFAULT_TRACE_RETENTION_BATCH_SIZE
        )
        assert result == []
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[trace_id],
        )


@pytest.mark.unit_tests
def test_delete_trace_batch_removes_metric_results_for_deleted_spans() -> None:
    """delete_trace_batch deletes metric_results that reference spans in the batch."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)
    trace_id = str(uuid.uuid4())

    metric_id = str(uuid.uuid4())
    db_session.add(
        DatabaseMetric(
            id=metric_id,
            type="hallucination",
            name="test_metric",
            metric_metadata="{}",
        )
    )
    db_session.commit()

    db_session.add(
        DatabaseTraceMetadata(
            trace_id=trace_id,
            task_id=task_id,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            span_count=1,
        )
    )
    span_id = str(uuid.uuid4())
    db_session.add(
        DatabaseSpan(
            id=span_id,
            trace_id=trace_id,
            span_id=span_id,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            task_id=task_id,
            raw_data={},
            status_code="Unset",
        )
    )
    db_session.commit()

    mr_id_1 = str(uuid.uuid4())
    mr_id_2 = str(uuid.uuid4())
    for mr_id in (mr_id_1, mr_id_2):
        db_session.add(
            DatabaseMetricResult(
                id=mr_id,
                metric_type="hallucination",
                prompt_tokens=0,
                completion_tokens=0,
                latency_ms=0,
                span_id=span_id,
                metric_id=metric_id,
            )
        )
    db_session.commit()

    try:
        delete_trace_batch(db_session, [trace_id])
        db_session.commit()

        assert (
            db_session.execute(
                select(DatabaseSpan).where(DatabaseSpan.id == span_id)
            ).scalar_one_or_none()
            is None
        )
        assert (
            db_session.execute(
                select(DatabaseMetricResult).where(
                    DatabaseMetricResult.span_id == span_id
                )
            ).all()
            == []
        )
        assert (
            db_session.execute(
                select(DatabaseTraceMetadata).where(
                    DatabaseTraceMetadata.trace_id == trace_id
                )
            ).scalar_one_or_none()
            is None
        )
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[trace_id],
            span_ids=[span_id],
            metric_ids=[metric_id],
        )


@pytest.mark.unit_tests
def test_delete_trace_batch_noop_on_empty_list() -> None:
    """delete_trace_batch returns immediately when given an empty list, leaving existing data intact."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)
    trace_id = str(uuid.uuid4())
    db_session.add(
        DatabaseTraceMetadata(
            trace_id=trace_id,
            task_id=task_id,
            start_time=now,
            end_time=now,
            span_count=0,
        )
    )
    db_session.commit()

    try:
        delete_trace_batch(db_session, [])
        db_session.commit()

        assert (
            db_session.execute(
                select(DatabaseTraceMetadata).where(
                    DatabaseTraceMetadata.trace_id == trace_id
                )
            ).scalar_one_or_none()
            is not None
        )
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[trace_id],
        )


@pytest.mark.unit_tests
def test_delete_trace_batch_removes_agentic_annotations() -> None:
    """delete_trace_batch deletes agentic annotations for targeted traces and preserves others."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)

    trace_to_delete = str(uuid.uuid4())
    trace_survivor = str(uuid.uuid4())
    for tid in (trace_to_delete, trace_survivor):
        db_session.add(
            DatabaseTraceMetadata(
                trace_id=tid,
                task_id=task_id,
                start_time=now - timedelta(days=2),
                end_time=now - timedelta(days=2),
                span_count=0,
            )
        )
    db_session.commit()

    annotation_deleted = uuid.uuid4()
    annotation_survivor = uuid.uuid4()
    db_session.add(
        DatabaseAgenticAnnotation(
            id=annotation_deleted,
            annotation_type="human",
            annotation_score=1,
            trace_id=trace_to_delete,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.add(
        DatabaseAgenticAnnotation(
            id=annotation_survivor,
            annotation_type="human",
            annotation_score=0,
            trace_id=trace_survivor,
            created_at=now,
            updated_at=now,
        )
    )
    db_session.commit()

    try:
        delete_trace_batch(db_session, [trace_to_delete])
        db_session.commit()

        assert (
            db_session.execute(
                select(DatabaseAgenticAnnotation).where(
                    DatabaseAgenticAnnotation.id == annotation_deleted
                )
            ).scalar_one_or_none()
            is None
        )
        assert (
            db_session.execute(
                select(DatabaseAgenticAnnotation).where(
                    DatabaseAgenticAnnotation.id == annotation_survivor
                )
            ).scalar_one_or_none()
            is not None
        )
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[trace_to_delete, trace_survivor],
            annotation_ids=[annotation_deleted, annotation_survivor],
        )


@pytest.mark.unit_tests
def test_resource_preserved_when_referenced_by_span_in_other_trace() -> None:
    """A resource referenced via DatabaseSpan.resource_id in a surviving trace is not deleted."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)

    shared_resource_id = str(uuid.uuid4())
    db_session.add(
        DatabaseResourceMetadata(
            id=shared_resource_id,
            service_name="shared-service",
            resource_attributes={},
        )
    )
    db_session.commit()

    trace_a = str(uuid.uuid4())
    trace_b = str(uuid.uuid4())
    for tid in (trace_a, trace_b):
        db_session.add(
            DatabaseTraceMetadata(
                trace_id=tid,
                task_id=task_id,
                root_span_resource_id=None,
                start_time=now - timedelta(days=2),
                end_time=now - timedelta(days=2),
                span_count=1,
            )
        )

    span_a = str(uuid.uuid4())
    db_session.add(
        DatabaseSpan(
            id=span_a,
            trace_id=trace_a,
            span_id=span_a,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            task_id=task_id,
            resource_id=shared_resource_id,
            raw_data={},
            status_code="Unset",
        )
    )
    span_b = str(uuid.uuid4())
    db_session.add(
        DatabaseSpan(
            id=span_b,
            trace_id=trace_b,
            span_id=span_b,
            start_time=now - timedelta(days=2),
            end_time=now - timedelta(days=2),
            task_id=task_id,
            resource_id=shared_resource_id,
            raw_data={},
            status_code="Unset",
        )
    )
    db_session.commit()

    try:
        delete_trace_batch(db_session, [trace_a])
        db_session.commit()

        assert (
            db_session.execute(
                select(DatabaseTraceMetadata).where(
                    DatabaseTraceMetadata.trace_id == trace_a
                )
            ).scalar_one_or_none()
            is None
        )
        assert (
            db_session.execute(
                select(DatabaseSpan).where(DatabaseSpan.id == span_a)
            ).scalar_one_or_none()
            is None
        )
        assert (
            db_session.execute(
                select(DatabaseResourceMetadata).where(
                    DatabaseResourceMetadata.id == shared_resource_id
                )
            ).scalar_one_or_none()
            is not None
        )
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[trace_a, trace_b],
            span_ids=[span_a, span_b],
            resource_ids=[shared_resource_id],
        )


@pytest.mark.unit_tests
def test_resource_preserved_when_referenced_by_root_span_resource_id_in_other_trace() -> (
    None
):
    """A resource referenced via root_span_resource_id in a surviving trace is not deleted."""
    db_session: Session = override_get_db_session()
    task_id = _make_task(db_session)
    now = datetime.now(timezone.utc)

    shared_resource_id = str(uuid.uuid4())
    db_session.add(
        DatabaseResourceMetadata(
            id=shared_resource_id,
            service_name="shared-service",
            resource_attributes={},
        )
    )
    db_session.commit()

    trace_a = str(uuid.uuid4())
    trace_b = str(uuid.uuid4())
    for tid in (trace_a, trace_b):
        db_session.add(
            DatabaseTraceMetadata(
                trace_id=tid,
                task_id=task_id,
                root_span_resource_id=shared_resource_id,
                start_time=now - timedelta(days=2),
                end_time=now - timedelta(days=2),
                span_count=0,
            )
        )
    db_session.commit()

    try:
        delete_trace_batch(db_session, [trace_a])
        db_session.commit()

        assert (
            db_session.execute(
                select(DatabaseTraceMetadata).where(
                    DatabaseTraceMetadata.trace_id == trace_a
                )
            ).scalar_one_or_none()
            is None
        )
        assert (
            db_session.execute(
                select(DatabaseResourceMetadata).where(
                    DatabaseResourceMetadata.id == shared_resource_id
                )
            ).scalar_one_or_none()
            is not None
        )
    finally:
        _cleanup_trace_data(
            db_session,
            task_ids=[task_id],
            trace_ids=[trace_a, trace_b],
            resource_ids=[shared_resource_id],
        )
